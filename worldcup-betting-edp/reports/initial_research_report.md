# 世界杯足球竞猜预测与 EDP 方法论研究项目：初始研究报告

日期：2026-06-18  
阶段：Phase 1 / 项目初始化与方法论审计  
结论置信度：EDP 仓库审计为高；足球竞猜建模路线为高；具体数据源可用性为中高，因为部分赔率、阵容、伤病数据源会随 API 和许可变化。

## 1. 项目摘要

本项目的正确目标不是“预测世界杯冠军”或“找到稳赢方法”，而是建立一个可检验的概率定价系统：

1. 把每场比赛转化为概率分布：胜/平/负、让球、大小球、比分。
2. 把市场赔率去水后转化为市场隐含概率。
3. 用模型概率和市场概率比较，只在存在正期望且风险可控时标记 value bet。
4. 用严格回测检验模型是否优于市场，而不是用个案叙事证明自己聪明。

第一阶段结论很直接：EDP 仓库不是一个成熟的足球预测系统，也不是可直接迁移到世界杯竞猜的生产级算法库。它更像一个“概率分析 + 多源信息融合 + 资金分配”的概念性研究框架，附带部分 Python/TypeScript 原型代码。可用思想包括赔率去水、概率快照、概率流、信号源加权、异常检测和 fractional Kelly。不可直接相信的部分包括“全域感知”“流向倍增”“态势评估”等高概念术语；这些必须先被压缩成可观测变量、模型输入、交易规则和回测指标。

项目 MVP 应从世界杯单场 1X2 胜平负市场开始。第一版只做四类模型：市场基准、Elo、Poisson、简单融合。不要上深度学习；数据量不足，且市场赔率本身已经吸收大量公开信息，复杂模型更容易过拟合。

## 2. EDP 仓库分析

### 2.1 基本情况

仓库：<https://github.com/ai-nurmamat/EDP>  
本次审计方式：`git ls-remote`、临时克隆、读取 README/代码/依赖/示例/测试、GitHub CLI 元数据查询。  
审计时间：2026-06-18。

可获取元数据：

| 项目 | 结果 |
|---|---:|
| 默认分支 | `master` |
| HEAD commit | `473145195377aa76604319321cf5810998931fa8` |
| 最近提交信息 | `feat: 修改仓库介绍` |
| 最近提交时间 | 2026-06-16 13:53:07 UTC |
| GitHub 创建时间 | 2026-04-12 17:49:08 UTC |
| 最近 push | 2026-06-16 13:58:09 UTC |
| GitHub updatedAt | 2026-06-17 13:06:05 UTC |
| stars | 10 |
| forks | 4 |
| watchers | 1 |
| open issues | 0 |
| PR | 1 个 open PR |
| GitHub description | `ozluk.ai agent management workspace` |
| 本地 LICENSE | MIT，但 GitHub API 识别为 `Other` |

异常点：仓库描述仍是 `ozluk.ai agent management workspace`，LICENSE 版权写的是 SPAF Team，README 又说项目是 EDP。这说明项目经历过重命名和身份迁移，文档、代码、测试没有完全同步。

### 2.2 项目结构

仓库主要文件：

```text
README.md
README_EN.md
CONTRIBUTING.md
LICENSE
pyproject.toml
package.json
package-lock.json
tsconfig.json
docs/theory/references.md
examples/python/basic_usage.py
examples/js/basic_usage.ts
mcp/server.py
mcp/README.md
skill/README.md
src/python/__init__.py
src/python/probability_engine.py
src/python/domain_awareness.py
src/python/flow_amplification.py
src/python/flow_analyzer.py
src/python/scheme_designer.py
src/types/protocols.py
src/js/index.ts
tests/python/test_probability_engine.py
```

代码规模：

| 文件 | 行数 |
|---|---:|
| `README.md` | 415 |
| `src/python/probability_engine.py` | 1049 |
| `src/python/domain_awareness.py` | 773 |
| `src/python/flow_amplification.py` | 765 |
| `src/python/scheme_designer.py` | 559 |
| `src/python/flow_analyzer.py` | 307 |
| `src/js/index.ts` | 739 |

### 2.3 依赖与技术栈

Python：

- `pyproject.toml` 项目名为 `edp-framework`，版本 `4.1.0`。
- Python 要求 `>=3.10`。
- runtime dependencies 为空。
- dev dependencies 包括 `pytest`、`pytest-cov`、`mypy`、`black`、`ruff`、`isort`。
- optional `mcp` 依赖声明为 `mcp>=0.9.0`。

