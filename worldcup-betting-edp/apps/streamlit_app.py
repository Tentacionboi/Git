"""Streamlit dashboard for World Cup betting research workflows."""

from __future__ import annotations

from datetime import datetime, time, timezone
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from worldcup_betting_edp.backtest import (
    default_world_cup_time_slices,
    run_batch_backtest,
    run_market_time_slice_backtest_from_csv,
    run_real_market_backtest,
    run_real_market_parameter_sweep,
)
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
DEFAULT_REAL_ODDS_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "odds"
    / "the_odds_api"
    / "2022-11-20T120000Z_canonical_odds.csv"
)
DEFAULT_ELO_PROBABILITIES_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "ratings"
    / "world_cup_elo_1x2_probabilities_calibrated.csv"
)
DEMO_TIME_SERIES_ODDS_PATH = PROJECT_ROOT / "examples" / "demo_world_cup_market_odds_timeseries.csv"
DEMO_MATCH_TIMING_PATH = PROJECT_ROOT / "examples" / "demo_world_cup_match_timing.csv"


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


@st.cache_data(show_spinner=False)
def _run_cached_real_market_backtest(
    canonical_odds_path: str,
    elo_probabilities_path: str,
    edge_threshold: float,
    ev_threshold: float,
    residual_gap_weight: float,
    residual_max_adjustment: float,
) -> dict[str, object]:
    return run_real_market_backtest(
        canonical_odds_path=canonical_odds_path,
        elo_probabilities_path=elo_probabilities_path,
        edge_threshold=edge_threshold,
        ev_threshold=ev_threshold,
        residual_config=ResidualEdgeConfig(
            fundamental_gap_weight=residual_gap_weight,
            max_abs_adjustment_per_outcome=residual_max_adjustment,
        ),
    )


@st.cache_data(show_spinner=False)
def _run_cached_real_market_parameter_sweep(
    canonical_odds_path: str,
    elo_probabilities_path: str,
    edge_thresholds: tuple[float, ...],
    ev_thresholds: tuple[float, ...],
    residual_gap_weights: tuple[float, ...],
    residual_max_adjustments: tuple[float, ...],
) -> dict[str, object]:
    return run_real_market_parameter_sweep(
        canonical_odds_path=canonical_odds_path,
        elo_probabilities_path=elo_probabilities_path,
        edge_thresholds=edge_thresholds,
        ev_thresholds=ev_thresholds,
        residual_gap_weights=residual_gap_weights,
        residual_max_adjustments=residual_max_adjustments,
    )


@st.cache_data(show_spinner=False)
def _run_cached_time_slice_backtest(
    market_odds_path: str,
    model_probabilities_path: str,
    match_timing_path: str,
    residual_gap_weight: float,
    residual_max_adjustment: float,
) -> dict[str, object]:
    return run_market_time_slice_backtest_from_csv(
        market_odds_path=market_odds_path,
        model_probabilities_path=model_probabilities_path,
        match_timing_path=match_timing_path,
        slices=default_world_cup_time_slices(),
        residual_config=ResidualEdgeConfig(
            fundamental_gap_weight=residual_gap_weight,
            max_abs_adjustment_per_outcome=residual_max_adjustment,
        ),
    )


def _probability_quality_dataframe(payload: dict[str, object]) -> pd.DataFrame:
    quality = payload["probability_quality"]
    rows = []
    model_labels = {
        "market_average": "Market Average / 市场均值",
        "elo_calibrated": "Elo Calibrated / 校准Elo",
        "market_residual": "Market Residual / 市场残差",
    }
    for key, label in model_labels.items():
        summary = quality[key]
        rows.append(
            {
                "Model / 模型": label,
                "Accuracy / 准确率": summary["accuracy"],
                "Brier Score": summary["mean_brier_score"],
                "Log Loss": summary["mean_log_loss"],
                "Avg Actual Prob / 实际结果均值概率": summary["average_probability_actual"],
            }
        )
    return pd.DataFrame.from_records(rows)


