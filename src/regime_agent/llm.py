from __future__ import annotations

import os
from dataclasses import dataclass, field

import pandas as pd

from .evaluation import RegimeCharacterization

_SYSTEM_PROMPT = """You are the analyst agent in an autonomous market-regime-detection \
research pipeline. You receive statistical output from a Gaussian HMM segmentation of \
S&P 500 sector-ETF data into volatility/correlation/liquidity regimes (states are ordered \
0 = calmest ... N-1 = most turbulent).

Your job, in order:
1. Decide whether the segmentation is statistically sound. If the data-quality flags show a \
near-degenerate or indistinguishable regime, you may request exactly ONE re-run with fewer states.
2. Otherwise, write the structured content for today's daily research note.

Rules:
- Be precise about statistical significance. Do not claim regimes predict average returns if the \
separation test p-value is not significant (p > 0.05) -- say so plainly instead.
- Never give investment advice, price targets, or trade recommendations.
- Use only the exact numbers provided in the prompt. Do not invent figures.
- Be concise and quantitative: this is a research note, not marketing copy.
"""

_TOOLS = [
    {
        "name": "request_rerun",
        "description": (
            "Request the regime model be refit with a different (smaller) number of states, "
            "because the current segmentation has a near-degenerate or statistically "
            "indistinguishable regime."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "n_states": {"type": "integer", "description": "New number of regimes to fit."},
                "reason": {"type": "string"},
            },
            "required": ["n_states", "reason"],
        },
    },
    {
        "name": "finalize_report",
        "description": "Submit the final structured write-up for today's regime research note.",
        "input_schema": {
            "type": "object",
            "properties": {
                "headline": {"type": "string", "description": "One-sentence current-regime headline."},
                "regime_summary": {"type": "string", "description": "2-4 sentence summary comparing all regimes."},
                "per_regime_notes": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                    "description": "Map of state index (as string) to a 1-2 sentence note.",
                },
                "caveats": {"type": "string", "description": "Statistical caveats and data-quality flags."},
                "outlook": {"type": "string", "description": "Closing note. Must not be investment advice."},
            },
            "required": ["headline", "regime_summary", "per_regime_notes", "caveats", "outlook"],
        },
    },
]

_FINALIZE_TOOL = _TOOLS[1]


@dataclass
class AnalystOutput:
    headline: str
    regime_summary: str
    per_regime_notes: dict[str, str]
    caveats: str
    outlook: str
    rerun_requested: int | None = None
    rerun_reason: str | None = None
    source: str = "llm"


def _qualitative_tag(state: int, n_states: int) -> str:
    labels_by_n = {
        2: ["calm", "turbulent"],
        3: ["calm", "moderate", "turbulent"],
        4: ["calm", "moderate", "elevated", "crisis-like"],
        5: ["calm", "steady", "moderate", "elevated", "crisis-like"],
    }
    bucket = labels_by_n.get(n_states)
    if bucket is None:
        bucket = [f"state {i}" for i in range(n_states)]
    return bucket[state]


def _build_prompt(evaluation: RegimeCharacterization, regime_detection: dict, config: dict, note: str) -> str:
    n_states = regime_detection["chosen_n_states"]
    stats = evaluation.stats.copy()
    stats.index.name = "state"
    stats_text = stats.round(4).to_markdown()

    lines = [
        f"Number of states fit: {n_states} (BIC-selected from {config['regimes']['candidate_n_states']})",
        f"BIC curve: {regime_detection['bic_curve']}",
        "",
        "Per-regime statistics (ann_return/ann_vol are annualized; share_of_days is the "
        "fraction of the full history spent in that regime):",
        stats_text,
        "",
        f"Current regime (most recent trading day): {evaluation.current_regime} "
        f"({_qualitative_tag(evaluation.current_regime, n_states)})",
        f"ANOVA p-value for mean-return separation across regimes: {evaluation.separation_pvalue:.4f}",
        f"Cross-method label agreement: HMM vs GMM = {evaluation.method_agreement['hmm_vs_gmm']:.2%}, "
        f"HMM vs KMeans = {evaluation.method_agreement['hmm_vs_kmeans']:.2%}",
        f"Data-quality flags: {evaluation.flags if evaluation.flags else 'none'}",
        f"Known-event sanity check: {evaluation.event_check if evaluation.event_check else 'no configured events in range'}",
    ]
    if note:
        lines.append("")
        lines.append(note)
    return "\n".join(lines)