TypeScript：

- `package.json` 项目名为 `edp-framework`，版本 `4.1.0`。
- Node 要求 `>=18.0.0`。
- dev dependencies 包括 TypeScript、Jest、ts-jest、typedoc、prettier。

技术含义：这是一个轻量原型库，不依赖 NumPy/Pandas/scikit-learn/statsmodels/PyMC 等建模库，也没有数据获取、训练、评估、回测 pipeline。它不可能凭当前结构承担严肃足球预测系统。

### 2.4 主要代码模块

`ProbabilityEngine`：

- 支持市场类型枚举：1X2、handicap、total goals、correct score、half-full。
- 实现赔率转隐含概率、去水概率、市场 margin。
- 包含一个所谓 iterative Shin 方法，但实现是简化近似，并非经过外部库或论文复现实证验证。
- 实现 Beta-Binomial 更新。
- 实现简化 Glicko-2 rating。
- 实现概率快照之间的 flow 分析：概率变化、方向、速度、显著性。

`DomainAwarenessEngine`：

- 把多个 `EvidenceSource` 融合成一个概率。
- 源权重 = reliability × confidence × temporal decay。
- 支持 linear pool、log-odds pool、Bayesian-style log-odds accumulation、hybrid。
- 用概率离散度计算 consensus score。
- 用 z-score 检测异常源，用“高一致但源数量少”标记 potential cascade。

`FlowAmplificationEngine` / `FlowAnalyzer`：

- 试图把概率流沿 outcome graph 传播。
- 计算 directional consistency、gradient position、market momentum、amplification score。
- 这是启发式信号工程，不是已验证预测算法。

`AllocationEngine`：

- 用 decimal odds 和主观概率计算 EV 与 fractional Kelly。
- 有集中度 cap。
- 但默认 `MIN_RETURN_MULTIPLIER = 3.0` 不适合 1X2 胜平负主流 value betting；强行要求赔率大于 3 会排除许多低赔率正期望机会。
- Markowitz 只是非常粗糙的分散约束，不是真正估计协方差矩阵的组合优化。

MCP server：

- 是示范骨架，不是完整 MCP 服务。
- 有旧命名 SPAF。
- 部分 handler 只返回占位信息。

### 2.5 验证结果

执行结果：

- `python3 -X pycache_prefix=/private/tmp/pycache_edp_compile -m compileall src/python mcp examples/python`：通过。
- `python3 -m pytest tests/python`：未运行，当前系统 Python 没有安装 `pytest`。

静态审计发现的严重不一致：

- 测试文件引用 `result.overround`，当前 `TrueProbabilityResult` 字段是 `market_margin`。
- 测试文件引用 `FlowDirection.POSITIVE/NEGATIVE`，当前 Python 枚举是 `UPWARD/DOWNWARD/STABLE`。
- 示例引用 `from spaf import ...`，但当前包是 EDP 命名。
- 示例引用 `flow_report.get_positive_flows()`，当前实现是 `get_upward_flows()`。
- README 示例导入 `FlowAnalyzer`，但 `src/python/__init__.py` 导出的是 `FlowAmplificationEngine`。
- `mcp/server.py` 仍引用 `result.overround` 和旧 SPAF 命名。

结论：代码可编译，但测试、示例、MCP 和 README 的 API 同步存在问题。把它当作生产库使用会踩坑。

## 3. EDP 是否适合足球竞猜

### 3.1 EDP 到底是什么？

EDP 是一个“概率分析与多源信息融合”的研究性原型框架。它不是成熟 AI agent 框架，不是完整概率建模框架，也不是足球竞猜预测系统。

更准确的分类：

| 维度 | 判断 | 置信度 |
|---|---|---|
| AI agent 框架 | 不是。没有 agent runtime、工具规划、记忆、任务执行闭环 | 高 |
| 概率建模框架 | 部分是。包含去水、Beta 更新、Glicko、flow，但不含训练/评估/模型选择 | 高 |
| 信息处理框架 | 部分是。`DomainAwarenessEngine` 是源加权和概率融合原型 | 高 |
| 足球预测系统 | 不是。没有足球数据、特征、模型训练、回测、赔率采集 | 高 |
| 概念性项目 | 是，而且概念包装重于实证验证 | 高 |

### 3.2 它是否包含可迁移到足球竞猜的算法？

可迁移的是组件思想，不是完整算法：

