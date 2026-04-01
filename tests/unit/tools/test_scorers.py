"""Unit tests for tools/eval/scorers.py."""

from unittest.mock import MagicMock, patch

import pytest

from tools.eval.scorers import score_tier1, score_tier2, validate_output_schema


# ---------------------------------------------------------------------------
# score_tier1
# ---------------------------------------------------------------------------

class TestScoreTier1:
    def _labels(self, good_terms, bad_terms, expected_score):
        return {"good_terms": good_terms, "bad_terms": bad_terms, "expected_score": expected_score}

    def test_high_precision_low_bad_rate(self):
        output = {
            "extracted_terms": ["Azure Arc", "Copilot stack", "intelligent cloud"],
            "relevance_score": 8,
        }
        labels = self._labels(
            good_terms=["azure arc", "copilot stack", "intelligent cloud"],
            bad_terms=["pleased to report"],
            expected_score=8,
        )
        result = score_tier1([output], [labels])
        assert result["term_precision"] == pytest.approx(1.0)
        assert result["bad_term_rate"] == pytest.approx(0.0)
        assert result["score_mae"] == pytest.approx(0.0)
        assert result["n_chunks"] == 1

    def test_low_precision_high_bad_rate(self):
        output = {
            "extracted_terms": ["pleased to report", "year-over-year", "Azure Arc"],
            "relevance_score": 3,
        }
        labels = self._labels(
            good_terms=["azure arc"],
            bad_terms=["pleased to report", "year-over-year"],
            expected_score=7,
        )
        result = score_tier1([output], [labels])
        # 1 good out of 3 total
        assert result["term_precision"] == pytest.approx(1 / 3, rel=1e-3)
        # 2 bad out of 3 total
        assert result["bad_term_rate"] == pytest.approx(2 / 3, rel=1e-3)
        # |3 - 7| = 4
        assert result["score_mae"] == pytest.approx(4.0)

    def test_score_mae_calculation(self):
        outputs = [
            {"extracted_terms": ["foo"], "relevance_score": 6},
            {"extracted_terms": ["bar"], "relevance_score": 9},
        ]
        labels_list = [
            self._labels(good_terms=["foo"], bad_terms=[], expected_score=5),
            self._labels(good_terms=["bar"], bad_terms=[], expected_score=7),
        ]
        result = score_tier1(outputs, labels_list)
        # MAE = (|6-5| + |9-7|) / 2 = (1 + 2) / 2 = 1.5
        assert result["score_mae"] == pytest.approx(1.5)
        assert result["n_chunks"] == 2

    def test_empty_terms_list(self):
        output = {"extracted_terms": [], "relevance_score": 5}
        labels = self._labels(good_terms=["foo"], bad_terms=["bar"], expected_score=5)
        result = score_tier1([output], [labels])
        assert result["term_precision"] == pytest.approx(0.0)
        assert result["bad_term_rate"] == pytest.approx(0.0)
        assert result["score_mae"] == pytest.approx(0.0)
        assert result["n_chunks"] == 1

    def test_empty_inputs(self):
        result = score_tier1([], [])
        assert result["n_chunks"] == 0

    def test_errored_chunks_are_skipped(self):
        outputs = [
            {"error": "LLM error: timeout"},
            {"extracted_terms": ["Azure Arc"], "relevance_score": 7},
        ]
        labels_list = [
            self._labels(good_terms=["azure arc"], bad_terms=[], expected_score=8),
            self._labels(good_terms=["azure arc"], bad_terms=[], expected_score=7),
        ]
        result = score_tier1(outputs, labels_list)
        assert result["n_chunks"] == 1
        assert result["term_precision"] == pytest.approx(1.0)

    def test_case_insensitive_term_matching(self):
        output = {"extracted_terms": ["AZURE ARC", "Copilot Stack"], "relevance_score": 8}
        labels = self._labels(
            good_terms=["azure arc", "copilot stack"],
            bad_terms=[],
            expected_score=8,
        )
        result = score_tier1([output], [labels])
        assert result["term_precision"] == pytest.approx(1.0)

    def test_averaging_across_chunks(self):
        outputs = [
            {"extracted_terms": ["foo", "bar"], "relevance_score": 5},  # 1/2 precision
            {"extracted_terms": ["baz"], "relevance_score": 7},           # 0/1 precision
        ]
        labels_list = [
            self._labels(good_terms=["foo"], bad_terms=[], expected_score=5),
            self._labels(good_terms=["qux"], bad_terms=[], expected_score=7),
        ]
        result = score_tier1(outputs, labels_list)
        # precision = (0.5 + 0.0) / 2 = 0.25
        assert result["term_precision"] == pytest.approx(0.25)
        assert result["n_chunks"] == 2


