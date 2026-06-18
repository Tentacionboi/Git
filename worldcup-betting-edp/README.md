# World Cup Betting EDP

世界杯足球竞猜预测与 EDP 方法论研究项目。

本项目目标不是证明某个方法必然有效，而是建立一个可验证、可回测、可解释的世界杯竞猜概率定价系统：

- 估计比赛真实概率；
- 与市场赔率去水后的隐含概率比较；
- 只在模型概率、赔率、风险约束同时满足时标记 value bet；
- 用严格回测判断模型是否真的优于市场基准。

## Directory Layout

```text
worldcup-betting-edp/
├── README.md
├── AGENTS.md
├── PROJECT_STATUS.md
├── ROADMAP.md
├── TASKS.md
├── DECISIONS.md
├── DATA_SOURCES.md
├── MODEL_SPEC.md
├── BACKTEST_SPEC.md
├── pyproject.toml
├── data/
│   ├── raw/          # 原始下载数据，不手工改写
│   ├── processed/    # 清洗、标准化、可建模数据
│   └── external/     # 第三方公开数据快照和说明
├── notebooks/        # 探索性分析与模型试验
├── src/
│   └── worldcup_betting_edp/
│       ├── data/     # 数据抓取、读取、校验、版本化
│       ├── features/ # 特征工程：Elo、状态、赛程、市场信号
│       ├── models/   # 概率模型：market、Elo、Poisson、融合模型
│       ├── market/   # 赔率去水、盘口快照、市场概率
│       ├── betting/  # EV、value bet、Kelly、风险控制
│       ├── backtest/ # 时间切分、预测质量、资金曲线回测
│       └── reports/  # 报告生成脚本
├── configs/          # 数据源、模型参数、回测参数
├── tests/            # 单元测试与回归测试
└── reports/          # 研究报告、图表、阶段性结论
```

## First Report

第一阶段研究报告见：

```text
reports/initial_research_report.md
```

Current checkpoint status:

```text
PROJECT_STATUS.md
```

## Development

This project requires Python 3.10+. On this machine, use:

```bash
/opt/homebrew/bin/python3.12 --version
```

Run tests:

```bash
PYTHONPATH=src /opt/homebrew/bin/python3.12 -m unittest discover -s tests
```

Run the single-match MVP demo:

```bash
PYTHONPATH=src /opt/homebrew/bin/python3.12 examples/single_match_demo.py
```

Run the local Streamlit dashboard:

```bash
/opt/homebrew/bin/python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[ui]"
streamlit run apps/streamlit_app.py
```

The dashboard uses English-first bilingual labels, for example `Market Odds / 市场赔率`.
