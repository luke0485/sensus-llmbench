# Changelog

## 1.0.0 — 2026-11-22（冻结）

- 45 道：40 道文本 + 5 道图片（图片为 provisional，未校准）
- 10 类情绪/意图转弯，每类 4 道文本
- 评分：转弯 / 层次 / 克制，各 0—2 分，≥ 0.7 通过
- 首轮校准：
  - DeepSeek chat 40 题：38% 通过，均分 0.65
  - DeepSeek chat / reasoner / 智谱 GLM-4.5-Flash 同 10 题：30% / 30% / 0%
  - 同一批 reasoner 回答，换 judge 相差约 0.14 分
- 冻结规则：不再修改 `data/items.jsonl`；任何改动进入 1.1.0，并重跑校准
- 仓库结构：`data/`（JSONL + JSON Schema + 图片）、`eval/`（运行/评分/导出/对比/统计）、`docs/`；不再包含逐题 txt/md
