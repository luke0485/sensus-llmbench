#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""跑模型：一条题 = 一次全新对话，不加 system prompt。

用法：
    export OPENAI_API_KEY=sk-...
    python eval/run.py --model gpt-4.1 --out runs/gpt41.json
"""

import argparse
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ITEMS_PATH = os.path.join(ROOT, "data", "items.jsonl")


def load_items():
    with open(ITEMS_PATH, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def build_prompt(item):
    user = item.get("user") or "（只发图，没有文字）"
    blocks = ["【材料】", item["scene"]]
    if item.get("history"):
        blocks += ["", "【前情】"] + item["history"]
    blocks += [
        "", "【用户】", user,
        "", "【任务】写出你的下一条回复。",
        "", "【作答】以“回复：”开头，只写回复正文，不要解释。",
    ]
    return "\n".join(blocks)


def build_content(item):
    parts = [{"type": "text", "text": build_prompt(item)}]
    if item.get("image"):
        path = os.path.join(ROOT, "data", "assets", item["image"])
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        parts.append({"type": "image_url",
                      "image_url": {"url": "data:image/jpeg;base64," + b64}})
    return parts


def clean(text):
    """Thinking models may wrap the answer in <think>/<answer>."""
    m = re.search(r"<answer>(.*?)</answer>", text, re.S)
    if m:
        text = m.group(1)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    return text.strip()


def chat(base_url, api_key, model, content, temperature, max_tokens, timeout):
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "temperature": temperature,
        "max_tokens": max_tokens,
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
    msg = body["choices"][0]["message"].get("content") or ""
    if isinstance(msg, list):
        msg = "".join(p.get("text", "") for p in msg if isinstance(p, dict))
    return clean(msg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="https://api.openai.com/v1")
    ap.add_argument("--model", default="gpt-4.1")
    ap.add_argument("--api-key-env", default="OPENAI_API_KEY")
    ap.add_argument("--out", default="runs/run.json")
    ap.add_argument("--ids", help="逗号分隔，只跑这些题")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--max-tokens", type=int, default=600)
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--delay", type=float, default=0.0, help="每次调用后的等待秒数")
    args = ap.parse_args()

    key = os.environ.get(args.api_key_env, "")
    if not key:
        print("缺少 API key：设置 %s" % args.api_key_env)
        return 2

    items = load_items()
    if args.ids:
        want = {x.strip() for x in args.ids.split(",")}
        items = [it for it in items if it["id"] in want]
    if args.limit:
        items = items[: args.limit]

    results = []
    for i, item in enumerate(items, 1):
        t0 = time.time()
        try:
            reply = chat(args.base_url, key, args.model, build_content(item),
                         args.temperature, args.max_tokens, args.timeout)
            err = None
        except Exception as e:                      # noqa: BLE001
            reply, err = "", "%s: %s" % (type(e).__name__, e)
        results.append({
            "id": item["id"],
            "prompt": build_prompt(item),
            "response": reply,
            "error": err,
            "latency_ms": int((time.time() - t0) * 1000),
        })
        print("[%d/%d] %s %s" % (i, len(items), item["id"],
                                 "ERROR" if err else "ok"))
        if args.delay:
            time.sleep(args.delay)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({
            "meta": {
                "model": args.model,
                "base_url": args.base_url,
                "temperature": args.temperature,
                "system": None,
                "items": len(items),
                "date": time.strftime("%Y-%m-%d"),
            },
            "results": results,
        }, f, ensure_ascii=False, indent=1)
    print("→", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
