# Daily market regime research note — 2026-10-30

**Current regime: 0 (calm) -- annualized vol 9.9%, Sharpe 2.25, historically 36% of trading days.**

## Current regime

- Regime **0** of 4 (states are numbered 0 = calmest ... 3 = most turbulent)
- Model: Gaussian HMM (`hmmlearn`), state count chosen by BIC over candidates [2, 3, 4]
- Analyst narrative source: deterministic

## Regime comparison

regime 0 (calm): ann. return 22.4%, ann. vol 9.9%, Sharpe 2.25, max drawdown -10.0%, 36% of days; regime 1 (moderate): ann. return 15.0%, ann. vol 12.1%, Sharpe 1.24, max drawdown -9.8%, 33% of days; regime 2 (elevated): ann. return 0.9%, ann. vol 21.0%, Sharpe 0.04, max drawdown -28.2%, 23% of days; regime 3 (crisis-like): ann. return 29.1%, ann. vol 35.5%, Sharpe 0.82, max drawdown -32.3%, 8% of days

## Regime statistics

|   regime |   n_days | share_of_days   | ann_return   | ann_vol   |   sharpe | max_drawdown   |   skew |   kurtosis |   n_episodes |   avg_episode_days |
|---------:|---------:|:----------------|:-------------|:----------|---------:|:---------------|-------:|-----------:|-------------:|-------------------:|
|        0 |     1475 | 35.9%           | 22.4%        | 9.9%      |     2.25 | -10.0%         |  -0.42 |       1.52 |           15 |            98.3333 |
|        1 |     1367 | 33.3%           | 15.0%        | 12.1%     |     1.24 | -9.8%          |  -0.28 |       1.09 |           11 |           124.273  |
|        2 |      931 | 22.7%           | 0.9%         | 21.0%     |     0.04 | -28.2%         |  -0.28 |       1.26 |           15 |            62.0667 |
|        3 |      333 | 8.1%            | 29.1%        | 35.5%     |     0.82 | -32.3%         |  -0.21 |       5.31 |            6 |            55.5    |

![Benchmark price shaded by detected regime](2026-10-30_regime_timeline.png)

## Per-regime notes

- **Regime 0**: Calm regime: 15 distinct episodes historically, averaging 98 trading days each.
- **Regime 1**: Moderate regime: 11 distinct episodes historically, averaging 124 trading days each.
- **Regime 2**: Elevated regime: 15 distinct episodes historically, averaging 62 trading days each.
- **Regime 3**: Crisis-like regime: 6 distinct episodes historically, averaging 56 trading days each.

## Method cross-check

- HMM vs GMM label agreement: 97%
- HMM vs KMeans label agreement: 86%

## Historical event sanity check

- COVID crash onset (2020-02-19): nearest trading day 2020-02-19 was regime 0
- 2022 rate-hike selloff (2022-01-01): nearest trading day 2021-12-31 was regime 2

## Caveats

Regime separation by mean return is not statistically significant (ANOVA p=0.21); regimes here primarily separate volatility, correlation-breakdown and liquidity behavior, not average forward returns. Cross-method label agreement: HMM vs GMM 97%, HMM vs KMeans 86%.

## Outlook

This note describes historical and current statistical regime characteristics only. It is not investment advice and does not predict future returns.

---

*Generated automatically by the regime-detection-agent pipeline on 2026-10-31 01:22 UTC. Universe: SPY + XLY, XLP, XLE, XLF, XLV, XLI, XLB, XLK, XLU. This note is end-of-day, backward-looking, and not investment advice.*