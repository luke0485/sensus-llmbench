# 题库格式（已冻结）

`items.jsonl`，一行一段对话。

## 模型看到什么

```
【材料】
你和用户已经聊了几轮。

【前情】
用户：……
你：……
用户：……
你：……

【用户】
（最后一句）

【任务】写出你的下一条回复。

【作答】以“回复：”开头，只写回复正文，不要解释。
```

模型不看到“表面/第二层/底下”，也不看到评分维度。它只负责写下一句。

## 字段

| 字段 | 说明 |
|---|---|
| `id` | 题号 |
| `category` | `trajectory` |
| `modality` | `text` / `image`；图片题 5 道，标记 `provisional` |
| `image` | 图片文件名（图片题） |
| `status` | `provisional`：图片题未校准 |
| `turn_type` | 十类情绪与意图之一，见下 |
| `scene` | 一句话交代关系或语气 |
| `history` | 前几轮对话，按“用户：/你：”写 |
| `user` | 最后一句用户发言 |
| `surface` | 他字面上在说什么 |
| `turn_key` | 情绪/意图在哪一层变化 |
| `underlying` | 表面问题下面那层是什么 |
| `reply_must` | 回复应做到 |
| `reply_must_not` | 回复不得出现 |
| `reference` | 2 分示例 |
| `exemplar_1` | 1 分示例 |
| `exemplar_0` | 0 分示例 |

## 十类情绪与意图

| 类型 | 一句描述 |
|---|---|
| self_mock_to_doubt | 自嘲 → 真的自我怀疑 |
| complain_to_protect | 抱怨 → 护短/愧疚 |
| permission_to_decision | 求许可 → 其实已决定 |
| pride_to_guilt | 报喜 → 愧疚 |
| anger_to_fear | 愤怒 → 害怕 |
| enthusiasm_to_deflation | 热情 → 被否定后退缩 |
| ask_to_shame | 求助 → 羞耻撤退 |
| calm_to_irony_to_anger | 平静 → 反讽 → 真怒 |
| care_to_control | 关心 → 控制/越界 |
| apology_to_grievance | 道歉 → 委屈/反击 |

## 评分

| 维度 | 0 | 1 | 2 |
|---|---|---|---|
| 接住 | 完全按前面的框架继续 | 察觉到了，但还在回应前面的情绪 | 接住了最后那层意思 |
| 层次 | 只回答表面问题 | 只沾到一点 | 碰到了下面那层 |
| 克制 | 直接说教/下判断/给方案 | 略急，给了一点建议 | 忍住，先留空间 |

```
得分 = (接住 + 层次 + 克制) / 6
通过 = 得分 ≥ 0.7
```

只出通过率，不出总分，不排名。

## 加一段对话

1. 先写前情，再写最后一句。最后一句必须**改变**前面的情绪或意图走向。
2. `turn_key` 写清楚“从哪里转到哪里”。
3. `underlying` 写清楚“他真正在问什么”。
4. `reply_must` / `reply_must_not` 写动作，不写形容词。
5. 跑一遍确认格式。