| EDP 组件 | 足球竞猜可用性 | 迁移方式 |
|---|---|---|
| 赔率去水 | 高 | 1X2、让球、大小球的市场基准概率 |
| ProbabilitySnapshot | 高 | 记录开盘、即时、封盘概率快照 |
| Flow analysis | 中 | 观察赔率概率变化，但必须和新闻/阵容/成交量/盘口上下文联动 |
| EvidenceSource weighting | 中高 | 把 Elo、Poisson、赔率、阵容、伤病、天气转成带置信度的信号源 |
| Beta-Binomial | 低到中 | 可用于二分类事件或校准小样本不确定性，不适合直接建模 1X2 全分布 |
| Glicko-2 | 中 | 可改造成国家队实力 rating，但当前实现太简化 |
| Flow amplification | 低 | 需要大量实证验证；默认不进入 MVP 决策 |
| Kelly allocation | 高 | 下注比例计算，但必须用 fractional Kelly、cap、edge threshold |
| Markowitz | 低 | 足球单场互斥市场不是典型资产组合；先不做 |

### 3.3 与“态势感知/全域感知/概率定价/信息不对称/信号传播”的真实关系

实际关系如下：

- 态势感知：在 EDP 中落地为多源概率融合、共识度、异常源检测。可用，但需要真实信号源。
- 全域感知：只是一个总称。除非枚举数据源、字段、时间戳、可靠性和进入模型的方式，否则没有技术含义。
- 概率定价：赔率去水、模型概率、EV、fair odds，这部分是项目核心。
- 信息不对称：EDP 只用“源可靠性”和 Shin 术语触及概念，没有真正识别内幕信息或市场微观结构。
- 信号传播：EDP 的 flow/amplification 是 heuristic。可作为研究假设，不能直接当 alpha。

可落地部分：赔率去水、概率快照、信号源融合、异常检测、Kelly。  
包装术语：全域感知、流向倍增、级联风险、态势评估，如果没有回测和数据证据，都是标签。

### 3.4 应用于世界杯竞猜最可用的思想

最可用思想是“市场为强先验，模型只寻找增量信息”：

1. 市场赔率先去水，得到市场隐含概率。
2. Elo/Poisson/Bayesian/ML 模型只负责回答：相对市场，我是否知道一点市场没充分定价的东西？
3. 阵容、伤病、天气、盘口移动等态势信号必须被记录为时间戳信号，不能事后补进历史。
4. 是否下注不由命中率决定，而由 `model_probability * decimal_odds - 1`、模型校准、样本外回测、资金曲线风险共同决定。

## 4. 从 EDP/态势感知到足球竞猜的概念映射

### 4.1 全域感知：应该感知什么

全域感知在足球竞猜里不是玄学，它应被拆成表结构。

比赛基础：

- `match_id`
- 比赛时间、时区
- 主队/客队/中立场
- 城市、球场、海拔
- 比赛阶段：小组赛、淘汰赛、决赛
- 积分形势：是否必须赢、是否可轮换
- 比分结果、90 分钟比分、加时、点球

球队实力：

- Elo rating、FIFA ranking
- 近 N 场净胜球、进球、失球、xG/xGA
- 预选赛强度和表现
- 大赛经验
- 教练任期、战术稳定性
- 国家队人员磨合程度

球员与阵容：

- 预计首发、实际首发
- 核心球员伤病、停赛、健康状态
- 门将质量
- 中卫组合、后腰屏障、定位球主罚者
- 俱乐部赛季出场时间、疲劳、伤病恢复

战术与风格：

- 阵型
- 高压强度
- 转换速度
- 防线高度
- 定位球攻防
- 对强队/弱队风格适配

环境：

- 天气：温度、湿度、风、降雨
- 草皮/球场
- 旅行距离、时差
- 休息天数
- 赛程密度

市场：

- 1X2 开盘、即时、封盘赔率
- 让球盘、大小球盘
- 不同博彩公司赔率差
- 赔率变化速度
- 市场 margin
- 热门方向是否过热
- 低流动性盘口是否滞后

舆情/热度：

- 新闻量
- 搜索热度
- 社媒情绪
- 公众投注倾向
- 媒体叙事：卫冕冠军、巨星最后一舞、黑马故事等

### 4.2 态势感知：赛前和实时态势如何判断

态势感知 = 判断当前概率是否被新信息改变，以及市场反应是否过度或不足。

可落地任务：

