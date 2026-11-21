#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""评分：一条回复，按「转弯 / 层次 / 克制」三个维度各判 0—2 分。

    export JUDGE_API_KEY=sk-...
    python eval/score.py --run runs/gpt.json --judge-model gpt-4.1 --out results/gpt.json
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ITEMS_PATH = os.path.join(ROOT, "data", "items.jsonl")

JUDGE_SYSTEM = (
    "你是评分员。你判断一条回复有没有接住对话里最后那个情绪/意图的转弯，"
    "有没有碰到表面问题下面那层，有没有忍住不给建议。不要看文采，不要因为写得多就给分。"
    "只输出 JSON。"
)

JUDGE_TEMPLATE = """【对话】
{history}
用户：{user}

【表面】
{surface}

【真正的转弯】
{turn_key}

【底下那层】
{underlying}

【回复应做到】
{must}

【回复不得出现】
{must_not}

【2分示例】
{reference}

【1分示例】
{exemplar_1}

【0分示例】
{exemplar_0}

【模型回复】
<<<
{reply}
>>>

请分别给 0、1、2 分：
- turn：2=接住了最后那个转弯；1=察觉到了但还在回应前面的情绪；0=完全按前面的框架继续
- layer：2=碰到了下面那层；1=只沾到一点；0=只回答了表面问题
- restraint：2=忍住不给建议/不评判，先留空间；1=略急，给了一点建议；0=直接说教/下判断/给方案

只输出：
{{"turn": 2, "layer": 1, "restraint": 2, "note": "一句话"}}"""


def load_items():
    with open(ITEMS_PATH, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def call_judge(base_url, api_key, model, prompt, timeout):
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": JUDGE_SYSTEM},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "max_tokens": 2500,
    }
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + api_key},
        method="POST",
    )
    body = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = json.loads(r.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(5 * (attempt + 1))
                continue
            raise
    return body["choices"][0]["message"].get("content") or ""


def parse_judge(text):
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None, "no JSON"
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None, "bad JSON"
    for k in ("turn", "layer", "restraint"):
        if obj.get(k) not in (0, 1, 2):
            return None, "%s out of range" % k
    obj["note"] = str(obj.get("note", ""))[:200]
    return obj, None


def score_one(item, response, judge):
    text = (response or "").strip()
    text = re.sub(r"^回复\s*[:：]\s*", "", text).strip()
    if not text:
        return 0.0, None, "空回答"

    for bad in item.get("forbid", []):
        if bad and bad in text:
            return 0.0, None, "命中禁用表达：%s" % bad

    history = "\n".join(item.get("history") or [])
    prompt = JUDGE_TEMPLATE.format(
        history=history,
        user=item.get("user") or "",
        surface=item.get("surface", ""),
        turn_key=item.get("turn_key", ""),
        underlying=item.get("underlying", ""),
        must="；".join(item["reply_must"]),
        must_not="；".join(item["reply_must_not"]),
        reference=item.get("reference", ""),
        exemplar_1=item.get("exemplar_1", ""),
        exemplar_0=item.get("exemplar_0", ""),
        reply=text[:2000],
    )
    try:
        raw = call_judge(judge["base_url"], judge["api_key"], judge["model"],
                         prompt, judge["timeout"])
        obj, err = parse_judge(raw)
    except Exception as e:                          # noqa: BLE001
        return None, None, "judge 失败：%s" % e
    if obj is None:
        return None, None, "judge 输出无法解析：%s" % err

    total = (obj["turn"] + obj["layer"] + obj["restraint"]) / 6.0
    return round(total, 3), obj, obj["note"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", default="results/profile.json")
    ap.add_argument("--judge-base-url", default="https://api.openai.com/v1")
    ap.add_argument("--judge-model", default="gpt-4.1")
    ap.add_argument("--judge-api-key-env", default="JUDGE_API_KEY")
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--judge-delay", type=float, default=0.0)
    args = ap.parse_args()

    key = os.environ.get(args.judge_api_key_env, "")
    if not key:
        print("缺少 judge key：设置 %s" % args.judge_api_key_env)
        return 2

    with open(args.run, encoding="utf-8") as f:
        run = json.load(f)
    by_id = {it["id"]: it for it in load_items()}
    judge = {"base_url": args.judge_base_url, "api_key": key,
             "model": args.judge_model, "timeout": args.timeout}

    rows = []
    for res in run["results"]:
        item = by_id.get(res["id"])
        if not item:
            continue
        score, dims, note = score_one(item, res.get("response", ""), judge)
        if args.judge_delay:
            time.sleep(args.judge_delay)
        rows.append({
            "id": item["id"],
            "category": item["category"],
            "score": score,
            "pass": bool(score is not None and score >= 0.7),
            "dims": dims,
            "note": note,
            "response": res.get("response", ""),
        })

    cats = {}
    for r in rows:
        if r["score"] is None:
            continue
        c = cats.setdefault(r["category"], {"n": 0, "passed": 0, "sum": 0.0})
        c["n"] += 1
        c["passed"] += 1 if r["pass"] else 0
        c["sum"] += r["score"]
    for c in cats.values():
        c["pass_rate"] = round(c["passed"] / c["n"], 3)
        c["mean"] = round(c["sum"] / c["n"], 3)
        del c["sum"]

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({
            "meta": dict(run.get("meta", {}), judge=args.judge_model),
            "categories": cats,
            "items": rows,
        }, f, ensure_ascii=False, indent=1)

    print("%-12s %3s %8s %6s" % ("category", "n", "pass", "mean"))
    for k, c in cats.items():
        print("%-12s %3d %7.0f%% %6.2f" % (k, c["n"], c["pass_rate"] * 100, c["mean"]))
    print("→", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
