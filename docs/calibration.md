# 校准协议

## 为什么不用本地小模型当标尺

本机那个是 Qwen2.5-1.5B-Instruct，纯文本，连视觉都没有，只能当“地板”：
证明题目不是不可解。它不能当参照，更不能决定难度。

**标尺必须是云端前沿模型。**

## 需要几个模型

至少 3 个，来自不同家族：

- 一个国际前沿（如 GPT / Claude / Gemini 的最新版）
- 一个国内前沿（如 Qwen-Max / DeepSeek / GLM）
- 一个上一代或小尺寸，作为对照

## 协议

1. 一题一个对话，不要把多题塞进同一段上下文。
2. 思考模式固定：默认关闭；如果模型只能开，记录 `thinking=on`，单独一组，不和关闭组混比。
3. `temperature=0`，同一题跑 3 次。
4. judge 用另一个模型，固定版本；和被测模型不要同家族。
5. 记录：模型版本、系统提示（无）、采样参数、judge、题库版本、日期。

## 判读

- 每题通过率 = 3 次里通过的次数 / 3。
- 目标区间：核心题 20%—80%。
- 通过率 ≥95%：题太浅，下一版淘汰或加硬。
- 通过率 ≤5%：可能太偏、歧义，或模型确实不会；先人工复盘，再决定。
- 不做公开难度等级，只做内部维护。

## 版本回归

代码能力升级后，人文对话有没有掉：

```bash
python eval/compare.py --old results/old.json --new results/new.json --out compare/
```

只看两件事：哪一类退了、哪几题退了。不看总分。

## 云端跑法

任何 OpenAI 兼容端点都行：

```bash
# OpenAI
python eval/run.py --base-url https://api.openai.com/v1 --model <model> --out runs/gpt.json

# DeepSeek
python eval/run.py --base-url https://api.deepseek.com/v1 --model deepseek-chat --out runs/ds.json

# 通义千问
python eval/run.py --base-url https://dashscope.aliyuncs.com/compatible-mode/v1 --model qwen-max --out runs/qwen.json

# Moonshot
python eval/run.py --base-url https://api.moonshot.cn/v1 --model moonshot-v1-8k --out runs/kimi.json
```

然后：

```bash
export JUDGE_API_KEY=...
python eval/score.py --run runs/gpt.json --judge-model <另一个模型> --out results/gpt.json
```

批量文件只用于快筛；正式分必须一题一对话。