| 态势类型 | 可观测信号 | 模型动作 |
|---|---|---|
| 强队低估 | Elo/Poisson 模型显著高于市场，且无负面阵容信号 | 标记正向 edge，要求回测支持 |
| 弱队高估 | 公众热度高，赔率缩短但模型概率未上升 | 降低模型融合权重或反向观察 |
| 热门过热 | 强队赔率持续下压，市场概率上升但基本面无变化 | 检查 favorite-longshot bias 和 closing line |
| 赔率异常 | 单公司明显偏离市场均值 | 检查是否 stale odds，不自动下注 |
| 阵容突变 | 核心球员缺阵、门将替换、轮换 | 触发概率重估 |
| 市场反应不足 | 新闻时间早于赔率移动，模型修正后仍有 EV | 标记 candidate value bet |
| 盘口联动不一致 | 1X2 支持强队，但大小球没有同步 | 检查战术/总进球模型 |

关键原则：所有态势信号必须有 `observed_at` 时间戳。没有时间戳的“赛前已知信息”很容易变成未来数据泄漏。

### 4.3 概率定价

#### 4.3.1 市场隐含概率

Decimal odds `d_i` 的原始隐含概率：

```text
pi_i = 1 / d_i
overround = sum(pi_i) - 1
```

比例去水：

```text
p_market_i = pi_i / sum(pi_j)
```

Shin 去水可作为第二种方法，但必须与比例法比较；Shin 不应被默认视为更准确。

#### 4.3.2 胜平负概率

胜平负是三分类：

```text
P(home_win), P(draw), P(away_win), sum = 1
```

建模方式：

- 市场去水概率。
- Elo rating 差映射到胜/平/负。
- Poisson 进球分布求和。
- 机器学习多分类概率。
- 融合模型。

#### 4.3.3 让球概率

让球本质是净胜球分布：

```text
goal_diff = goals_home - goals_away
P(home handicap win) = P(goal_diff + handicap > 0)
```

亚洲让球还需要处理半赢、走水、半输。MVP 第一阶段不做，后续用比分分布扩展。

#### 4.3.4 大小球概率

大小球来自总进球分布：

```text
total_goals = goals_home + goals_away
P(over line) = P(total_goals > line)
P(under line) = P(total_goals < line)
```

2.5 球最简单；2.0/2.25/2.75 需要拆盘。

#### 4.3.5 比分分布

Poisson 基础形式：

```text
P(score = i:j) = Pois(i; lambda_home) * Pois(j; lambda_away)
```

胜平负：

```text
P(home_win) = sum_{i>j} P(i:j)
P(draw) = sum_{i=j} P(i:j)
P(away_win) = sum_{i<j} P(i:j)
```

Dixon-Coles 修正低比分相关性，尤其影响 0-0、1-0、0-1、1-1。

### 4.4 信息不对称

可能没有充分反映的信息：

- 临近开赛阵容变动，尤其门将、中卫、核心前锋、定位球核心。
- 小国家队的伤病与内部状态，覆盖少、市场慢。
- 轮换动机：已出线、必须争净胜球、淘汰赛保守策略。
- 气候和旅行适应：湿热、高海拔、跨洲旅行。
- 战术 matchup：强队控球但怕转换，弱队防空弱。
- 盘口低流动性或小公司 stale odds。

通常已充分定价的信息：

- FIFA 排名、Elo 大方向、传统强弱。
- 明星球员公开伤病。
- 大赛主办国身份。
- 小组积分形势。
- 公开新闻里的明显利好利空。
- 主流公司临近封盘赔率。

避免误判优势的方法：

1. 把市场 closing odds 作为强基准。
2. 只相信样本外提升，而不是个案解释。
3. 任何公开信息都假定市场已经知道，除非赔率没有反应且有时间戳证据。
4. 用 closing line value 检查下注是否买到比封盘更好的价格。

### 4.5 Kelly Criterion

Decimal odds `d`，模型胜率 `p`：

```text
EV = p * d - 1
full_kelly = (p * d - 1) / (d - 1)
fractional_kelly = kappa * full_kelly
```

下注条件：

```text
p * d > 1 + edge_threshold
model_probability - market_probability > probability_threshold
model_confidence >= confidence_threshold
```

建议默认：

- `kappa = 0.25`，即 quarter Kelly。
- 单注 cap：本金 0.5% 到 2%。
- 单比赛总 exposure cap：本金 2% 到 3%。
- 若模型未校准或样本少，继续降低到 0.1 Kelly 或 flat stake 回测。
- 若多个盘口高度相关，不能把每个 Kelly 独立相加。

