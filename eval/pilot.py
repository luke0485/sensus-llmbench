#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""预试统计：每题通过率、跨模型区分度、重复运行稳定性。

    python eval/pilot.py --results results/*.json --out-dir pilot

输入是 score.py 产出的结果文件。输出：
  pilot/item_stats.csv   每题统计
  pilot/review.csv       双人审题表（空白，待填）
  pilot/summary.md       汇总

注意：这里只做“题还值不值得留”的维护判断，不对外标难度等级。
"""

import argparse
import csv
import glob
import json
import os
import statistics
import sys
from collections import defaultdict


def load_results(patterns):
    runs = []
    for pat in patterns:
        for path in glob.glob(pat):
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            runs.append((os.path.basename(path), data.get("meta", {}), data.get("items", [])))
    return runs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", nargs="+", required=True)
    ap.add_argument("--out-dir", default="pilot")
    args = ap.parse_args()

    runs = load_results(args.results)
    if len(runs) < 2:
        print("至少需要 2 份结果（最好是不同模型，或同一模型重复跑）")
        return 2

    # item_id -> list of (model, pass)
    obs = defaultdict(list)
    model_of = {}
    for name, meta, items in runs:
        model = meta.get("model", name)
        model_of[name] = model
        for r in items:
            if r.get("pass") is None:
                continue
            obs[r["id"]].append((model, bool(r["pass"]), r.get("category", "")))

    rows = []
    for iid, entries in sorted(obs.items()):
        passes = [p for _, p, _ in entries]
        rate = sum(passes) / len(passes)
        by_model = defaultdict(list)
        for m, p, _ in entries:
            by_model[m].append(p)
        model_rates = {m: sum(v) / len(v) for m, v in by_model.items()}
        spread = (max(model_rates.values()) - min(model_rates.values())) if len(model_rates) > 1 else None
        unstable = any(
            len(v) > 1 and (max(v) - min(v)) >= 0.5 for v in by_model.values()
        )

        flag = ""
        if len(passes) >= 2 and rate >= 0.95:
            flag = "too_easy"
        elif len(passes) >= 2 and rate <= 0.05:
            flag = "too_hard"
        elif unstable:
            flag = "unstable"
        elif spread is not None and spread < 0.1 and 0.1 < rate < 0.9:
            flag = "no_discrimination"

        rows.append({
            "id": iid,
            "category": entries[0][2],
            "n": len(passes),
            "models": len(model_rates),
            "pass_rate": round(rate, 3),
            "spread": "" if spread is None else round(spread, 3),
            "flag": flag,
        })

    os.makedirs(args.out_dir, exist_ok=True)

    with open(os.path.join(args.out_dir, "item_stats.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "category", "n", "models",
                                          "pass_rate", "spread", "flag"])
        w.writeheader()
        w.writerows(rows)

    with open(os.path.join(args.out_dir, "review.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "category",
                    "r1_intent_ok", "r1_cues_real", "r1_bias_ok",
                    "r2_intent_ok", "r2_cues_real", "r2_bias_ok", "notes"])
        for r in rows:
            w.writerow([r["id"], r["category"], "", "", "", "", "", "", ""])

    by_flag = defaultdict(list)
    for r in rows:
        if r["flag"]:
            by_flag[r["flag"]].append(r)

    md = ["# 预试统计", "",
          "结果文件：%d 份；模型：%s" % (len(runs), "、".join(sorted(set(model_of.values())))), "",
          "| 指标 | 值 |", "|---|---|",
          "| 题目数 | %d |" % len(rows),
          "| 过易（≥95%%） | %d |" % len(by_flag["too_easy"]),
          "| 过难（≤5%%） | %d |" % len(by_flag["too_hard"]),
          "| 区分度不足 | %d |" % len(by_flag["no_discrimination"]),
          "| 不稳定 | %d |" % len(by_flag["unstable"]), ""]
    for flag, title in [("too_easy", "过易"), ("too_hard", "过难"),
                        ("no_discrimination", "区分度不足"), ("unstable", "不稳定")]:
        md.append("## %s" % title)
        md.append("")
        if by_flag[flag]:
            md.append("| 题号 | 类别 | 通过率 | 跨模型差 |")
            md.append("|---|---|---:|---:|")
            for r in by_flag[flag]:
                md.append("| `%s` | %s | %.0f%% | %s |"
                          % (r["id"], r["category"], r["pass_rate"] * 100, r["spread"] or "—"))
        else:
            md.append("无。")
        md.append("")
    md += ["## 说明", "",
           "淘汰只是维护判断：这道题在当前模型区间内不再有区分度，下一版下架或改写。",
           "不对外发布难度等级。", ""]
    with open(os.path.join(args.out_dir, "summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print("items %d | too_easy %d | too_hard %d | no_discrimination %d | unstable %d"
          % (len(rows), len(by_flag["too_easy"]), len(by_flag["too_hard"]),
             len(by_flag["no_discrimination"]), len(by_flag["unstable"])))
    print("→", args.out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