def _real_value_bets_dataframe(payload: dict[str, object]) -> pd.DataFrame:
    records = []
    for bet in payload["value_bets"]:
        records.append(
            {
                "Date / 日期": bet["match_date"],
                "Match / 比赛": f"{bet['home_team']} vs {bet['away_team']}",
                "Bookmaker / 公司": bet["bookmaker"],
                "Bet / 方向": OUTCOME_LABELS[str(bet["outcome"])],
                "Actual / 实际": OUTCOME_LABELS[str(bet["actual"])],
                "Odds / 赔率": bet["odds"],
                "Market Prob (%) / 市场概率(%)": float(bet["market_probability"]) * 100.0,
                "Model Prob (%) / 模型概率(%)": float(bet["model_probability"]) * 100.0,
                "Edge (%) / 概率差(%)": float(bet["edge"]) * 100.0,
                "EV (%)": float(bet["ev"]) * 100.0,
                "Profit / 盈亏": bet["profit_flat_1"],
                "Hit / 命中": bool(bet["hit"]),
            }
        )
    return pd.DataFrame.from_records(records)


def _real_bankroll_dataframe(payload: dict[str, object]) -> pd.DataFrame:
    records = []
    for point in payload["bankroll_curve"]:
        records.append(
            {
                "Step / 步骤": point["step"],
                "Date / 日期": point["match_date"],
                "Match / 比赛": f"{point['home_team']} vs {point['away_team']}",
                "Bet / 方向": OUTCOME_LABELS[str(point["outcome"])],
                "Actual / 实际": OUTCOME_LABELS[str(point["actual"])],
                "Odds / 赔率": point["odds"],
                "Profit / 盈亏": point["profit"],
                "Bankroll / 本金": point["bankroll"],
                "Drawdown (%) / 回撤(%)": float(point["drawdown"]) * 100.0,
            }
        )
    return pd.DataFrame.from_records(records)


def _real_match_rows_dataframe(payload: dict[str, object]) -> pd.DataFrame:
    records = []
    for row in payload["match_rows"]:
        records.append(
            {
                "Date / 日期": row["match_date"],
                "Match / 比赛": f"{row['home_team']} vs {row['away_team']}",
                "Actual / 实际": OUTCOME_LABELS[str(row["actual_result"])],
                "Bookmakers / 公司数": row["bookmaker_count"],
                "Market H/D/A / 市场主平客": (
                    f"{float(row['market_home_probability']):.1%} / "
                    f"{float(row['market_draw_probability']):.1%} / "
                    f"{float(row['market_away_probability']):.1%}"
                ),
                "Elo H/D/A / Elo主平客": (
                    f"{float(row['elo_home_probability']):.1%} / "
                    f"{float(row['elo_draw_probability']):.1%} / "
                    f"{float(row['elo_away_probability']):.1%}"
                ),
                "Residual H/D/A / 残差主平客": (
                    f"{float(row['residual_home_probability']):.1%} / "
                    f"{float(row['residual_draw_probability']):.1%} / "
                    f"{float(row['residual_away_probability']):.1%}"
                ),
                "Largest Adj / 最大修正": (
                    f"{OUTCOME_LABELS[str(row['largest_residual_adjustment_outcome'])]} "
                    f"{float(row['largest_residual_adjustment']):+.2%}"
                ),
            }
        )
    return pd.DataFrame.from_records(records)


def _sweep_dataframe(payload: dict[str, object]) -> pd.DataFrame:
    records = []
    for row in payload["rows"]:
        records.append(
            {
                "Edge Threshold / 概率阈值": row["edge_threshold"],
                "EV Threshold / EV阈值": row["ev_threshold"],
                "Residual Gap Weight / 残差权重": row["residual_gap_weight"],
                "Max Adjustment / 最大修正": row["residual_max_adjustment"],
                "Accuracy / 准确率": row["accuracy"],
                "Brier Score": row["brier_score"],
                "Log Loss": row["log_loss"],
                "Residual-Market Brier": row["residual_minus_market_brier"],
                "Residual-Market LogLoss": row["residual_minus_market_log_loss"],
                "Bet Count / 下注数": row["bet_count"],
                "Hit Rate / 命中率": row["hit_rate"],
                "Flat ROI / 固定注ROI": row["flat_roi"],
                "Flat Profit / 固定注盈亏": row["flat_profit"],
                "Average EV / 平均EV": row["average_ev"],
                "Average Odds / 平均赔率": row["average_odds"],
                "Max Drawdown / 最大回撤": row["max_drawdown"],
            }
        )
    return pd.DataFrame.from_records(records)