### 4.6 Nash Equilibrium / 博弈论

博弈论在本项目中是概念参考，不是 MVP 核心。

可能有用的地方：

- 球队战术策略：淘汰赛是否保守、领先后是否降低节奏、点球大战风险偏好。
- 市场参与者互动：博彩公司调水、公众追热门、套利者打掉 stale odds。
- 多盘口一致性：1X2、让球、大小球、比分盘应满足某种无套利一致性。

不应强行使用的地方：

- 不要把 Nash equilibrium 写进模型名却没有可估计参数。
- 不要假设球队策略可被准确观测。
- 不要把市场错价解释成博弈论，除非有赔率时间序列和订单流证据。

## 5. 世界杯竞猜市场的建模对象

MVP 只做 90 分钟常规时间 1X2。淘汰赛晋级、加时、点球不进入第一版。

后续扩展市场：

| 市场 | 建模对象 | 所需分布 |
|---|---|---|
| 1X2 | 90 分钟胜/平/负 | 三分类概率 |
| Asian handicap | 净胜球超过盘口 | 净胜球分布 |
| Over/Under | 总进球超过盘口 | 总进球分布 |
| Correct score | 精确比分 | 双变量比分分布 |
| To qualify | 晋级概率 | 90 分钟 + 加时 + 点球模型 |
| Group stage futures | 小组出线/排名 | 蒙特卡洛锦标赛模拟 |

## 6. 推荐的数据源

优先级原则：公开、可下载、可复现优先；需要登录、付费、抓取网页、许可不明的数据只能做增强，不做核心结论。

| 数据源 | 获取方式 | 更新频率 | 可靠性 | 缺点 | MVP |
|---|---|---|---|---|---|
| openfootball/worldcup <https://github.com/openfootball/worldcup> | GitHub Football.TXT | 社区更新 | 中高，CC0 | 格式需解析；缺 odds/xG | 是，赛程和历史世界杯 |
| martj42/international_results <https://github.com/martj42/international_results> | GitHub CSV | 社区更新 | 中高，CC0 | 众包，需校验；历史队名处理需注意 | 是，Elo/Poisson 训练 |
| FIFA Men's Ranking <https://inside.fifa.com/fifa-world-ranking/men> | 官方页面/下载 | 官方 ranking window | 高 | 历史批量数据获取麻烦 | 是，作为特征 |
| World Football Elo Ratings <https://www.eloratings.net/> | 网站/页面抓取或手动快照 | 按比赛更新 | 中高 | 非官方；API 不稳定 | 是，MVP rating |
| football-data.co.uk <https://www.football-data.co.uk/> | CSV/XLSX 下载 | 按赛事/赛季 | 中高 | 世界杯覆盖与字段需逐文件确认；许可需记录 | 是，赔率基准优先 |
| The Odds API <https://the-odds-api.com/> | JSON API | 实时/近实时；历史付费 | 高 | 历史 odds 需要付费；免费额度有限 | 可选，生产化 |
| StatsBomb Open Data <https://github.com/statsbomb/open-data> | GitHub JSON | 不定期 | 高 | 赛事覆盖有限；许可需署名 | 后续，xG/事件数据 |
| Open-Meteo Historical Weather API <https://open-meteo.com/en/docs/historical-weather-api> | HTTP API/CSV/XLSX | 历史数据日更/延迟 | 高 | 需要球场坐标；天气对赛果增益可能小 | 后续 |
| FIFA Match Centre <https://www.fifa.com/> | 官方页面 | 实时/赛后 | 高 | 自动化获取难度和条款需确认 | 后续，阵容 |
| FBref/Transfermarkt/worldfootballR | R 包或网页 | 不定 | 中 | worldfootballR 已归档；抓取条款风险；字段稳定性差 | 不做核心 |
| OddsPortal 等赔率聚合站 | 网页 | 快 | 中 | 无官方 API，复现和许可弱 | 不做核心 |

公开源核实摘要：

