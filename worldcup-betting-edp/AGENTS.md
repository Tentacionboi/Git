# AGENTS.md

本文件是项目级协作规则。任何后续对话、子 agent 或人工贡献者都应先读本文件，再修改代码。

## Project Goal

建立一个可复现、可回测、可解释的世界杯足球竞猜概率定价系统。

系统目标不是制造“稳赢”叙事，而是：

1. 估计赛前真实概率。
2. 与市场赔率去水概率比较。
3. 标记可能的正期望机会。
4. 用样本外回测判断模型是否优于市场。

## Non-Negotiable Rules

1. 市场赔率是强基准，任何模型都必须与去水市场概率比较。
2. 不允许使用未来数据预测过去。
3. 所有特征必须能回答：在下注时点是否已经可获得？
4. 命中率不是核心指标；Brier、log loss、ROI、drawdown、calibration 同等重要。
5. 若模型不能击败市场，结论必须直接写出来。
6. “态势感知”“全域感知”“信号传播”等术语必须落地为字段、模型、规则或指标。
7. MVP 只做 90 分钟 1X2 胜平负市场。
8. 复杂模型必须在简单模型和市场基准之后。

## Thread Strategy

当前主线程负责总控、架构、取舍和合并。只有当任务边界清楚时，才开专项线程：

- 数据线程：数据源、下载、schema、清洗。
- 模型线程：market baseline、Elo、Poisson、融合模型。
- 回测线程：评分指标、资金曲线、Kelly、风险分析。

专项线程不得单独改变项目方向、schema 或核心接口。需要变更时，先记录到 `DECISIONS.md`。

## Code Standards

- 使用 Python 3.10+。
- 核心逻辑放在 `src/worldcup_betting_edp/`。
- 测试放在 `tests/`。
- 基础模块优先使用标准库，避免过早引入重依赖。
- 每个可交易判断必须能追溯到概率、赔率、EV 和风险限制。

## Current Phase

Phase 2：建立可运行 MVP 地基。

当前优先级：

1. 市场赔率去水模块。
2. EV/value bet/Kelly 模块。
3. 统一比赛和赔率 schema。
4. 市场 baseline 回测。
5. Elo baseline。
6. Poisson baseline。