def _time_slice_summary_dataframe(payload: dict[str, object]) -> pd.DataFrame:
    records = []
    for slice_payload in payload["slices"]:
        coverage = slice_payload["coverage"]
        quality = slice_payload["quality"]
        record = {
            "Slice / 时间切片": slice_payload["name"],
            "Selection / 选择规则": slice_payload["selection_mode"],
            "Hours Before / 开赛前小时": slice_payload["hours_before_kickoff"],
            "Evaluated Matches / 回测场数": coverage["evaluated_match_count"],
            "Avg Bookmakers / 平均公司数": coverage["average_bookmakers_per_match"],
            "Selected Odds / 选中赔率行": coverage["selected_odds_count"],
        }
        if quality is not None:
            record.update(
                {
                    "Market Brier": quality["market"]["mean_brier_score"],
                    "Residual Brier": quality["market_residual"]["mean_brier_score"],
                    "Residual-Market Brier": quality["residual_minus_market_brier"],
                    "Market LogLoss": quality["market"]["mean_log_loss"],
                    "Residual LogLoss": quality["market_residual"]["mean_log_loss"],
                    "Residual-Market LogLoss": quality["residual_minus_market_log_loss"],
                    "Residual Accuracy / 残差准确率": quality["market_residual"]["accuracy"],
                }
            )
        records.append(record)
    return pd.DataFrame.from_records(records)


def _time_slice_rows_dataframe(payload: dict[str, object]) -> pd.DataFrame:
    records = []
    for slice_payload in payload["slices"]:
        for row in slice_payload["rows"]:
            records.append(
                {
                    "Slice / 时间切片": row["slice_name"],
                    "Prediction Time / 预测时间": row["prediction_time"],
                    "Match / 比赛": f"{row['home_team']} vs {row['away_team']}",
                    "Actual / 实际": OUTCOME_LABELS[str(row["actual_result"])],
                    "Bookmakers / 公司数": row["bookmaker_count"],
                    "Market H/D/A / 市场主平客": (
                        f"{float(row['market_home_probability']):.1%} / "
                        f"{float(row['market_draw_probability']):.1%} / "
                        f"{float(row['market_away_probability']):.1%}"
                    ),
                    "Residual H/D/A / 残差主平客": (
                        f"{float(row['residual_home_probability']):.1%} / "
                        f"{float(row['residual_draw_probability']):.1%} / "
                        f"{float(row['residual_away_probability']):.1%}"
                    ),
                }
            )
    return pd.DataFrame.from_records(records)