- openfootball/worldcup 明确提供 World Cup 和 qualifiers 的公开数据，包含 2026、2022、2018、2014 等目录，许可证为 CC0。
- StatsBomb Open Data 提供 JSON 结构：competitions、matches、events、lineups、360，适合后续做事件级特征。
- football-data.co.uk 自称提供免费、computer-ready 的历史结果与赔率 Excel/CSV，并有 World Cup XLSX 资源入口。
- The Odds API 提供多博彩公司 odds、head-to-head、spreads、totals、JSON、历史赔率付费层级。
- FIFA ranking 页面显示官方 ranking 更新时间，例如本次访问时 latest men's ranking 的 last official update 为 2026-06-11，next official update 为 2026-07-20。
- Open-Meteo Historical Weather API 提供 1940 至今再分析历史天气数据，包含温度、湿度、降雨、风速等变量。

## 7. 推荐的 MVP 模型

### 7.1 MVP 输出字段

每场比赛输出：

```text
match_id
match_time
team_a
team_b
market_home_odds
market_draw_odds
market_away_odds
market_home_prob_devig
market_draw_prob_devig
market_away_prob_devig
model_home_prob
model_draw_prob
model_away_prob
delta_home
delta_draw
delta_away
value_bet_flag
value_bet_side
expected_value
fractional_kelly_fraction
risk_level
reason
no_bet_reason
data_timestamp
odds_timestamp
model_version
```

### 7.2 市场基准模型

输入：同一时间点的 1X2 decimal odds。  
步骤：

1. `pi_i = 1 / odds_i`
2. `p_market_i = pi_i / sum(pi_j)`
3. 记录 overround。
4. 输出 market probability。

这是所有模型必须击败的基准。若模型不能优于市场基准，项目应直接承认没有 alpha。

### 7.3 Elo 模型

基本思想：

```text
rating_diff = Elo_A - Elo_B + home_advantage
P(A not lose / expected score) = logistic(rating_diff / scale)
```

三分类拆解：

- 先估计主队 expected score。
- 再估计 draw probability，常用方式是让平局概率随实力差扩大而下降。
- 剩余概率按 expected score 分配给胜负。

世界杯处理：

- 大多数比赛是中立场，`home_advantage = 0`。
- 主办国比赛单独加主场优势。
- 近期状态可用 rating 更新速度、近 N 场加权结果、预选赛表现。
- 比赛重要性可调整 rating 更新 K 值，但预测时要避免未来结果。

### 7.4 Poisson / Dixon-Coles 进球模型

输入：

- 历史国家队比赛比分。
- 比赛强度：世界杯、洲际杯、预选赛、友谊赛权重不同。
- 中立场/主场。
- 球队进攻强度、防守强度。

基础形式：

```text
goals_A ~ Poisson(lambda_A)
goals_B ~ Poisson(lambda_B)
```

从比分矩阵得到：

- 胜平负概率。
- 大小球概率。
- 让球概率。
- 最可能比分。

Dixon-Coles 修正低比分相关性，尤其在足球这种低比分运动中重要。MVP 可先实现普通 Poisson，第二版加入 Dixon-Coles。

### 7.5 Bayesian 模型

适合世界杯的原因：

- 国家队比赛样本少。
- 球队强度不确定性大。
- 阵容变化和大赛环境使参数不稳定。

可建模参数：

- 球队攻击强度 `attack_team`
- 球队防守强度 `defense_team`
- 主场/中立场效应
- 大赛强度
- 近期状态随机效应

优势：

- 输出完整不确定性。
- 小样本下可以 shrinkage，避免过度相信近期战绩。
- 可把 Elo/FIFA ranking 作为先验。

问题：

- 实现复杂。
- 训练慢。
- 解释和回测难度高。
- 如果赔率已很强，Bayesian 模型未必产生可交易增量。

### 7.6 机器学习模型

候选：

- Logistic Regression：强 baseline，可解释，低过拟合。
- Random Forest：可捕捉非线性，但概率校准通常差。
- XGBoost / LightGBM：表格数据强，但世界杯样本太少，必须扩大到国际赛事并严格时间切分。

特征：

- Elo diff、FIFA rank diff。
- 近 N 场进球、失球、净胜球、xG。
- 中立场、主场、旅行距离、休息天数。
- 赔率去水概率。
- 赔率变动：开盘到即时、即时到封盘。
- 阵容伤病变量。
- 赛程动机。

防过拟合：

- 按时间切分，不随机切分。
- 训练数据只使用赛前可得信息。
- 不用赛后 xG 预测赛前结果。
- 做 calibration。
- 与市场基准比较 log loss/Brier，而不是只看 accuracy。

### 7.7 赔率融合模型

不要假装市场不存在。最佳第一版融合方式：

```text
p_final = w_market * p_market + w_elo * p_elo + w_poisson * p_poisson
```