# ---------------------------------------------------------------------------
# score_tier2
# ---------------------------------------------------------------------------

class TestScoreTier2:
    CHUNK_TEXT = (
        "Analyst: Can you explain why operating margins declined by 200 basis points? "
        "Executive: We are confident in our long-term margin expansion story."
    )

    def _make_output(self, takeaways=None, evasion=None, misconceptions=None, speakers=None):
        return {
            "takeaways": takeaways or [],
            "evasion": evasion or [],
            "misconceptions": misconceptions or [],
            "speakers": speakers or [],
        }

    @patch("tools.eval.scorers.anthropic.Anthropic")
    def test_verbatim_match_present(self, mock_anthropic_class):
        # mock_anthropic_class IS the Anthropic constructor mock
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text="4")]
        mock_client.messages.create.return_value = mock_message

        output = self._make_output(
            takeaways=[{"takeaway": "Margins declined 200 bps due to cost pressure"}],
            evasion=[{
                "question_text": "Can you explain why operating margins declined by 200 basis points",
                "answer_text": "We are confident in our long-term margin expansion story",
                "evasion_type": "deflection",
            }],
            speakers=["Analyst", "Executive"],
        )
        result = score_tier2(output, self.CHUNK_TEXT)
        assert result["evasion_verbatim_rate"] == pytest.approx(1.0)
        assert result["completeness_rate"] > 0.0

    @patch("tools.eval.scorers.anthropic.Anthropic")
    def test_verbatim_match_missing(self, mock_anthropic_class):
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        mock_client.messages.create.return_value = MagicMock(content=[MagicMock(text="3")])

        output = self._make_output(
            evasion=[{
                "question_text": "This question text does not appear in the chunk at all",
                "answer_text": "Neither does this answer text",
                "evasion_type": "deflection",
            }],
        )
        result = score_tier2(output, self.CHUNK_TEXT)
        assert result["evasion_verbatim_rate"] == pytest.approx(0.0)

    @patch("tools.eval.scorers.anthropic.Anthropic")
    def test_completeness_full(self, mock_anthropic_class):
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        mock_client.messages.create.return_value = MagicMock(content=[MagicMock(text="4")])

        output = self._make_output(
            takeaways=[{"takeaway": "Margins compressed"}],
            evasion=[{"question_text": "q", "answer_text": "a", "evasion_type": "t"}],
            misconceptions=["Margins are always improving"],
            speakers=["CEO", "Analyst"],
        )
        result = score_tier2(output, self.CHUNK_TEXT)
        assert result["completeness_rate"] == pytest.approx(1.0)

    @patch("tools.eval.scorers.anthropic.Anthropic")
    def test_completeness_partial(self, mock_anthropic_class):
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        mock_client.messages.create.return_value = MagicMock(content=[MagicMock(text="3")])

        # Missing misconceptions and speakers
        output = self._make_output(
            takeaways=[{"takeaway": "Margins compressed"}],
        )
        result = score_tier2(output, self.CHUNK_TEXT)
        # Only takeaways is populated (1/4)
        assert result["completeness_rate"] == pytest.approx(1 / 4)

    @patch("tools.eval.scorers.anthropic.Anthropic")
    def test_takeaway_scoring_with_mocked_judge(self, mock_anthropic_class):
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        # Judge always returns "4"
        mock_client.messages.create.return_value = MagicMock(content=[MagicMock(text="4")])

        output = self._make_output(
            takeaways=[
                {"takeaway": "Operating margins declined 200bps due to elevated R&D spend"},
                {"takeaway": "Revenue guidance raised for next quarter"},
            ],
        )
        result = score_tier2(output, self.CHUNK_TEXT)
        assert result["takeaway_specificity_avg"] == pytest.approx(4.0)

    def test_errored_chunk_returns_zeros(self):
        output = {"error": "LLM error: timeout"}
        result = score_tier2(output, self.CHUNK_TEXT)
        assert result["takeaway_specificity_avg"] == pytest.approx(0.0)
        assert result["evasion_verbatim_rate"] == pytest.approx(0.0)
        assert result["completeness_rate"] == pytest.approx(0.0)
        assert result["n_chunks"] == 1

    @patch("tools.eval.scorers.anthropic.Anthropic")
    def test_no_evasion_items_verbatim_rate_is_one(self, mock_anthropic_class):
        """When there are no evasion items, verbatim_rate defaults to 1.0 (nothing to fail)."""
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        mock_client.messages.create.return_value = MagicMock(content=[MagicMock(text="3")])

        output = self._make_output(takeaways=[{"takeaway": "Revenue grew 12%"}])
        result = score_tier2(output, self.CHUNK_TEXT)
        assert result["evasion_verbatim_rate"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# validate_output_schema
# ---------------------------------------------------------------------------

class TestValidateOutputSchema:
    def _tier1_output(self, **overrides):
        base = {
            "relevance_score": 7,
            "extracted_terms": ["Azure Arc"],
            "chunk_category": "prepared_remarks",
        }
        base.update(overrides)
        return base

    def _tier2_output(self, **overrides):
        base = {
            "takeaways": [{"takeaway": "margins compressed"}],
            "evasion": [{
                "question_text": "Why?",
                "answer_text": "We are confident.",
                "evasion_type": "deflection",
            }],
            "misconceptions": ["margins always improve"],
            "speakers": ["CEO"],
        }
        base.update(overrides)
        return base

    def test_tier1_valid_passes(self):
        result = validate_output_schema([self._tier1_output()], "tier1")
        assert result["schema_pass_rate"] == pytest.approx(1.0)
        assert result["violations"] == []

    def test_tier1_missing_field(self):
        output = self._tier1_output()
        del output["extracted_terms"]
        result = validate_output_schema([output], "tier1")
        assert result["schema_pass_rate"] == pytest.approx(0.0)
        fields = [v["field"] for v in result["violations"]]
        assert "extracted_terms" in fields

    def test_tier1_wrong_type_list_field(self):
        output = self._tier1_output(extracted_terms="not a list")
        result = validate_output_schema([output], "tier1")
        assert result["schema_pass_rate"] == pytest.approx(0.0)
        violation = next(v for v in result["violations"] if v["field"] == "extracted_terms")
        assert "expected" in violation["violation"]

    def test_tier1_out_of_range_score(self):
        output = self._tier1_output(relevance_score=11)
        result = validate_output_schema([output], "tier1")
        assert result["schema_pass_rate"] == pytest.approx(0.0)
        violation = next(v for v in result["violations"] if v["field"] == "relevance_score")
        assert "out of range" in violation["violation"]

    def test_tier2_valid_passes(self):
        result = validate_output_schema([self._tier2_output()], "tier2")
        assert result["schema_pass_rate"] == pytest.approx(1.0)
        assert result["violations"] == []

    def test_tier2_nested_evasion_field_missing(self):
        output = self._tier2_output()
        # Remove question_text from first evasion item
        del output["evasion"][0]["question_text"]
        result = validate_output_schema([output], "tier2")
        assert result["schema_pass_rate"] == pytest.approx(0.0)
        fields = [v["field"] for v in result["violations"]]
        assert "evasion[0].question_text" in fields

    def test_errored_chunks_skipped(self):
        outputs = [
            {"error": "LLM error"},
            self._tier1_output(),
        ]
        result = validate_output_schema(outputs, "tier1")
        # Only 1 real chunk, it passes
        assert result["schema_pass_rate"] == pytest.approx(1.0)

    def test_pass_rate_partial(self):
        outputs = [
            self._tier1_output(),
            self._tier1_output(relevance_score=15),  # out of range
        ]
        result = validate_output_schema(outputs, "tier1")
        assert result["schema_pass_rate"] == pytest.approx(0.5)

    def test_unknown_phase_returns_full_pass(self):
        result = validate_output_schema([{"foo": "bar"}], "tier99")
        assert result["schema_pass_rate"] == pytest.approx(1.0)
        assert result["violations"] == []