def _format_float_choice(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _render_real_market_backtest_page() -> None:
    st.sidebar.header("Real Odds Data / 真实赔率数据")
    odds_path = st.sidebar.text_input(
        "Canonical odds CSV / 标准赔率CSV",
        value=str(DEFAULT_REAL_ODDS_PATH),
    )
    elo_path = st.sidebar.text_input(
        "Elo probabilities CSV / Elo概率CSV",
        value=str(DEFAULT_ELO_PROBABILITIES_PATH),
    )
    st.sidebar.caption(
        "Default data is local and ignored by Git when it comes from paid odds. / "
        "默认赔率数据保存在本地，付费赔率明细不会提交到Git。"
    )

    st.sidebar.header("Tuning / 调参")
    edge_threshold = st.sidebar.slider(
        "Edge threshold / 概率优势阈值",
        min_value=0.0,
        max_value=0.10,
        value=0.02,
        step=0.005,
        format="%.3f",
        key="real_edge_threshold",
    )
    ev_threshold = st.sidebar.slider(
        "EV threshold / 期望值阈值",
        min_value=0.0,
        max_value=0.20,
        value=0.01,
        step=0.005,
        format="%.3f",
        key="real_ev_threshold",
    )
    residual_gap_weight = st.sidebar.slider(
        "Residual gap weight / 残差权重",
        min_value=0.0,
        max_value=0.75,
        value=0.25,
        step=0.05,
        format="%.2f",
        key="real_residual_gap_weight",
    )
    residual_max_adjustment = st.sidebar.slider(
        "Max residual adjustment / 最大残差修正",
        min_value=0.0,
        max_value=0.10,
        value=0.05,
        step=0.005,
        format="%.3f",
        key="real_residual_max_adjustment",
    )

    if not Path(odds_path).exists():
        st.error(
            "Real odds CSV not found. / 未找到真实赔率CSV。"
            f"\n\n`{odds_path}`"
        )
        return
    if not Path(elo_path).exists():
        st.error(
            "Elo probabilities CSV not found. / 未找到Elo概率CSV。"
            f"\n\n`{elo_path}`"
        )
        return

    try:
        payload = _run_cached_real_market_backtest(
            odds_path,
            elo_path,
            float(edge_threshold),
            float(ev_threshold),
            float(residual_gap_weight),
            float(residual_max_adjustment),
        )
    except ValueError as exc:
        st.error(f"Real market backtest failed. / 真实赔率回测失败：{exc}")
        return

    coverage = payload["coverage"]
    value_summary = payload["value_bet_summary"]
    quality = payload["probability_quality"]

    st.subheader("Real Market Backtest / 真实赔率回测")
    st.caption(
        "Historical The Odds API snapshot + calibrated World Cup Elo. This is a "
        "time-slice research view, not live monitoring yet. / "
        "历史赔率快照 + 校准世界杯Elo。这是时间截面研究视图，还不是实时监控。"
    )
    st.warning(
        "Interpretation guardrail / 解读约束：当前只有一个历史赔率截面，且 value bet "
        "会在多个博彩公司之间选最高EV；ROI可能非常不稳定，不能当作已验证优势。"
    )

    metric_cols = st.columns(6)
    metric_cols[0].metric("Matches / 比赛数", str(coverage["evaluated_match_count"]))
    metric_cols[1].metric(
        "Bookmakers / 平均公司数",
        _format_number(coverage["average_bookmakers_per_match"], digits=1),
    )
    metric_cols[2].metric(
        "Market Overround / 平均水位",
        _format_percent(float(coverage["average_market_overround"])),
    )
    metric_cols[3].metric("Bets / 下注数", str(value_summary["bet_count"]))
    metric_cols[4].metric("Flat ROI / 固定注ROI", _format_optional_percent(value_summary["flat_roi"]))
    metric_cols[5].metric(
        "Max Drawdown / 最大回撤",
        _format_optional_percent(value_summary["max_drawdown"]),
    )

    st.divider()

    quality_df = _probability_quality_dataframe(payload)
    bankroll_df = _real_bankroll_dataframe(payload)
    chart_col, pnl_col = st.columns([1.05, 1.25], gap="large")
    with chart_col:
        st.subheader("Prediction Quality / 预测质量")
        quality_long = quality_df.melt(
            id_vars=["Model / 模型"],
            value_vars=["Brier Score", "Log Loss"],
            var_name="Metric / 指标",
            value_name="Value / 数值",
        )
        quality_chart = (
            alt.Chart(quality_long)
            .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
            .encode(
                x=alt.X("Metric / 指标:N", title=None),
                xOffset=alt.XOffset("Model / 模型:N"),
                y=alt.Y("Value / 数值:Q", title="Lower is better / 越低越好"),
                color=alt.Color("Model / 模型:N", legend=alt.Legend(orient="bottom", title=None)),
                tooltip=[
                    "Metric / 指标:N",
                    "Model / 模型:N",
                    alt.Tooltip("Value / 数值:Q", format=".4f"),
                ],
            )
            .properties(height=320)
        )
        st.altair_chart(quality_chart, width="stretch")

    with pnl_col:
        st.subheader("Flat-Stake Bankroll Curve / 固定注资金曲线")
        if bankroll_df.empty:
            st.info("No bets passed the current thresholds. / 当前阈值下没有下注。")
        else:
            pnl_chart = (
                alt.Chart(bankroll_df)
                .mark_line(point=True)
                .encode(
                    x=alt.X("Step / 步骤:O", title="Bet sequence / 下注序列"),
                    y=alt.Y("Bankroll / 本金:Q", title="Bankroll / 本金", scale=alt.Scale(zero=False)),
                    tooltip=[
                        "Step / 步骤:O",
                        "Date / 日期:N",
                        "Match / 比赛:N",
                        "Bet / 方向:N",
                        alt.Tooltip("Odds / 赔率:Q", format=".2f"),
                        alt.Tooltip("Profit / 盈亏:Q", format=".2f"),
                        alt.Tooltip("Bankroll / 本金:Q", format=".2f"),
                        alt.Tooltip("Drawdown (%) / 回撤(%):Q", format=".2f"),
                    ],
                )
                .properties(height=320)
            )
            st.altair_chart(pnl_chart, width="stretch")

    score_cols = st.columns(4)
    score_cols[0].metric(
        "Residual vs Market Brier / 残差-Brier",
        _format_number(quality["residual_minus_market_brier"], digits=4),
    )
    score_cols[1].metric(
        "Residual vs Market LogLoss / 残差-LogLoss",
        _format_number(quality["residual_minus_market_log_loss"], digits=4),
    )
    score_cols[2].metric("Hit Rate / 命中率", _format_optional_percent(value_summary["hit_rate"]))
    score_cols[3].metric("Average Odds / 平均赔率", _format_number(value_summary["average_odds"]))

    st.subheader("Quality Table / 预测质量表")
    st.dataframe(
        quality_df,
        hide_index=True,
        width="stretch",
        column_config={
            "Accuracy / 准确率": st.column_config.NumberColumn(format="%.2f"),
            "Brier Score": st.column_config.NumberColumn(format="%.4f"),
            "Log Loss": st.column_config.NumberColumn(format="%.4f"),
            "Avg Actual Prob / 实际结果均值概率": st.column_config.NumberColumn(format="%.4f"),
        },
    )

    st.subheader("Value Bet Table / 价值投注表")
    value_df = _real_value_bets_dataframe(payload)
    if value_df.empty:
        st.info("No value bets under current rules. / 当前规则下没有价值投注。")
    else:
        st.dataframe(
            value_df,
            hide_index=True,
            width="stretch",
            column_config={
                "Odds / 赔率": st.column_config.NumberColumn(format="%.2f"),
                "Market Prob (%) / 市场概率(%)": st.column_config.NumberColumn(format="%.2f"),
                "Model Prob (%) / 模型概率(%)": st.column_config.NumberColumn(format="%.2f"),
                "Edge (%) / 概率差(%)": st.column_config.NumberColumn(format="%.2f"),
                "EV (%)": st.column_config.NumberColumn(format="%.2f"),
                "Profit / 盈亏": st.column_config.NumberColumn(format="%.2f"),
            },
        )

    st.subheader("Parameter Sweep / 参数扫描")
    st.caption(
        "Run a bounded grid search to see parameter regions, not just one hand-picked setting. / "
        "运行受控网格扫描，看参数区域，而不是只看一个手选参数点。"
    )
    sweep_edge_candidates = [0.0, 0.01, 0.02, 0.03, 0.04, 0.05]
    sweep_ev_candidates = [0.0, 0.01, 0.02, 0.05, 0.10]
    sweep_gap_candidates = [0.0, 0.15, 0.25, 0.35, 0.50]
    sweep_adjustment_candidates = [0.02, 0.05, 0.08, 0.10]
    sweep_cols = st.columns(4)
    with sweep_cols[0]:
        sweep_edges = st.multiselect(
            "Edge values / 概率阈值候选",
            sweep_edge_candidates,
            default=[0.0, 0.02, 0.04],
            format_func=_format_float_choice,
            key="sweep_edges",
        )
    with sweep_cols[1]:
        sweep_evs = st.multiselect(
            "EV values / EV阈值候选",
            sweep_ev_candidates,
            default=[0.0, 0.01, 0.05],
            format_func=_format_float_choice,
            key="sweep_evs",
        )
    with sweep_cols[2]:
        sweep_gaps = st.multiselect(
            "Residual weights / 残差权重候选",
            sweep_gap_candidates,
            default=[0.0, 0.25, 0.50],
            format_func=_format_float_choice,
            key="sweep_gaps",
        )
    with sweep_cols[3]:
        sweep_adjustments = st.multiselect(
            "Max adjustments / 最大修正候选",
            sweep_adjustment_candidates,
            default=[0.05, 0.10],
            format_func=_format_float_choice,
            key="sweep_adjustments",
        )

    sweep_run_count = (
        len(sweep_edges) * len(sweep_evs) * len(sweep_gaps) * len(sweep_adjustments)
    )
    st.caption(f"Planned runs / 计划回测组合数：{sweep_run_count}")
    if sweep_run_count == 0:
        st.info("Choose at least one value in each sweep control. / 每组候选值至少选择一个。")
    elif sweep_run_count > 200:
        st.error("Sweep grid is too large. Keep it at 200 runs or fewer. / 参数组合过多，请控制在200组以内。")
    else:
        run_sweep = st.button(
            "Run Parameter Sweep / 运行参数扫描",
            key="run_real_market_sweep",
            type="primary",
        )
        if run_sweep:
            with st.spinner("Running parameter sweep... / 正在运行参数扫描..."):
                try:
                    st.session_state["real_market_sweep_payload"] = (
                        _run_cached_real_market_parameter_sweep(
                            odds_path,
                            elo_path,
                            tuple(float(value) for value in sweep_edges),
                            tuple(float(value) for value in sweep_evs),
                            tuple(float(value) for value in sweep_gaps),
                            tuple(float(value) for value in sweep_adjustments),
                        )
                    )
                except ValueError as exc:
                    st.error(f"Parameter sweep failed. / 参数扫描失败：{exc}")

    sweep_payload = st.session_state.get("real_market_sweep_payload")
    if sweep_payload:
        sweep_df = _sweep_dataframe(sweep_payload)
        st.warning(
            "Sweep interpretation / 扫描解读：这里仍然是同一个历史样本内结果。"
            "不要用最高ROI单点作为最终模型参数；优先看概率质量、下注数和回撤是否同时合理。"
        )
        metric_choice = st.selectbox(
            "Heatmap metric / 热力图指标",
            [
                "Flat ROI / 固定注ROI",
                "Brier Score",
                "Log Loss",
                "Bet Count / 下注数",
                "Max Drawdown / 最大回撤",
            ],
            index=0,
            key="sweep_heatmap_metric",
        )
        filter_cols = st.columns(2)
        with filter_cols[0]:
            gap_slice = st.selectbox(
                "Heatmap residual weight slice / 热力图残差权重切片",
                sorted(sweep_df["Residual Gap Weight / 残差权重"].unique()),
                format_func=_format_float_choice,
                key="sweep_gap_slice",
            )
        with filter_cols[1]:
            adjustment_slice = st.selectbox(
                "Heatmap max adjustment slice / 热力图最大修正切片",
                sorted(sweep_df["Max Adjustment / 最大修正"].unique()),
                format_func=_format_float_choice,
                key="sweep_adjustment_slice",
            )
        heatmap_df = sweep_df[
            (sweep_df["Residual Gap Weight / 残差权重"] == gap_slice)
            & (sweep_df["Max Adjustment / 最大修正"] == adjustment_slice)
        ]
        heatmap = (
            alt.Chart(heatmap_df)
            .mark_rect()
            .encode(
                x=alt.X("Edge Threshold / 概率阈值:O", title="Edge threshold / 概率阈值"),
                y=alt.Y("EV Threshold / EV阈值:O", title="EV threshold / EV阈值"),
                color=alt.Color(f"{metric_choice}:Q", title=metric_choice),
                tooltip=[
                    alt.Tooltip("Edge Threshold / 概率阈值:Q", format=".3f"),
                    alt.Tooltip("EV Threshold / EV阈值:Q", format=".3f"),
                    alt.Tooltip("Residual Gap Weight / 残差权重:Q", format=".2f"),
                    alt.Tooltip("Max Adjustment / 最大修正:Q", format=".3f"),
                    alt.Tooltip(f"{metric_choice}:Q", format=".4f"),
                    alt.Tooltip("Bet Count / 下注数:Q", format=".0f"),
                    alt.Tooltip("Brier Score:Q", format=".4f"),
                    alt.Tooltip("Log Loss:Q", format=".4f"),
                ],
            )
            .properties(height=320)
        )
        st.altair_chart(heatmap, width="stretch")

        rank_metric = st.selectbox(
            "Ranking metric / 排名指标",
            [
                "Flat ROI / 固定注ROI",
                "Brier Score",
                "Log Loss",
                "Residual-Market Brier",
                "Bet Count / 下注数",
                "Max Drawdown / 最大回撤",
            ],
            index=0,
            key="sweep_rank_metric",
        )
        lower_is_better = rank_metric in {
            "Brier Score",
            "Log Loss",
            "Residual-Market Brier",
            "Max Drawdown / 最大回撤",
        }
        ranked_df = sweep_df.sort_values(
            by=rank_metric,
            ascending=lower_is_better,
            na_position="last",
        )
        st.dataframe(
            ranked_df.head(25),
            hide_index=True,
            width="stretch",
            column_config={
                "Edge Threshold / 概率阈值": st.column_config.NumberColumn(format="%.3f"),
                "EV Threshold / EV阈值": st.column_config.NumberColumn(format="%.3f"),
                "Residual Gap Weight / 残差权重": st.column_config.NumberColumn(format="%.2f"),
                "Max Adjustment / 最大修正": st.column_config.NumberColumn(format="%.3f"),
                "Accuracy / 准确率": st.column_config.NumberColumn(format="%.3f"),
                "Brier Score": st.column_config.NumberColumn(format="%.4f"),
                "Log Loss": st.column_config.NumberColumn(format="%.4f"),
                "Residual-Market Brier": st.column_config.NumberColumn(format="%.4f"),
                "Residual-Market LogLoss": st.column_config.NumberColumn(format="%.4f"),
                "Hit Rate / 命中率": st.column_config.NumberColumn(format="%.3f"),
                "Flat ROI / 固定注ROI": st.column_config.NumberColumn(format="%.3f"),
                "Flat Profit / 固定注盈亏": st.column_config.NumberColumn(format="%.2f"),
                "Average EV / 平均EV": st.column_config.NumberColumn(format="%.3f"),
                "Average Odds / 平均赔率": st.column_config.NumberColumn(format="%.2f"),
                "Max Drawdown / 最大回撤": st.column_config.NumberColumn(format="%.3f"),
            },
        )

    with st.expander("Match probability rows / 比赛概率明细"):
        st.dataframe(
            _real_match_rows_dataframe(payload),
            hide_index=True,
            width="stretch",
        )

    with st.expander("Raw aggregate payload / 原始聚合结果"):
        st.json(
            {
                "input": payload["input"],
                "coverage": payload["coverage"],
                "probability_quality": payload["probability_quality"],
                "value_bet_summary": payload["value_bet_summary"],
                "notes": payload["notes"],
            }
        )


def _render_time_slice_backtest_page() -> None:
    st.sidebar.header("Time Slice Data / 时间切片数据")
    odds_path = st.sidebar.text_input(
        "Odds time-series CSV / 赔率时间序列CSV",
        value=str(DEMO_TIME_SERIES_ODDS_PATH),
        key="time_slice_odds_path",
    )
    model_path = st.sidebar.text_input(
        "Model probabilities CSV / 模型概率CSV",
        value=str(DEFAULT_ELO_PROBABILITIES_PATH),
        key="time_slice_model_path",
    )
    timing_path = st.sidebar.text_input(
        "Match timing CSV / 比赛开赛时间CSV",
        value=str(DEMO_MATCH_TIMING_PATH),
        key="time_slice_timing_path",
    )
    st.sidebar.caption(
        "Default odds and timing files are synthetic demos. Replace them with real multi-timestamp "
        "odds and verified kickoff times for real evaluation. / 默认赔率和开赛时间是合成演示数据；"
        "真实评估需要替换为真实多时间点赔率和已验证开赛时间。"
    )
    st.sidebar.header("Residual Rules / 残差规则")
    residual_gap_weight = st.sidebar.slider(
        "Residual gap weight / 残差权重",
        min_value=0.0,
        max_value=0.75,
        value=0.25,
        step=0.05,
        format="%.2f",
        key="time_slice_residual_gap",
    )
    residual_max_adjustment = st.sidebar.slider(
        "Max residual adjustment / 最大残差修正",
        min_value=0.0,
        max_value=0.10,
        value=0.05,
        step=0.005,
        format="%.3f",
        key="time_slice_residual_max",
    )

    for path, label in (
        (odds_path, "Odds time-series CSV / 赔率时间序列CSV"),
        (model_path, "Model probabilities CSV / 模型概率CSV"),
        (timing_path, "Match timing CSV / 比赛开赛时间CSV"),
    ):
        if not Path(path).exists():
            st.error(f"{label} not found. / 文件不存在：`{path}`")
            return

    try:
        payload = _run_cached_time_slice_backtest(
            odds_path,
            model_path,
            timing_path,
            float(residual_gap_weight),
            float(residual_max_adjustment),
        )
    except ValueError as exc:
        st.error(f"Time-slice backtest failed. / 时间切片回测失败：{exc}")
        return

    summary_df = _time_slice_summary_dataframe(payload)
    rows_df = _time_slice_rows_dataframe(payload)
    coverage = payload["coverage"]

    st.subheader("Time Slice Backtest / 时间切片回测")
    st.caption(
        "As-of odds selection for open, 24h, 6h, 1h, and close slices. / "
        "按 open、24h、6h、1h、close 时间切片选择当时可见赔率。"
    )
    st.warning(
        "Current default data is synthetic. This page validates the no-leakage mechanism; "
        "real conclusions require real multi-timestamp odds and verified kickoff timestamps. / "
        "当前默认数据是合成演示。此页用于验证无未来函数机制；真实结论需要真实多时间点赔率和已验证开赛时间。"
    )

    metric_cols = st.columns(4)
    metric_cols[0].metric("Model Matches / 模型场数", str(coverage["model_match_count"]))
    metric_cols[1].metric("Timing Matches / 开赛时间场数", str(coverage["timing_match_count"]))
    metric_cols[2].metric("Odds Matches / 赔率场数", str(coverage["odds_match_count"]))
    metric_cols[3].metric("Common Matches / 交集场数", str(coverage["common_match_count"]))

    st.subheader("Slice Quality / 切片质量")
    if summary_df.empty:
        st.info("No slices could be evaluated. / 没有可回测的时间切片。")
        return

    quality_long = summary_df.melt(
        id_vars=["Slice / 时间切片"],
        value_vars=["Market Brier", "Residual Brier", "Market LogLoss", "Residual LogLoss"],
        var_name="Metric / 指标",
        value_name="Value / 数值",
    ).dropna()
    quality_chart = (
        alt.Chart(quality_long)
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=alt.X("Slice / 时间切片:N", title=None),
            xOffset=alt.XOffset("Metric / 指标:N"),
            y=alt.Y("Value / 数值:Q", title="Lower is better / 越低越好"),
            color=alt.Color("Metric / 指标:N", legend=alt.Legend(orient="bottom", title=None)),
            tooltip=[
                "Slice / 时间切片:N",
                "Metric / 指标:N",
                alt.Tooltip("Value / 数值:Q", format=".4f"),
            ],
        )
        .properties(height=320)
    )
    st.altair_chart(quality_chart, width="stretch")

    st.subheader("Slice Summary Table / 切片汇总表")
    st.dataframe(
        summary_df,
        hide_index=True,
        width="stretch",
        column_config={
            "Hours Before / 开赛前小时": st.column_config.NumberColumn(format="%.1f"),
            "Avg Bookmakers / 平均公司数": st.column_config.NumberColumn(format="%.2f"),
            "Market Brier": st.column_config.NumberColumn(format="%.4f"),
            "Residual Brier": st.column_config.NumberColumn(format="%.4f"),
            "Residual-Market Brier": st.column_config.NumberColumn(format="%.4f"),
            "Market LogLoss": st.column_config.NumberColumn(format="%.4f"),
            "Residual LogLoss": st.column_config.NumberColumn(format="%.4f"),
            "Residual-Market LogLoss": st.column_config.NumberColumn(format="%.4f"),
            "Residual Accuracy / 残差准确率": st.column_config.NumberColumn(format="%.3f"),
        },
    )

    st.subheader("Selected Match Rows / 选中比赛明细")
    st.dataframe(rows_df, hide_index=True, width="stretch")

    with st.expander("Raw time-slice payload / 原始时间切片结果"):
        st.json(
            {
                "input": payload["input"],
                "coverage": payload["coverage"],
                "notes": payload["notes"],
            }
        )


