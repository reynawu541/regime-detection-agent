from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from regime_agent.evaluation import characterize_regimes
from regime_agent.features import build_feature_matrix, select_model_features
from regime_agent.llm import run_analyst
from regime_agent.regimes import run_regime_detection


@pytest.fixture
def evaluation_and_detection(synthetic_universe, test_config):
    feats = build_feature_matrix(synthetic_universe, test_config)
    model_feats = select_model_features(feats)
    regime_detection = run_regime_detection(model_feats, test_config)
    benchmark_returns = synthetic_universe["close"]["SPY"].pct_change()
    evaluation = characterize_regimes(benchmark_returns, regime_detection, test_config)
    return evaluation, regime_detection


def _tool_use_response(name: str, input_dict: dict):
    block = SimpleNamespace(type="tool_use", name=name, input=input_dict)
    return SimpleNamespace(content=[block])


def test_run_analyst_uses_llm_finalize_report(monkeypatch, evaluation_and_detection, test_config):
    evaluation, regime_detection = evaluation_and_detection
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    response = _tool_use_response(
        "finalize_report",
        {"headline": "h", "regime_summary": "s", "per_regime_notes": {"0": "n"}, "caveats": "c", "outlook": "o"},
    )

    with patch("anthropic.Anthropic") as mock_anthropic_cls:
        mock_client = mock_anthropic_cls.return_value
        mock_client.messages.create.return_value = response
        result = run_analyst(evaluation, regime_detection, test_config)

    assert result.source == "llm"
    assert result.headline == "h"
    assert result.rerun_requested is None

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["tool_choice"] == {"type": "any"}
    assert len(call_kwargs["tools"]) == 2


def test_run_analyst_uses_llm_request_rerun(monkeypatch, evaluation_and_detection, test_config):
    evaluation, regime_detection = evaluation_and_detection
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    response = _tool_use_response("request_rerun", {"n_states": 2, "reason": "looks degenerate"})

    with patch("anthropic.Anthropic") as mock_anthropic_cls:
        mock_client = mock_anthropic_cls.return_value
        mock_client.messages.create.return_value = response
        result = run_analyst(evaluation, regime_detection, test_config)

    assert result.rerun_requested == 2
    assert result.rerun_reason == "looks degenerate"


def test_run_analyst_forces_finalize_tool_when_rerun_disallowed(
    monkeypatch, evaluation_and_detection, test_config
):
    evaluation, regime_detection = evaluation_and_detection
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    response = _tool_use_response(
        "finalize_report",
        {"headline": "h", "regime_summary": "s", "per_regime_notes": {}, "caveats": "c", "outlook": "o"},
    )

    with patch("anthropic.Anthropic") as mock_anthropic_cls:
        mock_client = mock_anthropic_cls.return_value
        mock_client.messages.create.return_value = response
        run_analyst(evaluation, regime_detection, test_config, allow_rerun=False)

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["tool_choice"] == {"type": "tool", "name": "finalize_report"}
    assert len(call_kwargs["tools"]) == 1


def test_run_analyst_falls_back_without_api_key(monkeypatch, evaluation_and_detection, test_config):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    evaluation, regime_detection = evaluation_and_detection

    with patch("anthropic.Anthropic") as mock_anthropic_cls:
        result = run_analyst(evaluation, regime_detection, test_config)

    mock_anthropic_cls.assert_not_called()
    assert result.source == "deterministic"
