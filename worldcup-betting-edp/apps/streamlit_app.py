"""Streamlit dashboard for World Cup betting research workflows."""

from __future__ import annotations

from datetime import datetime, time, timezone
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from worldcup_betting_edp.backtest import run_batch_backtest
from worldcup_betting_edp.data import (
    PredictionInput,
    load_backtest_manifest_path,
    load_backtest_manifest_text,
    load_prediction_input_text,
)
from worldcup_betting_edp.domain import Match, ModelProbabilities, OddsSnapshot
from worldcup_betting_edp.models import ResidualEdgeConfig
from worldcup_betting_edp.reports import evaluate_single_match


OUTCOME_LABELS = {
    "home": "Home / 主胜",
    "draw": "Draw / 平局",
    "away": "Away / 客胜",
}

SOURCE_LABELS = {
    "market": "Market / 市场",
    "model": "Model / 模型",
    "fundamental": "Fundamental / 基本面",
    "final": "Final / 最终",
}

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEMO_MANIFEST_PATH = PROJECT_ROOT / "examples" / "demo_backtest_manifest.json"


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 1180px;
            padding-top: 2.25rem;
            padding-bottom: 3rem;
        }
        h1 {
            letter-spacing: 0;
        }
        [data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #e6e8ef;
            border-radius: 8px;
            padding: 14px 16px;
            box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
        }
        [data-testid="stMetricLabel"] {
            color: #667085;
            font-size: 0.85rem;
        }
        [data-testid="stMetricValue"] {
            color: #101828;
            font-size: 1.45rem;
        }
        div[data-testid="stDataFrame"] {
            border: 1px solid #e6e8ef;
            border-radius: 8px;
        }
        .section-note {
            color: #667085;
            font-size: 0.92rem;
            margin-top: -0.35rem;
            margin-bottom: 0.75rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _combine_datetime(match_date: object, match_time: time) -> datetime:
    if not hasattr(match_date, "year"):
        raise ValueError("invalid match date")
    return datetime.combine(match_date, match_time, tzinfo=timezone.utc)


def _parse_sidebar_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("datetime must use ISO-8601 format") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _default_prediction_input() -> PredictionInput:
    match = Match(
        match_id="demo-2026-final",
        match_time=datetime(2026, 7, 19, 15, 0, tzinfo=timezone.utc),
        home_team="Team A",
        away_team="Team B",
        stage="Final",
        neutral=True,
    )
    odds = OddsSnapshot(
        match_id=match.match_id,
        captured_at=datetime(2026, 6, 18, 7, 32, 42, tzinfo=timezone.utc),
        bookmaker="demo_book",
        home=2.20,
        draw=3.25,
        away=3.60,
    )
    model = ModelProbabilities.from_1x2(
        match_id=match.match_id,
        model_name="manual_research_model",
        home=0.49,
        draw=0.27,
        away=0.24,
    )
    return PredictionInput(match=match, odds_snapshot=odds, model_probabilities=model)


def _load_sidebar_prediction_input() -> PredictionInput | None:
    st.sidebar.header("Input File / 输入文件")
    uploaded_file = st.sidebar.file_uploader("Upload JSON / 上传JSON", type=["json"])
    st.sidebar.caption(
        "Optional. Use examples/demo_single_match.json as the format reference. / "
        "可选。可参考 examples/demo_single_match.json。"
    )
    if uploaded_file is None:
        return _default_prediction_input()

    try:
        prediction_input = load_prediction_input_text(uploaded_file.getvalue().decode("utf-8"))
    except UnicodeDecodeError as exc:
        st.sidebar.error(f"Uploaded file must be UTF-8 JSON. / 上传文件必须是 UTF-8 JSON。{exc}")
        return None
    except ValueError as exc:
        st.sidebar.error(f"Invalid prediction JSON. / 预测 JSON 无效：{exc}")
        return None

    st.sidebar.success("Loaded JSON input. / 已加载 JSON 输入。")
    return prediction_input


def _probability_dataframe(row: dict[str, object]) -> pd.DataFrame:
    records = []
    is_residual = row.get("probability_model_mode") == "market_residual"
    for outcome in ("home", "draw", "away"):
        records.append(
            {
                "Outcome": OUTCOME_LABELS[outcome],
                "Source / 来源": SOURCE_LABELS["market"],
                "Probability (%) / 概率(%)": float(row[f"market_{outcome}_prob_devig"]) * 100.0,
            }
        )
        if is_residual:
            records.append(
                {
                    "Outcome": OUTCOME_LABELS[outcome],
                    "Source / 来源": SOURCE_LABELS["fundamental"],
                    "Probability (%) / 概率(%)": float(row[f"fundamental_{outcome}_prob"])
                    * 100.0,
                }
            )
            records.append(
                {
                    "Outcome": OUTCOME_LABELS[outcome],
                    "Source / 来源": SOURCE_LABELS["final"],
                    "Probability (%) / 概率(%)": float(row[f"model_{outcome}_prob"]) * 100.0,
                }
            )
        else:
            records.append(
                {
                    "Outcome": OUTCOME_LABELS[outcome],
                    "Source / 来源": SOURCE_LABELS["model"],
                    "Probability (%) / 概率(%)": float(row[f"model_{outcome}_prob"]) * 100.0,
                }
            )
    return pd.DataFrame.from_records(records)


def _decision_dataframe(row: dict[str, object]) -> pd.DataFrame:
    records = []
    is_residual = row.get("probability_model_mode") == "market_residual"
    model_probability_column = (
        "Final Prob (%) / 最终概率(%)"
        if is_residual
        else "Model Prob (%) / 模型概率(%)"
    )
    for outcome in ("home", "draw", "away"):
        reason = str(row[f"{outcome}_decision_reason"])
        record = {
            "Outcome / 结果": OUTCOME_LABELS[outcome],
            "Odds / 赔率": float(row[f"market_{outcome}_odds"]),
            "Market Prob (%) / 市场概率(%)": float(row[f"market_{outcome}_prob_devig"]) * 100.0,
        }
        if is_residual:
            record["Fundamental Prob (%) / 基本面概率(%)"] = (
                float(row[f"fundamental_{outcome}_prob"]) * 100.0
            )
        record[model_probability_column] = float(row[f"model_{outcome}_prob"]) * 100.0
        if is_residual:
            record["Residual Adj (%) / 残差修正(%)"] = (
                float(row[f"residual_{outcome}_adjustment"]) * 100.0
            )
        record["Edge (%) / 概率差(%)"] = float(row[f"delta_{outcome}"]) * 100.0
        record["EV (%)"] = float(row[f"{outcome}_ev"]) * 100.0
        record["Kelly (%) / 凯利(%)"] = float(row[f"{outcome}_kelly_fraction"]) * 100.0
        record["Reason / 理由"] = _display_reason(reason)
        records.append(record)
    return pd.DataFrame.from_records(records)


def _batch_scoring_dataframe(rows: list[dict[str, object]]) -> pd.DataFrame:
    records = []
    for row in rows:
        records.append(
            {
                "Match ID / 比赛ID": row["match_id"],
                "Actual / 实际结果": OUTCOME_LABELS[str(row["actual_result"])],
                "Model Brier": row["model_brier_score"],
                "Market Brier": row["market_brier_score"],
                "Model Log Loss": row["model_log_loss"],
                "Market Log Loss": row["market_log_loss"],
                "Model Beats Market Brier / 模型Brier胜市场": row["model_beats_market_brier"],
                "Model Beats Market Log Loss / 模型LogLoss胜市场": row["model_beats_market_log_loss"],
            }
        )
    return pd.DataFrame.from_records(records)


def _batch_settlement_dataframe(rows: list[dict[str, object]]) -> pd.DataFrame:
    records = []
    for row in rows:
        bet_outcome = row["bet_outcome"]
        records.append(
            {
                "Match ID / 比赛ID": row["match_id"],
                "Bet Placed / 已下注": row["bet_placed"],
                "Bet Outcome / 下注方向": OUTCOME_LABELS[str(bet_outcome)] if bet_outcome else "No bet / 不下注",
                "Actual / 实际结果": OUTCOME_LABELS[str(row["actual_result"])],
                "Odds / 赔率": row["decimal_odds"],
                "Stake / 注额": row["stake"],
                "Profit / 盈亏": row["profit"],
                "ROI": row["roi"],
                "Hit / 命中": row["hit"],
            }
        )
    return pd.DataFrame.from_records(records)


def _kelly_curve_dataframe(points: list[dict[str, object]]) -> pd.DataFrame:
    records = []
    for index, point in enumerate(points, start=1):
        records.append(
            {
                "Step / 步骤": index,
                "Match ID / 比赛ID": point["match_id"],
                "Bankroll / 本金": point["bankroll_end"],
                "Drawdown / 回撤": float(point["drawdown"]) * 100.0,
                "Stake / 注额": point["stake"],
                "Profit / 盈亏": point["profit"],
                "Bet Placed / 已下注": point["bet_placed"],
            }
        )
    return pd.DataFrame.from_records(records)


def _format_percent(value: float) -> str:
    return f"{value:.2%}"


def _format_optional_percent(value: object) -> str:
    if value is None:
        return "n/a"
    return _format_percent(float(value))


def _format_number(value: object, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.{digits}f}"


def _display_reason(reason: str) -> str:
    """Add a compact Chinese explanation to algorithm-generated reasons."""
    if reason.startswith("positive edge:"):
        return reason.replace("positive edge:", "positive edge / 正向优势:", 1)
    if reason.startswith("no bet: probability edge"):
        return reason.replace("no bet: probability edge", "no bet / 不下注: probability edge / 概率优势", 1)
    if reason.startswith("no bet: EV"):
        return reason.replace("no bet: EV", "no bet / 不下注: EV / 期望值", 1)
    if reason.startswith("no bet: Kelly"):
        return reason.replace("no bet:", "no bet / 不下注:", 1)
    return reason


def _build_sidebar_inputs() -> tuple[
    Match,
    OddsSnapshot,
    ModelProbabilities,
    bool,
    ResidualEdgeConfig | None,
] | None:
    defaults = _load_sidebar_prediction_input()
    if defaults is None:
        st.info("Fix the uploaded JSON file or remove it. / 请修复上传的 JSON 文件，或移除该文件。")
        return None

    default_match = defaults.match
    default_odds = defaults.odds_snapshot
    default_model = defaults.model_probabilities
    default_match_time = default_match.match_time.astimezone(timezone.utc)

    st.sidebar.header("Match / 比赛信息")
    match_id = st.sidebar.text_input("Match ID / 比赛ID", value=default_match.match_id)
    home_team = st.sidebar.text_input("Home / Team A / 主队或球队A", value=default_match.home_team)
    away_team = st.sidebar.text_input("Away / Team B / 客队或球队B", value=default_match.away_team)
    stage = st.sidebar.text_input("Stage / 阶段", value=default_match.stage)
    neutral = st.sidebar.checkbox("Neutral venue / 中立场", value=default_match.neutral)
    match_date = st.sidebar.date_input("Match date / 比赛日期", value=default_match_time.date())
    match_time = st.sidebar.time_input(
        "Match time UTC / UTC比赛时间",
        value=default_match_time.time().replace(tzinfo=None),
    )

    st.sidebar.header("Market Odds / 市场赔率")
    bookmaker = st.sidebar.text_input("Bookmaker / 博彩公司", value=default_odds.bookmaker)
    odds_captured_at = st.sidebar.text_input(
        "Odds captured at UTC / UTC赔率采集时间",
        value=default_odds.captured_at.astimezone(timezone.utc).isoformat(),
    )
    odds_home = st.sidebar.number_input("Home odds / 主胜赔率", min_value=1.01, value=float(default_odds.home), step=0.01)
    odds_draw = st.sidebar.number_input("Draw odds / 平局赔率", min_value=1.01, value=float(default_odds.draw), step=0.01)
    odds_away = st.sidebar.number_input("Away odds / 客胜赔率", min_value=1.01, value=float(default_odds.away), step=0.01)

    st.sidebar.header("Model Mode / 模型模式")
    model_mode = st.sidebar.selectbox(
        "Probability mode / 概率模式",
        ["Direct Model / 直接模型概率", "Market Residual / 市场残差模型"],
        index=0,
    )
    use_residual_model = model_mode.startswith("Market Residual")

    st.sidebar.header(
        "Fundamental Probabilities / 基本面概率"
        if use_residual_model
        else "Model Probabilities / 模型概率"
    )
    st.sidebar.caption(
        "In residual mode these are fundamental probabilities; final probabilities are "
        "market-anchored. / 残差模式下这里输入的是基本面概率，最终概率会锚定市场概率。"
        if use_residual_model
        else "Enter probabilities as percentages. They must sum to 100%. / 请输入百分比，三项合计必须为100%。"
    )
    model_name = st.sidebar.text_input(
        "Fundamental model name / 基本面模型名称"
        if use_residual_model
        else "Model name / 模型名称",
        value=default_model.model_name,
    )
    model_home_pct = st.sidebar.number_input(
        "Home model probability / 主胜模型概率",
        0.0,
        100.0,
        float(default_model.probabilities["home"] * 100.0),
        0.5,
    )
    model_draw_pct = st.sidebar.number_input(
        "Draw model probability / 平局模型概率",
        0.0,
        100.0,
        float(default_model.probabilities["draw"] * 100.0),
        0.5,
    )
    model_away_pct = st.sidebar.number_input(
        "Away model probability / 客胜模型概率",
        0.0,
        100.0,
        float(default_model.probabilities["away"] * 100.0),
        0.5,
    )
    probability_total = model_home_pct + model_draw_pct + model_away_pct
    residual_config = None
    if use_residual_model:
        st.sidebar.header("Residual Rules / 残差规则")
        fundamental_gap_weight = st.sidebar.slider(
            "Fundamental gap weight / 基本面差异权重",
            min_value=0.0,
            max_value=1.0,
            value=0.25,
            step=0.05,
            format="%.2f",
        )
        max_abs_adjustment = st.sidebar.slider(
            "Max adjustment per outcome / 单项最大修正",
            min_value=0.0,
            max_value=0.10,
            value=0.05,
            step=0.005,
            format="%.3f",
        )
        residual_config = ResidualEdgeConfig(
            fundamental_gap_weight=float(fundamental_gap_weight),
            max_abs_adjustment_per_outcome=float(max_abs_adjustment),
        )

    st.sidebar.header("Bet Rules / 下注规则")
    probability_edge_threshold = st.sidebar.slider(
        "Probability edge threshold / 概率优势阈值",
        min_value=0.0,
        max_value=0.10,
        value=0.02,
        step=0.005,
        format="%.3f",
    )
    ev_threshold = st.sidebar.slider(
        "EV threshold / 期望值阈值",
        min_value=0.0,
        max_value=0.10,
        value=0.01,
        step=0.005,
        format="%.3f",
    )
    kelly_fraction = st.sidebar.slider(
        "Kelly fraction / 凯利折扣",
        min_value=0.05,
        max_value=1.00,
        value=0.25,
        step=0.05,
        format="%.2f",
    )
    stake_cap = st.sidebar.slider(
        "Stake cap / 单注上限",
        min_value=0.001,
        max_value=0.10,
        value=0.02,
        step=0.001,
        format="%.3f",
    )

    if abs(probability_total - 100.0) > 1e-9:
        st.sidebar.error(f"Model probabilities sum to {probability_total:.1f}%, not 100%. / 模型概率合计为 {probability_total:.1f}%，不是100%。")
        st.info("Adjust the model probabilities in the sidebar until they sum to 100%. / 请调整侧边栏模型概率，使三项合计为100%。")
        return None

    try:
        parsed_odds_captured_at = _parse_sidebar_datetime(odds_captured_at)
    except ValueError as exc:
        st.sidebar.error(f"Invalid odds captured time. / 赔率采集时间无效：{exc}")
        st.info("Use an ISO-8601 datetime such as 2026-06-18T07:32:42+00:00. / 请使用 ISO-8601 时间格式。")
        return None

    match = Match(
        match_id=match_id.strip(),
        match_time=_combine_datetime(match_date, match_time),
        home_team=home_team.strip(),
        away_team=away_team.strip(),
        stage=stage.strip() or "unknown",
        neutral=neutral,
    )
    odds = OddsSnapshot(
        match_id=match.match_id,
        captured_at=parsed_odds_captured_at,
        bookmaker=bookmaker.strip() or "unknown",
        home=float(odds_home),
        draw=float(odds_draw),
        away=float(odds_away),
    )
    model = ModelProbabilities.from_1x2(
        match_id=match.match_id,
        model_name=model_name.strip() or "manual_ui_model",
        home=float(model_home_pct) / 100.0,
        draw=float(model_draw_pct) / 100.0,
        away=float(model_away_pct) / 100.0,
    )

    st.session_state["bet_rules"] = {
        "probability_edge_threshold": probability_edge_threshold,
        "ev_threshold": ev_threshold,
        "kelly_fraction": kelly_fraction,
        "stake_cap": stake_cap,
    }
    return match, odds, model, use_residual_model, residual_config


def _render_single_match_page() -> None:
    inputs = _build_sidebar_inputs()
    if inputs is None:
        return

    match, odds, model, use_residual_model, residual_config = inputs
    rules = st.session_state["bet_rules"]
    report = evaluate_single_match(
        match=match,
        odds_snapshot=odds,
        model_probabilities=model,
        probability_edge_threshold=float(rules["probability_edge_threshold"]),
        ev_threshold=float(rules["ev_threshold"]),
        kelly_fraction=float(rules["kelly_fraction"]),
        stake_cap=float(rules["stake_cap"]),
        use_market_residual_model=use_residual_model,
        residual_config=residual_config,
    )
    row = report.to_dict()

    st.subheader(f"{match.home_team} vs {match.away_team}")
    st.caption(
        f"{match.competition} - {match.stage} - "
        f"{'Neutral venue / 中立场' if match.neutral else 'Home venue / 主场'} - "
        f"{match.match_time.isoformat()}"
    )

    best_direction_raw = row["value_bet_direction"]
    best_direction = (
        OUTCOME_LABELS[str(best_direction_raw)]
        if isinstance(best_direction_raw, str) and best_direction_raw in OUTCOME_LABELS
        else "No bet / 不下注"
    )
    best_ev = row["expected_value"]
    best_ev_label = "n/a" if best_ev is None else _format_percent(float(best_ev))

    metric_cols = st.columns(4)
    metric_cols[0].metric("Market Overround / 市场水位", _format_percent(float(row["market_overround"])))
    metric_cols[1].metric("Best Value Bet / 最佳价值投注", str(best_direction))
    metric_cols[2].metric("Expected Value / 期望值", best_ev_label)
    metric_cols[3].metric("Kelly Stake / 凯利仓位", _format_percent(float(row["fractional_kelly_fraction"])))

    st.divider()

    chart_col, summary_col = st.columns([1.3, 0.9], gap="large")
    with chart_col:
        st.subheader(
            "Market vs Fundamental vs Final Probability / 市场 vs 基本面 vs 最终概率"
            if row.get("probability_model_mode") == "market_residual"
            else "Market vs Model Probability / 市场概率 vs 模型概率"
        )
        probability_df = _probability_dataframe(row)
        chart = (
            alt.Chart(probability_df)
            .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
            .encode(
                x=alt.X(
                    "Outcome:N",
                    sort=[OUTCOME_LABELS["home"], OUTCOME_LABELS["draw"], OUTCOME_LABELS["away"]],
                    title=None,
                ),
                xOffset=alt.XOffset("Source / 来源:N"),
                y=alt.Y(
                    "Probability (%) / 概率(%):Q",
                    title="Probability (%) / 概率(%)",
                    scale=alt.Scale(domain=[0, 60]),
                ),
                color=alt.Color(
                    "Source / 来源:N",
                    scale=alt.Scale(range=["#175cd3", "#7cc4fa", "#12b76a"]),
                    legend=alt.Legend(orient="bottom", title=None),
                ),
                tooltip=[
                    "Outcome:N",
                    "Source / 来源:N",
                    alt.Tooltip("Probability (%) / 概率(%):Q", format=".2f"),
                ],
            )
            .properties(height=310)
        )
        st.altair_chart(chart, width="stretch")

    with summary_col:
        st.subheader("Decision / 决策")
        if bool(row["value_bet_flag"]):
            st.success(_display_reason(str(row["reason"])))
        else:
            st.warning(_display_reason(str(row["reason"])))
        decision_summary = {
            "risk_level / 风险等级": row["risk_level"],
            "probability_mode / 概率模式": row["probability_model_mode"],
            "bookmaker / 博彩公司": row["bookmaker"],
            "odds_captured_at / 赔率采集时间": row["odds_captured_at"],
        }
        if row.get("probability_model_mode") == "market_residual":
            adjustment_outcome = str(row["largest_residual_adjustment_outcome"])
            decision_summary["largest_residual_adjustment / 最大残差修正"] = (
                f"{OUTCOME_LABELS[adjustment_outcome]} "
                f"{float(row['largest_residual_adjustment']):+.2%}"
            )
            decision_summary["residual_gap_weight / 残差权重"] = row[
                "residual_fundamental_gap_weight"
            ]
        st.write(
            decision_summary
        )

    st.subheader("Outcome Table / 结果表")
    decision_df = _decision_dataframe(row)
    st.dataframe(
        decision_df,
        hide_index=True,
        width="stretch",
        column_config={
            "Odds / 赔率": st.column_config.NumberColumn(format="%.2f"),
            "Market Prob (%) / 市场概率(%)": st.column_config.NumberColumn(format="%.2f"),
            "Model Prob (%) / 模型概率(%)": st.column_config.NumberColumn(format="%.2f"),
            "Fundamental Prob (%) / 基本面概率(%)": st.column_config.NumberColumn(format="%.2f"),
            "Final Prob (%) / 最终概率(%)": st.column_config.NumberColumn(format="%.2f"),
            "Residual Adj (%) / 残差修正(%)": st.column_config.NumberColumn(format="%.2f"),
            "Edge (%) / 概率差(%)": st.column_config.NumberColumn(format="%.2f"),
            "EV (%)": st.column_config.NumberColumn(format="%.2f"),
            "Kelly (%) / 凯利(%)": st.column_config.NumberColumn(format="%.2f"),
        },
    )

    with st.expander("Raw report dictionary / 原始报告字典"):
        st.json(row)


def _load_batch_manifest_from_sidebar():
    st.sidebar.header("Batch Input / 批量输入")
    uploaded_file = st.sidebar.file_uploader(
        "Upload manifest JSON / 上传清单JSON",
        type=["json"],
        key="batch_manifest_uploader",
    )
    base_dir_choice = st.sidebar.selectbox(
        "Manifest relative path base / 清单相对路径基准",
        ["examples", "project root"],
        index=0,
    )
    if uploaded_file is None:
        try:
            manifest = load_backtest_manifest_path(DEMO_MANIFEST_PATH)
        except ValueError as exc:
            st.sidebar.error(f"Demo manifest failed. / Demo清单失败：{exc}")
            return None
        st.sidebar.caption("Using examples/demo_backtest_manifest.json. / 使用示例批量清单。")
        return manifest

    base_dir = PROJECT_ROOT / "examples" if base_dir_choice == "examples" else PROJECT_ROOT
    try:
        manifest = load_backtest_manifest_text(
            uploaded_file.getvalue().decode("utf-8"),
            base_dir=base_dir,
            source_path=uploaded_file.name,
        )
    except UnicodeDecodeError as exc:
        st.sidebar.error(f"Uploaded manifest must be UTF-8 JSON. / 上传清单必须是 UTF-8 JSON。{exc}")
        return None
    except (OSError, ValueError) as exc:
        st.sidebar.error(f"Invalid manifest. / 批量清单无效：{exc}")
        return None

    st.sidebar.success("Loaded batch manifest. / 已加载批量清单。")
    return manifest


def _render_batch_backtest_page() -> None:
    manifest = _load_batch_manifest_from_sidebar()
    if manifest is None:
        st.info("Fix the manifest or use the demo manifest. / 请修复清单，或使用示例清单。")
        return

    st.sidebar.header("Batch Rules / 批量规则")
    flat_stake = st.sidebar.number_input(
        "Flat stake / 固定下注额",
        min_value=0.01,
        value=10.0,
        step=1.0,
    )
    starting_bankroll = st.sidebar.number_input(
        "Starting bankroll / 初始本金",
        min_value=1.0,
        value=100.0,
        step=10.0,
    )
    probability_edge_threshold = st.sidebar.slider(
        "Probability edge threshold / 概率优势阈值",
        min_value=0.0,
        max_value=0.10,
        value=0.02,
        step=0.005,
        format="%.3f",
        key="batch_probability_edge_threshold",
    )
    ev_threshold = st.sidebar.slider(
        "EV threshold / 期望值阈值",
        min_value=0.0,
        max_value=0.10,
        value=0.01,
        step=0.005,
        format="%.3f",
        key="batch_ev_threshold",
    )
    kelly_fraction = st.sidebar.slider(
        "Kelly fraction / 凯利折扣",
        min_value=0.05,
        max_value=1.00,
        value=0.25,
        step=0.05,
        format="%.2f",
        key="batch_kelly_fraction",
    )
    stake_cap = st.sidebar.slider(
        "Stake cap / 单注上限",
        min_value=0.001,
        max_value=0.10,
        value=0.02,
        step=0.001,
        format="%.3f",
        key="batch_stake_cap",
    )
    use_residual_model = st.sidebar.checkbox(
        "Use market residual probabilities / 使用市场残差概率",
        value=False,
        key="batch_use_residual_model",
    )
    residual_config = None
    if use_residual_model:
        st.sidebar.header("Batch Residual Rules / 批量残差规则")
        residual_config = ResidualEdgeConfig(
            fundamental_gap_weight=float(
                st.sidebar.slider(
                    "Fundamental gap weight / 基本面差异权重",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.25,
                    step=0.05,
                    format="%.2f",
                    key="batch_residual_fundamental_gap_weight",
                )
            ),
            max_abs_adjustment_per_outcome=float(
                st.sidebar.slider(
                    "Max adjustment per outcome / 单项最大修正",
                    min_value=0.0,
                    max_value=0.10,
                    value=0.05,
                    step=0.005,
                    format="%.3f",
                    key="batch_residual_max_adjustment",
                )
            ),
        )

    try:
        result = run_batch_backtest(
            manifest,
            flat_stake=float(flat_stake),
            starting_bankroll=float(starting_bankroll),
            probability_edge_threshold=float(probability_edge_threshold),
            ev_threshold=float(ev_threshold),
            kelly_fraction=float(kelly_fraction),
            stake_cap=float(stake_cap),
            use_market_residual_model=use_residual_model,
            residual_config=residual_config,
        )
    except ValueError as exc:
        st.error(f"Batch backtest failed. / 批量回测失败：{exc}")
        return

    payload = result.to_dict()
    summary = payload["summary"]

    st.subheader("Batch Backtest / 批量回测")
    st.caption(
        "Manifest-driven scoring, flat-stake settlement, and Kelly bankroll curve. / "
        "基于清单的评分、固定下注结算与Kelly资金曲线。"
    )

    metric_cols = st.columns(5)
    metric_cols[0].metric("Entries / 场次数", str(summary["entry_count"]))
    metric_cols[1].metric("Flat ROI / 固定注ROI", _format_optional_percent(summary["flat_roi"]))
    metric_cols[2].metric("Kelly Final / Kelly最终本金", _format_number(summary["kelly_final_bankroll"]))
    metric_cols[3].metric("Max Drawdown / 最大回撤", _format_optional_percent(summary["kelly_max_drawdown"]))
    metric_cols[4].metric("Hit Rate / 命中率", _format_optional_percent(summary.get("flat_hit_rate")))

    st.divider()

    curve_df = _kelly_curve_dataframe(payload["kelly_curve"]["points"])
    chart_col, score_col = st.columns([1.35, 0.95], gap="large")
    with chart_col:
        st.subheader("Kelly Bankroll Curve / Kelly资金曲线")
        if curve_df.empty:
            st.info("No bankroll points. / 暂无资金曲线数据。")
        else:
            curve_chart = (
                alt.Chart(curve_df)
                .mark_line(point=True)
                .encode(
                    x=alt.X("Step / 步骤:O", title="Step / 步骤"),
                    y=alt.Y("Bankroll / 本金:Q", title="Bankroll / 本金", scale=alt.Scale(zero=False)),
                    tooltip=[
                        "Step / 步骤:O",
                        "Match ID / 比赛ID:N",
                        alt.Tooltip("Bankroll / 本金:Q", format=".2f"),
                        alt.Tooltip("Drawdown / 回撤:Q", format=".2f"),
                        alt.Tooltip("Stake / 注额:Q", format=".2f"),
                        alt.Tooltip("Profit / 盈亏:Q", format=".2f"),
                    ],
                )
                .properties(height=320)
            )
            st.altair_chart(curve_chart, width="stretch")

    with score_col:
        st.subheader("Model vs Market / 模型 vs 市场")
        comparison_df = pd.DataFrame.from_records(
            [
                {
                    "Metric / 指标": "Mean Brier",
                    "Model / 模型": summary["mean_model_brier_score"],
                    "Market / 市场": summary["mean_market_brier_score"],
                    "Fundamental / 基本面": summary.get("mean_fundamental_brier_score"),
                },
                {
                    "Metric / 指标": "Mean Log Loss",
                    "Model / 模型": summary["mean_model_log_loss"],
                    "Market / 市场": summary["mean_market_log_loss"],
                    "Fundamental / 基本面": summary.get("mean_fundamental_log_loss"),
                },
            ]
        )
        comparison_df = comparison_df.dropna(axis=1, how="all")
        comparison_chart = (
            alt.Chart(comparison_df.melt("Metric / 指标", var_name="Source / 来源", value_name="Value / 数值"))
            .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
            .encode(
                x=alt.X("Metric / 指标:N", title=None),
                xOffset=alt.XOffset("Source / 来源:N"),
                y=alt.Y("Value / 数值:Q", title="Lower is better / 越低越好"),
                color=alt.Color(
                    "Source / 来源:N",
                    scale=alt.Scale(range=["#7cc4fa", "#175cd3"]),
                    legend=alt.Legend(orient="bottom", title=None),
                ),
                tooltip=["Metric / 指标:N", "Source / 来源:N", alt.Tooltip("Value / 数值:Q", format=".4f")],
            )
            .properties(height=320)
        )
        st.altair_chart(comparison_chart, width="stretch")

    st.subheader("Scoring Table / 评分表")
    scoring_df = _batch_scoring_dataframe(payload["scored_predictions"])
    st.dataframe(
        scoring_df,
        hide_index=True,
        width="stretch",
        column_config={
            "Model Brier": st.column_config.NumberColumn(format="%.4f"),
            "Market Brier": st.column_config.NumberColumn(format="%.4f"),
            "Model Log Loss": st.column_config.NumberColumn(format="%.4f"),
            "Market Log Loss": st.column_config.NumberColumn(format="%.4f"),
        },
    )

    st.subheader("Flat-Stake Settlement / 固定下注结算")
    settlement_df = _batch_settlement_dataframe(payload["flat_stake_settlements"])
    st.dataframe(
        settlement_df,
        hide_index=True,
        width="stretch",
        column_config={
            "Odds / 赔率": st.column_config.NumberColumn(format="%.2f"),
            "Stake / 注额": st.column_config.NumberColumn(format="%.2f"),
            "Profit / 盈亏": st.column_config.NumberColumn(format="%.2f"),
            "ROI": st.column_config.NumberColumn(format="%.2f"),
        },
    )

    with st.expander("Raw batch backtest payload / 原始批量回测结果"):
        st.json(payload)


def main() -> None:
    st.set_page_config(
        page_title="World Cup Betting EDP",
        layout="wide",
    )
    _inject_styles()

    st.title("World Cup Betting EDP")
    mode = st.sidebar.radio(
        "Mode / 模式",
        ["Single Match / 单场预测", "Batch Backtest / 批量回测"],
        horizontal=False,
    )

    if mode.startswith("Single"):
        st.markdown(
            '<p class="section-note">Single-match 1X2 probability pricing, market comparison, '
            "and fractional Kelly sizing. / 单场胜平负概率定价、市场比较与分数凯利仓位建议。</p>",
            unsafe_allow_html=True,
        )
        _render_single_match_page()
        return

    st.markdown(
        '<p class="section-note">Manifest-driven batch scoring, settlement, and bankroll monitoring. '
        "/ 基于清单的批量评分、结算与资金曲线监控。</p>",
        unsafe_allow_html=True,
    )
    _render_batch_backtest_page()


if __name__ == "__main__":
    main()
