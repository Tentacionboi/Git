"""Streamlit dashboard for the single-match World Cup betting MVP."""

from __future__ import annotations

from datetime import datetime, time, timezone

import altair as alt
import pandas as pd
import streamlit as st

from worldcup_betting_edp.domain import Match, ModelProbabilities, OddsSnapshot
from worldcup_betting_edp.reports import evaluate_single_match


OUTCOME_LABELS = {
    "home": "Home / 主胜",
    "draw": "Draw / 平局",
    "away": "Away / 客胜",
}

SOURCE_LABELS = {
    "market": "Market / 市场",
    "model": "Model / 模型",
}


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


def _probability_dataframe(row: dict[str, object]) -> pd.DataFrame:
    records = []
    for outcome in ("home", "draw", "away"):
        records.extend(
            [
                {
                    "Outcome": OUTCOME_LABELS[outcome],
                    "Source / 来源": SOURCE_LABELS["market"],
                    "Probability (%) / 概率(%)": float(row[f"market_{outcome}_prob_devig"]) * 100.0,
                },
                {
                    "Outcome": OUTCOME_LABELS[outcome],
                    "Source / 来源": SOURCE_LABELS["model"],
                    "Probability (%) / 概率(%)": float(row[f"model_{outcome}_prob"]) * 100.0,
                },
            ]
        )
    return pd.DataFrame.from_records(records)


def _decision_dataframe(row: dict[str, object]) -> pd.DataFrame:
    records = []
    for outcome in ("home", "draw", "away"):
        reason = str(row[f"{outcome}_decision_reason"])
        records.append(
            {
                "Outcome / 结果": OUTCOME_LABELS[outcome],
                "Odds / 赔率": float(row[f"market_{outcome}_odds"]),
                "Market Prob (%) / 市场概率(%)": float(row[f"market_{outcome}_prob_devig"]) * 100.0,
                "Model Prob (%) / 模型概率(%)": float(row[f"model_{outcome}_prob"]) * 100.0,
                "Edge (%) / 概率差(%)": float(row[f"delta_{outcome}"]) * 100.0,
                "EV (%)": float(row[f"{outcome}_ev"]) * 100.0,
                "Kelly (%) / 凯利(%)": float(row[f"{outcome}_kelly_fraction"]) * 100.0,
                "Reason / 理由": _display_reason(reason),
            }
        )
    return pd.DataFrame.from_records(records)


def _format_percent(value: float) -> str:
    return f"{value:.2%}"


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


def _build_sidebar_inputs() -> tuple[Match, OddsSnapshot, ModelProbabilities] | None:
    st.sidebar.header("Match / 比赛信息")
    match_id = st.sidebar.text_input("Match ID / 比赛ID", value="demo-2026-final")
    home_team = st.sidebar.text_input("Home / Team A / 主队或球队A", value="Team A")
    away_team = st.sidebar.text_input("Away / Team B / 客队或球队B", value="Team B")
    stage = st.sidebar.text_input("Stage / 阶段", value="Final")
    neutral = st.sidebar.checkbox("Neutral venue / 中立场", value=True)
    match_date = st.sidebar.date_input("Match date / 比赛日期", value=datetime(2026, 7, 19).date())
    match_time = st.sidebar.time_input("Match time UTC / UTC比赛时间", value=time(15, 0))

    st.sidebar.header("Market Odds / 市场赔率")
    bookmaker = st.sidebar.text_input("Bookmaker / 博彩公司", value="demo_book")
    odds_home = st.sidebar.number_input("Home odds / 主胜赔率", min_value=1.01, value=2.20, step=0.01)
    odds_draw = st.sidebar.number_input("Draw odds / 平局赔率", min_value=1.01, value=3.25, step=0.01)
    odds_away = st.sidebar.number_input("Away odds / 客胜赔率", min_value=1.01, value=3.60, step=0.01)

    st.sidebar.header("Model Probabilities / 模型概率")
    st.sidebar.caption("Enter probabilities as percentages. They must sum to 100%. / 请输入百分比，三项合计必须为100%。")
    model_home_pct = st.sidebar.number_input("Home model probability / 主胜模型概率", 0.0, 100.0, 49.0, 0.5)
    model_draw_pct = st.sidebar.number_input("Draw model probability / 平局模型概率", 0.0, 100.0, 27.0, 0.5)
    model_away_pct = st.sidebar.number_input("Away model probability / 客胜模型概率", 0.0, 100.0, 24.0, 0.5)
    probability_total = model_home_pct + model_draw_pct + model_away_pct

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
        captured_at=datetime.now(timezone.utc),
        bookmaker=bookmaker.strip() or "unknown",
        home=float(odds_home),
        draw=float(odds_draw),
        away=float(odds_away),
    )
    model = ModelProbabilities.from_1x2(
        match_id=match.match_id,
        model_name="manual_ui_model",
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
    return match, odds, model


def main() -> None:
    st.set_page_config(
        page_title="World Cup Betting EDP",
        layout="wide",
    )
    _inject_styles()

    st.title("World Cup Betting EDP")
    st.markdown(
        '<p class="section-note">Single-match 1X2 probability pricing, market comparison, '
        "and fractional Kelly sizing. / 单场胜平负概率定价、市场比较与分数凯利仓位建议。</p>",
        unsafe_allow_html=True,
    )

    inputs = _build_sidebar_inputs()
    if inputs is None:
        return

    match, odds, model = inputs
    rules = st.session_state["bet_rules"]
    report = evaluate_single_match(
        match=match,
        odds_snapshot=odds,
        model_probabilities=model,
        probability_edge_threshold=float(rules["probability_edge_threshold"]),
        ev_threshold=float(rules["ev_threshold"]),
        kelly_fraction=float(rules["kelly_fraction"]),
        stake_cap=float(rules["stake_cap"]),
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
        st.subheader("Market vs Model Probability / 市场概率 vs 模型概率")
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
                    scale=alt.Scale(range=["#175cd3", "#7cc4fa"]),
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
        st.altair_chart(chart, use_container_width=True)

    with summary_col:
        st.subheader("Decision / 决策")
        if bool(row["value_bet_flag"]):
            st.success(_display_reason(str(row["reason"])))
        else:
            st.warning(_display_reason(str(row["reason"])))
        st.write(
            {
                "risk_level / 风险等级": row["risk_level"],
                "bookmaker / 博彩公司": row["bookmaker"],
                "odds_captured_at / 赔率采集时间": row["odds_captured_at"],
            }
        )

    st.subheader("Outcome Table / 结果表")
    decision_df = _decision_dataframe(row)
    st.dataframe(
        decision_df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Odds / 赔率": st.column_config.NumberColumn(format="%.2f"),
            "Market Prob (%) / 市场概率(%)": st.column_config.NumberColumn(format="%.2f"),
            "Model Prob (%) / 模型概率(%)": st.column_config.NumberColumn(format="%.2f"),
            "Edge (%) / 概率差(%)": st.column_config.NumberColumn(format="%.2f"),
            "EV (%)": st.column_config.NumberColumn(format="%.2f"),
            "Kelly (%) / 凯利(%)": st.column_config.NumberColumn(format="%.2f"),
        },
    )

    with st.expander("Raw report dictionary / 原始报告字典"):
        st.json(row)


if __name__ == "__main__":
    main()