def main() -> None:
    st.set_page_config(
        page_title="World Cup Betting EDP",
        layout="wide",
    )
    _inject_styles()

    st.title("World Cup Betting EDP")
    mode = st.sidebar.radio(
        "Mode / 模式",
        [
            "Single Match / 单场预测",
            "Batch Backtest / 批量回测",
            "Real Market Backtest / 真实赔率回测",
            "Time Slice Backtest / 时间切片回测",
        ],
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

    if mode.startswith("Batch"):
        st.markdown(
            '<p class="section-note">Manifest-driven batch scoring, settlement, and bankroll monitoring. '
            "/ 基于清单的批量评分、结算与资金曲线监控。</p>",
            unsafe_allow_html=True,
        )
        _render_batch_backtest_page()
        return

    if mode.startswith("Real"):
        st.markdown(
            '<p class="section-note">Real historical odds snapshot backtest with interactive thresholds, '
            "residual tuning, scoring, and P&L curve. / 真实历史赔率截面回测、交互阈值调参、评分与盈亏曲线。</p>",
            unsafe_allow_html=True,
        )
        _render_real_market_backtest_page()
        return

    st.markdown(
        '<p class="section-note">As-of time-sliced odds backtest for leakage-safe market comparison. '
        "/ 按时间切片验证赔率可见性、模型质量与市场基准。</p>",
        unsafe_allow_html=True,
    )
    _render_time_slice_backtest_page()


if __name__ == "__main__":
    main()
