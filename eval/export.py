#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""导出单题或批次，用于手动测试。

    python eval/export.py --id E01
    python eval/export.py --id V01 --out prompts
    python eval/export.py --batch 1
    python eval/export.py --list
"""

import argparse
import json
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ITEMS_PATH = os.path.join(ROOT, "data", "items.jsonl")
ASSETS = os.path.join(ROOT, "data", "assets")


def load():
    with open(ITEMS_PATH, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def prompt(it):
    blocks = ["【材料】", it["scene"]]
    if it.get("history"):
        blocks += ["", "【前情】"] + it["history"]
    if it.get("type") == "image":
        blocks += ["", "【图片】见附图"]
    blocks += ["", "【用户】", it.get("user") or "（只发图）"]
    blocks += ["", "【任务】写出你的下一条回复。"]
    blocks += ["", "【作答】以“回复：”开头，只写回复正文，不要解释。"]
    return "\n".join(blocks) + "\n"


def batches(items):
    text = [x for x in items if x["type"] == "text"]
    types = []
    for x in text:
        if x["turn_type"] not in types:
            types.append(x["turn_type"])
    by = {t: [x for x in text if x["turn_type"] == t] for t in types}
    out = {i: [] for i in range(5)}
    for ti, t in enumerate(types):
        for j, x in enumerate(by[t]):
            out[(ti + j) % 5].append(x)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id")
    ap.add_argument("--batch", type=int, choices=range(1, 6))
    ap.add_argument("--out", help="写出文件；不给就打印")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    items = load()
    by_id = {x["id"]: x for x in items}

    if args.list:
        for x in items:
            print("%-4s %-5s %-28s %s" % (x["id"], x["type"], x["turn_type"], x.get("status", "")))
        return 0

    if args.id:
        if args.id not in by_id:
            print("no such id:", args.id)
            return 2
        it = by_id[args.id]
        text = prompt(it)
        if not args.out:
            print(text)
            return 0
        d = os.path.join(args.out, it["id"])
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "题目.txt"), "w", encoding="utf-8") as f:
            f.write(text)
        if it.get("type") == "image":
            shutil.copy2(os.path.join(ASSETS, it["image"]), os.path.join(d, "图片.jpg"))
        print("→", d)
        return 0

    if args.batch:
        bs = batches(items)
        chosen = bs[args.batch - 1]
        lines = ["下面有 %d 段独立对话。每段只看自己的前情，不要参考其他段。" % len(chosen),
                 "为每段写出你的下一条回复。",
                 "每题只输出一行：<题号>. 回复：<正文>",
                 "不要分析、不要解释、不要合并不同题。", ""]
        for n, it in enumerate(chosen, 1):
            lines += ["===== 第 %d 段 =====" % n, "【材料】", it["scene"]]
            if it.get("history"):
                lines += ["", "【前情】"] + it["history"]
            lines += ["", "【用户】", it["user"], ""]
        text = "\n".join(lines)
        if not args.out:
            print(text)
            return 0
        os.makedirs(args.out, exist_ok=True)
        p = os.path.join(args.out, "批次%d.txt" % args.batch)
        open(p, "w", encoding="utf-8").write(text)
        print("→", p)
        return 0

    print("use --id, --batch, or --list")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
