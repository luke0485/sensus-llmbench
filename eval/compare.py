#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""版本回归：同一套题，比较两个模型版本，看人文对话有没有掉。

    python eval/compare.py --old results/model_v1.json --new results/model_v2.json --out compare/

输入是 score.py 产出的两份 profile。输出：
  compare/compare.md    按类别 + 逐题的回归报告
  compare/compare.json  同样的数据，给 CI 用

不做总分，不做排名。只看“哪些题/哪类能力退化了”。
"""

import argparse
import json
import os
import sys


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--out", default="compare")
    args = ap.parse_args()

    old, new = load(args.old), load(args.new)
    om, nm = old.get("meta", {}), new.get("meta", {})

    if om.get("judge") and nm.get("judge") and om["judge"] != nm["judge"]:
        print("警告：两次 judge 不同（%s vs %s），分数不可直接比较" % (om["judge"], nm["judge"]))

    oi = {r["id"]: r for r in old.get("items", [])}
    ni = {r["id"]: r for r in new.get("items", [])}
    common = sorted(set(oi) & set(ni))

    rows = []
    for iid in common:
        o, n = oi[iid], ni[iid]
        if o.get("score") is None or n.get("score") is None:
            continue
        delta = round(n["score"] - o["score"], 3)
        flag = ""
        if o.get("pass") and not n.get("pass"):
            flag = "lost_pass"
        elif delta <= -0.3:
            flag = "regression"
        elif delta >= 0.3:
            flag = "improvement"
        rows.append({
            "id": iid,
            "category": o.get("category", ""),
            "old": o["score"],
            "new": n["score"],
            "delta": delta,
            "flag": flag,
            "old_pass": bool(o.get("pass")),
            "new_pass": bool(n.get("pass")),
            "new_response": (n.get("response") or "")[:300],
        })

    cats = {}
    for r in rows:
        c = cats.setdefault(r["category"], {"n": 0, "old": 0.0, "new": 0.0,
                                            "old_pass": 0, "new_pass": 0})
        c["n"] += 1
        c["old"] += r["old"]
        c["new"] += r["new"]
        c["old_pass"] += 1 if r["old_pass"] else 0
        c["new_pass"] += 1 if r["new_pass"] else 0
    for c in cats.values():
        c["old"] = round(c["old"] / c["n"], 3)
        c["new"] = round(c["new"] / c["n"], 3)
        c["delta"] = round(c["new"] - c["old"], 3)
        c["old_pass_rate"] = round(c["old_pass"] / c["n"], 3)
        c["new_pass_rate"] = round(c["new_pass"] / c["n"], 3)
        for k in ("old_pass", "new_pass"):
            del c[k]

    regressions = [r for r in rows if r["flag"] in ("regression", "lost_pass")]
    improvements = [r for r in rows if r["flag"] == "improvement"]

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "compare.json"), "w", encoding="utf-8") as f:
        json.dump({
            "meta": {"old": om, "new": nm, "matched_items": len(common)},
            "categories": cats,
            "items": rows,
        }, f, ensure_ascii=False, indent=1)

    md = ["# 版本回归：人文对话还在不在", "",
          "- 旧版：`%s`" % om.get("model", "?"),
          "- 新版：`%s`" % nm.get("model", "?"),
          "- judge：`%s`" % (nm.get("judge") or om.get("judge") or "?"),
          "- 对齐题数：%d" % len(common), ""]

    md += ["## 类别变化", "",
           "| 类别 | 题数 | 旧均分 | 新均分 | 变化 | 旧通过率 | 新通过率 |",
           "|---|---:|---:|---:|---:|---:|---:|"]
    for k, c in sorted(cats.items()):
        md.append("| %s | %d | %.2f | %.2f | %+.2f | %.0f%% | %.0f%% |"
                  % (k, c["n"], c["old"], c["new"], c["delta"],
                     c["old_pass_rate"] * 100, c["new_pass_rate"] * 100))
    md.append("")

    md += ["## 退化的题", ""]
    if regressions:
        md += ["| 题号 | 类别 | 旧 | 新 | 变化 | 新版回答（截断） |",
               "|---|---|---:|---:|---:|---|"]
        for r in regressions:
            md.append("| `%s` | %s | %.2f | %.2f | %+.2f | %s |"
                      % (r["id"], r["category"], r["old"], r["new"], r["delta"],
                         r["new_response"].replace("|", "｜").replace("\n", " ")))
    else:
        md.append("无。")
    md.append("")

    md += ["## 提升的题", ""]
    if improvements:
        md += ["| 题号 | 类别 | 旧 | 新 | 变化 |", "|---|---|---:|---:|---:|"]
        for r in improvements:
            md.append("| `%s` | %s | %.2f | %.2f | %+.2f |"
                      % (r["id"], r["category"], r["old"], r["new"], r["delta"]))
    else:
        md.append("无。")
    md += ["", "> 只有题库版本、judge、采样参数都一致，这个对比才成立。"
               "批量模式的结果不要拿来比。", ""]

    with open(os.path.join(args.out, "compare.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print("matched %d | regressions %d | improvements %d"
          % (len(common), len(regressions), len(improvements)))
    print("→", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