def _deterministic_analyst(
    evaluation: RegimeCharacterization, regime_detection: dict, config: dict, allow_rerun: bool
) -> AnalystOutput:
    if allow_rerun and evaluation.flags:
        candidates = config["regimes"]["candidate_n_states"]
        current = regime_detection["chosen_n_states"]
        smaller = [c for c in candidates if c < current]
        if smaller:
            return AnalystOutput(
                headline="",
                regime_summary="",
                per_regime_notes={},
                caveats="",
                outlook="",
                rerun_requested=max(smaller),
                rerun_reason="; ".join(evaluation.flags),
                source="deterministic",
            )

    n_states = regime_detection["chosen_n_states"]
    stats = evaluation.stats
    current = evaluation.current_regime
    tag = _qualitative_tag(current, n_states)
    row = stats.loc[current]

    headline = (
        f"Current regime: {current} ({tag}) -- annualized vol {row['ann_vol']:.1%}, "
        f"Sharpe {row['sharpe']:.2f}, historically {row['share_of_days']:.0%} of trading days."
    )

    regime_summary = "; ".join(
        f"regime {s} ({_qualitative_tag(s, n_states)}): ann. return {r['ann_return']:.1%}, "
        f"ann. vol {r['ann_vol']:.1%}, Sharpe {r['sharpe']:.2f}, "
        f"max drawdown {r['max_drawdown']:.1%}, {r['share_of_days']:.0%} of days"
        for s, r in stats.iterrows()
    )

    per_regime_notes = {
        str(s): (
            f"{_qualitative_tag(s, n_states).capitalize()} regime: {int(r['n_episodes'])} distinct "
            f"episodes historically, averaging {r['avg_episode_days']:.0f} trading days each."
        )
        for s, r in stats.iterrows()
    }

    significant = evaluation.separation_pvalue <= 0.05
    caveats = (
        f"Regime separation by mean return is {'' if significant else 'not '}statistically significant "
        f"(ANOVA p={evaluation.separation_pvalue:.2f}); regimes here primarily separate volatility, "
        f"correlation-breakdown and liquidity behavior, not average forward returns. "
        f"Cross-method label agreement: HMM vs GMM {evaluation.method_agreement['hmm_vs_gmm']:.0%}, "
        f"HMM vs KMeans {evaluation.method_agreement['hmm_vs_kmeans']:.0%}."
    )
    if evaluation.flags:
        caveats += " Data-quality flags: " + "; ".join(evaluation.flags)

    outlook = (
        "This note describes historical and current statistical regime characteristics only. "
        "It is not investment advice and does not predict future returns."
    )

    return AnalystOutput(
        headline=headline,
        regime_summary=regime_summary,
        per_regime_notes=per_regime_notes,
        caveats=caveats,
        outlook=outlook,
        source="deterministic",
    )


def run_analyst(
    evaluation: RegimeCharacterization,
    regime_detection: dict,
    config: dict,
    allow_rerun: bool = True,
    note: str = "",
) -> AnalystOutput:
    """Reviews regime stats and either requests one bounded re-run or finalizes the
    report narrative. Uses Claude tool-calling when ANTHROPIC_API_KEY is set, otherwise
    falls back to a deterministic template so the pipeline runs with no API key."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return _deterministic_analyst(evaluation, regime_detection, config, allow_rerun)

    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    model = os.environ.get(config["llm"]["model_env_var"], config["llm"]["default_model"])
    prompt = _build_prompt(evaluation, regime_detection, config, note)

    tools = _TOOLS if allow_rerun else [_FINALIZE_TOOL]
    tool_choice = (
        {"type": "any"} if allow_rerun else {"type": "tool", "name": "finalize_report"}
    )

    response = client.messages.create(
        model=model,
        max_tokens=1500,
        system=_SYSTEM_PROMPT,
        tools=tools,
        tool_choice=tool_choice,
        messages=[{"role": "user", "content": prompt}],
    )

    for block in response.content:
        if block.type != "tool_use":
            continue
        if block.name == "finalize_report":
            return AnalystOutput(**block.input, source="llm")
        if block.name == "request_rerun":
            return AnalystOutput(
                headline="",
                regime_summary="",
                per_regime_notes={},
                caveats="",
                outlook="",
                rerun_requested=block.input["n_states"],
                rerun_reason=block.input.get("reason"),
                source="llm",
            )

    return _deterministic_analyst(evaluation, regime_detection, config, allow_rerun)