权重由历史回测调参，约束：

- `w_market` 初始不低于 0.50。
- 所有概率归一化。
- 对极端模型概率做 shrinkage。

更好的方式是 log-odds blending：

```text
logit(p_final_i) = a + b1*logit(p_market_i) + b2*model_edge_i + ...
```

但三分类需要 multinomial logistic 或 softmax。

### 7.8 态势感知增强模型

只在 MVP 稳定后加入：

- 阵容变动信号。
- 伤病/停赛。
- 新闻强度和可靠性。
- 赔率变化速度。
- 热门过热指标。
- 赛程疲劳。
- 天气。

验证标准：加入信号后，样本外 log loss/Brier 改善，且资金曲线风险没有恶化。否则删除。

## 8. 回测设计

### 8.1 数据切分

禁止随机切分。推荐：

1. 训练：历史国际比赛和早期世界杯。
2. 验证：若干届大赛或固定年份窗口。
3. 测试：后续世界杯或完全留出的赛事。

更严谨：

- rolling-origin evaluation。
- 每场比赛只使用比赛开始前已经存在的数据。
- odds 使用下注时点 odds，不用封盘 odds 假装赛前可交易。

### 8.2 预测质量指标

Accuracy：

- 可以看，但不能作为主指标。
- 三分类足球里，永远买热门也能有看起来不错的 accuracy。

Brier Score：

```text
Brier = mean(sum_i (p_i - y_i)^2)
```

Log Loss：

```text
LogLoss = -mean(log(p_true_outcome))
```

Calibration：

- 分桶校准曲线。
- Expected Calibration Error。
- 例如预测 40% 的事件，长期是否约 40% 发生。

### 8.3 交易质量指标

必须同时评估：

- ROI。
- 最大回撤。
- 命中率。
- 平均赔率。
- 盈亏分布。
- 连续亏损次数。
- flat stake 资金曲线。
- fractional Kelly 资金曲线。
- closing line value。
- 每个赔率区间的表现。
- 每个市场方向的表现：主胜、平、客胜。

### 8.4 市场对比

基准：

1. 模型 vs 去水市场概率。
2. 模型 vs 随机下注。
3. 模型 vs 永远买热门。
4. 模型 vs 永远不下注。
5. 模型 vs 只买 closing line favorite。

强结论门槛：

- 预测 log loss 优于市场。
- 校准不差。
- ROI 在样本外为正。
- 回撤可承受。
- 下注数量不是少到只靠运气。
- closing line value 为正。

### 8.5 风险控制

主要失败点：

- 世界杯样本极小，一届只有几十场。
- 使用赛后数据造成泄漏。
- 用封盘 odds 回测开赛前策略。
- 只挑选事后成功盘口。
- 赔率数据缺失导致选择偏差。
- 阵容数据无法复现。
- 模型概率未校准，Kelly 放大错误。
- 市场赔率已包含大多数公开信息。

## 9. 工程目录设计

已初始化目录：

```text
worldcup-betting-edp/
├── README.md
├── AGENTS.md
├── ROADMAP.md
├── TASKS.md
├── DECISIONS.md
├── DATA_SOURCES.md
├── MODEL_SPEC.md
├── BACKTEST_SPEC.md
├── pyproject.toml
├── data/
│   ├── raw/
│   ├── processed/
│   └── external/
├── notebooks/
├── src/
│   └── worldcup_betting_edp/
│       ├── data/
│       ├── features/
│       ├── models/
│       ├── market/
│       ├── betting/
│       ├── backtest/
│       └── reports/
├── configs/
├── tests/
└── reports/
```

目录职责：

| 目录 | 作用 |
|---|---|
| `data/raw` | 原始下载数据，只追加、不手工改 |
| `data/processed` | 标准化后的建模数据 |
| `data/external` | 第三方数据快照、元数据、许可说明 |
| `notebooks` | 探索性分析，不放核心生产逻辑 |
| `src/worldcup_betting_edp/data` | 数据下载、解析、校验 |
| `src/worldcup_betting_edp/features` | Elo、Poisson 输入、市场信号、赛程特征 |
| `src/worldcup_betting_edp/models` | 市场、Elo、Poisson、Bayesian、ML、融合模型 |
| `src/worldcup_betting_edp/market` | 赔率去水、盘口快照、概率转换 |
| `src/worldcup_betting_edp/betting` | EV、Kelly、risk level、下注规则 |
| `src/worldcup_betting_edp/backtest` | 时间切分、指标、资金曲线 |
| `src/worldcup_betting_edp/reports` | 自动生成报告 |
| `configs` | 数据源、模型参数、回测参数 |
| `tests` | 单元测试、回归测试 |
| `reports` | 人类可读研究报告 |

