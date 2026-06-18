from pathlib import Path
import tempfile
import unittest

from worldcup_betting_edp.data import (
    build_canonical_matches_from_results,
    load_martj42_results_path,
)
from worldcup_betting_edp.models import (
    CURRENT_ELO_RATING_COLUMNS,
    ELO_1X2_PROBABILITY_COLUMNS,
    ELO_RATING_HISTORY_COLUMNS,
    EloConfig,
    EloProbabilityConfig,
    actual_home_score,
    build_elo_rating_history,
    build_elo_probability_history,
    current_elo_table,
    current_elo_ratings,
    draw_probability_from_rating_gap,
    elo_1x2_probabilities,
    expected_home_score,
    tournament_multiplier,
    update_elo_ratings,
    write_current_elo_ratings_csv,
    write_elo_probability_history_csv,
    write_elo_rating_history_csv,
)


SAMPLE_CSV = "tests/fixtures/martj42_results_sample.csv"


class EloModelTests(unittest.TestCase):
    def test_expected_score_is_half_for_equal_ratings(self) -> None:
        self.assertAlmostEqual(expected_home_score(1500.0, 1500.0), 0.5)

    def test_expected_score_reflects_rating_advantage(self) -> None:
        self.assertGreater(expected_home_score(1600.0, 1500.0), 0.5)
        self.assertGreater(expected_home_score(1500.0, 1500.0, home_advantage=60.0), 0.5)

    def test_actual_home_score_mapping(self) -> None:
        self.assertEqual(actual_home_score("home"), 1.0)
        self.assertEqual(actual_home_score("draw"), 0.5)
        self.assertEqual(actual_home_score("away"), 0.0)
        with self.assertRaises(ValueError):
            actual_home_score("cancelled")

    def test_draw_probability_declines_with_rating_gap(self) -> None:
        self.assertGreater(
            draw_probability_from_rating_gap(0.0),
            draw_probability_from_rating_gap(400.0),
        )
        self.assertGreaterEqual(draw_probability_from_rating_gap(1000.0), 0.12)

    def test_elo_1x2_probabilities_sum_to_one_and_preserve_expected_score(self) -> None:
        probabilities = elo_1x2_probabilities(home_rating=1600.0, away_rating=1500.0)
        expected = expected_home_score(1600.0, 1500.0)

        self.assertAlmostEqual(sum(probabilities.values()), 1.0)
        self.assertAlmostEqual(
            probabilities["home"] + 0.5 * probabilities["draw"],
            expected,
        )
        self.assertGreater(probabilities["home"], probabilities["away"])

    def test_elo_1x2_probabilities_support_custom_draw_config(self) -> None:
        probability_config = EloProbabilityConfig(
            base_draw_probability=0.30,
            draw_gap_penalty_per_100_elo=0.0,
            min_draw_probability=0.10,
            max_draw_probability=0.40,
        )

        probabilities = elo_1x2_probabilities(
            home_rating=1500.0,
            away_rating=1500.0,
            probability_config=probability_config,
        )

        self.assertAlmostEqual(probabilities["draw"], 0.30)
        self.assertAlmostEqual(probabilities["home"], 0.35)
        self.assertAlmostEqual(probabilities["away"], 0.35)

    def test_tournament_multiplier_defaults_unknown_to_one(self) -> None:
        self.assertEqual(tournament_multiplier("Unknown Cup"), 1.0)
        self.assertGreater(tournament_multiplier("FIFA World Cup"), 1.0)

    def test_update_elo_ratings_conserves_rating_points(self) -> None:
        home_post, away_post, expected, actual, delta = update_elo_ratings(
            home_rating=1500.0,
            away_rating=1500.0,
            result_1x2="home",
            tournament="FIFA World Cup",
        )

        self.assertAlmostEqual(expected, 0.5)
        self.assertEqual(actual, 1.0)
        self.assertAlmostEqual(delta, 15.0)
        self.assertAlmostEqual(home_post, 1515.0)
        self.assertAlmostEqual(away_post, 1485.0)
        self.assertAlmostEqual(home_post + away_post, 3000.0)

    def test_build_elo_rating_history_from_canonical_matches(self) -> None:
        results = load_martj42_results_path(SAMPLE_CSV)
        matches = build_canonical_matches_from_results(results)

        history = build_elo_rating_history(matches)

        self.assertEqual(len(history), 4)
        self.assertEqual(history[0].home_team, "France")
        self.assertEqual(history[0].away_team, "Mexico")
        self.assertAlmostEqual(history[0].home_rating_pre, 1500.0)
        self.assertAlmostEqual(history[0].away_rating_pre, 1500.0)
        self.assertAlmostEqual(history[0].rating_delta, 15.0)
        self.assertEqual(history[2].home_team, "Argentina")
        self.assertEqual(history[2].away_team, "France")
        self.assertEqual(history[2].actual_home_score, 0.5)

    def test_current_elo_ratings_returns_latest_team_ratings(self) -> None:
        results = load_martj42_results_path(SAMPLE_CSV)
        matches = build_canonical_matches_from_results(results)

        ratings = current_elo_ratings(matches)

        self.assertIn("France", ratings)
        self.assertIn("Brazil", ratings)
        self.assertGreater(ratings["Brazil"], ratings["England"])

    def test_current_elo_table_has_ranked_rows(self) -> None:
        results = load_martj42_results_path(SAMPLE_CSV)
        matches = build_canonical_matches_from_results(results)
        history = build_elo_rating_history(matches)

        table = current_elo_table(history)

        self.assertEqual(tuple(table[0].keys()), CURRENT_ELO_RATING_COLUMNS)
        self.assertGreaterEqual(table[0]["rating"], table[-1]["rating"])
        self.assertEqual(table[0]["matches_played"], 1)

    def test_build_elo_probability_history(self) -> None:
        results = load_martj42_results_path(SAMPLE_CSV)
        matches = build_canonical_matches_from_results(results)
        history = build_elo_rating_history(matches)

        probability_history = build_elo_probability_history(history)

        self.assertEqual(len(probability_history), 4)
        self.assertEqual(tuple(probability_history[0].to_dict().keys()), ELO_1X2_PROBABILITY_COLUMNS)
        self.assertEqual(probability_history[0].actual_result, "home")
        self.assertAlmostEqual(sum(probability_history[0].probabilities.values()), 1.0)

    def test_writes_elo_history_and_current_rating_csvs(self) -> None:
        results = load_martj42_results_path(SAMPLE_CSV)
        matches = build_canonical_matches_from_results(results)
        history = build_elo_rating_history(matches)

        with tempfile.TemporaryDirectory() as tmp_dir:
            history_path = Path(tmp_dir) / "elo_history.csv"
            current_path = Path(tmp_dir) / "current_elo_ratings.csv"

            written_history = write_elo_rating_history_csv(history, history_path)
            written_current = write_current_elo_ratings_csv(
                current_elo_table(history),
                current_path,
            )

            self.assertEqual(written_history, history_path)
            self.assertEqual(written_current, current_path)
            self.assertTrue(history_path.with_suffix(".csv.metadata.json").exists())
            self.assertTrue(current_path.with_suffix(".csv.metadata.json").exists())
            self.assertIn(",".join(ELO_RATING_HISTORY_COLUMNS), history_path.read_text())
            self.assertIn(",".join(CURRENT_ELO_RATING_COLUMNS), current_path.read_text())

    def test_writes_elo_probability_history_csv(self) -> None:
        results = load_martj42_results_path(SAMPLE_CSV)
        matches = build_canonical_matches_from_results(results)
        history = build_elo_rating_history(matches)
        probability_history = build_elo_probability_history(history)

        with tempfile.TemporaryDirectory() as tmp_dir:
            destination = Path(tmp_dir) / "elo_1x2_probabilities.csv"

            written = write_elo_probability_history_csv(probability_history, destination)

            self.assertEqual(written, destination)
            self.assertTrue(destination.with_suffix(".csv.metadata.json").exists())
            self.assertIn(",".join(ELO_1X2_PROBABILITY_COLUMNS), destination.read_text())

    def test_custom_config_changes_update_size(self) -> None:
        config = EloConfig(k_factor=10.0, tournament_multipliers={"FIFA World Cup": 1.0})

        home_post, away_post, _expected, _actual, delta = update_elo_ratings(
            home_rating=1500.0,
            away_rating=1500.0,
            result_1x2="home",
            tournament="FIFA World Cup",
            config=config,
        )

        self.assertAlmostEqual(delta, 5.0)
        self.assertAlmostEqual(home_post, 1505.0)
        self.assertAlmostEqual(away_post, 1495.0)


if __name__ == "__main__":
    unittest.main()