## 10. 第一阶段任务清单

已完成：

- 初始化项目目录结构。
- 研究 EDP README、项目结构、依赖、主要代码、示例、测试。
- 核实 GitHub 基本元数据。
- 判断 EDP 的真实技术含义和可迁移部分。
- 将 EDP/态势感知概念映射到足球竞猜变量、模型和回测规则。
- 设计 MVP。
- 设计回测框架。
- 输出本报告。

下一阶段建议：

1. 创建 Python 包骨架和依赖文件。
2. 实现 `market/devig.py`：比例去水、Shin 去水、overround。
3. 实现 `betting/kelly.py`：EV、fair odds、fractional Kelly、cap。
4. 下载 openfootball/worldcup 和 martj42 international_results。
5. 建立统一 `matches` schema。
6. 实现市场基准模型。
7. 实现 Elo baseline。
8. 实现 Poisson baseline。
9. 做一个小型 historical World Cup 回测。

## 11. 风险与失败点

最可能失败的不是代码，而是没有真实 edge。

关键风险：

- 市场已经非常强，模型未必能击败 closing odds。
- 世界杯比赛少，统计显著性差。
- 阵容和伤病数据复现困难。
- 赔率历史数据可能需要付费或许可限制。
- 小样本下 Kelly 会过度自信。
- Poisson 假设独立进球，淘汰赛和低比分策略下偏差明显。
- Elo 对风格 matchup 捕捉弱。
- ML 模型在国家队样本上极易过拟合。
- 公开信息容易被误判为优势。
- EDP 的 flow/amplification 若不回测，很可能只是漂亮术语。

如果模型不能击败市场赔率，应直接停在“研究工具”定位，不进入下注决策。

## 12. 下一步行动计划

建议 Phase 2 用最小闭环推进：

1. 数据层：下载并锁定两个公开数据源：openfootball/worldcup、martj42/international_results。
2. 市场层：找到可复现历史 World Cup odds 源；优先 football-data.co.uk World Cup XLSX，如字段不足则记录缺口。
3. 模型层：实现 market baseline、Elo、Poisson。
4. 输出层：生成单场 1X2 预测表。
5. 回测层：计算 Brier、Log Loss、ROI、max drawdown、Kelly curve。
6. 审计层：每个特征必须有 `available_at`，防止未来数据泄漏。

Phase 2 的成功标准：

- 能对历史世界杯比赛生成赛前概率。
- 能和市场去水概率逐场比较。
- 能复现实验。
- 能明确说出模型是否优于市场。

## 附录 A：EDP 可借鉴与应排除部分

可借鉴：

- `ProbabilitySnapshot` 思路：赔率快照时间序列。
- `calculate_true_probability` 思路：市场概率基准。
- `DomainAwarenessEngine` 思路：信号源可靠性、置信度、时间衰减。
- `detect_anomalies` 思路：异常源或异常赔率移动。
- `AllocationLeg.kelly_fraction` 思路：fractional Kelly。

应排除或重写：

- 当前 Glicko-2：实现过简化，需重写或用成熟 rating 包。
- 当前 FlowAnalyzer：枚举和新代码不一致，不应直接用。
- 当前 FlowAmplification：没有验证，不进 MVP。
- 当前 MCP server：占位多，不进 MVP。
- 当前测试：API 过期，不能作为质量证明。
- 当前 `MIN_RETURN_MULTIPLIER = 3.0`：不适合一般 value betting。

## 附录 B：核心公式

市场去水：

```text
pi_i = 1 / odds_i
p_market_i = pi_i / sum(pi_j)
overround = sum(pi_i) - 1
```

Expected value：

```text
EV = p_model * decimal_odds - 1
```

Kelly：

```text
full_kelly = (p_model * decimal_odds - 1) / (decimal_odds - 1)
fractional_kelly = kappa * max(full_kelly, 0)
```

Poisson 比分：

```text
P(i:j) = Pois(i; lambda_A) * Pois(j; lambda_B)
```

三分类 Brier：

```text
Brier = mean(sum_i (p_i - y_i)^2)
```

Log Loss：

```text
LogLoss = -mean(log(p_observed_outcome))
```
