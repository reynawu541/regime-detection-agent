# Daily market regime research note — 2026-10-26

**Current regime: 0 (calm) -- annualized vol 10.1%, Sharpe 2.10, historically 36% of trading days.**

## Current regime

- Regime **0** of 4 (states are numbered 0 = calmest ... 3 = most turbulent)
- Model: Gaussian HMM (`hmmlearn`), state count chosen by BIC over candidates [2, 3, 4]
- Analyst narrative source: deterministic

## Regime comparison

regime 0 (calm): ann. return 21.2%, ann. vol 10.1%, Sharpe 2.10, max drawdown -10.0%, 36% of days; regime 1 (moderate): ann. return 15.5%, ann. vol 12.2%, Sharpe 1.27, max drawdown -9.7%, 33% of days; regime 2 (elevated): ann. return 1.2%, ann. vol 22.1%, Sharpe 0.06, max drawdown -27.4%, 24% of days; regime 3 (crisis-like): ann. return 34.7%, ann. vol 34.4%, Sharpe 1.01, max drawdown -25.0%, 7% of days

## Regime statistics

|   regime |   n_days | share_of_days   | ann_return   | ann_vol   |   sharpe | max_drawdown   |   skew |   kurtosis |   n_episodes |   avg_episode_days |
|---------:|---------:|:----------------|:-------------|:----------|---------:|:---------------|-------:|-----------:|-------------:|-------------------:|
|        0 |     1477 | 36.0%           | 21.2%        | 10.1%     |     2.1  | -10.0%         |  -0.52 |       2.07 |           15 |            98.4667 |
|        1 |     1356 | 33.1%           | 15.5%        | 12.2%     |     1.27 | -9.7%          |  -0.27 |       1.05 |           10 |           135.6    |
|        2 |      978 | 23.8%           | 1.2%         | 22.1%     |     0.06 | -27.4%         |   0.13 |       4.1  |           16 |            61.125  |
|        3 |      291 | 7.1%            | 34.7%        | 34.4%     |     1.01 | -25.0%         |  -0.56 |       5.62 |            3 |            97      |

![Benchmark price shaded by detected regime](2026-10-26_regime_timeline.png)

## Per-regime notes

- **Regime 0**: Calm regime: 15 distinct episodes historically, averaging 98 trading days each.
- **Regime 1**: Moderate regime: 10 distinct episodes historically, averaging 136 trading days each.
- **Regime 2**: Elevated regime: 16 distinct episodes historically, averaging 61 trading days each.
- **Regime 3**: Crisis-like regime: 3 distinct episodes historically, averaging 97 trading days each.

## Method cross-check

- HMM vs GMM label agreement: 96%
- HMM vs KMeans label agreement: 87%

## Historical event sanity check

- COVID crash onset (2020-02-19): nearest trading day 2020-02-19 was regime 0
- 2022 rate-hike selloff (2022-01-01): nearest trading day 2021-12-31 was regime 2

## Caveats

Regime separation by mean return is not statistically significant (ANOVA p=0.18); regimes here primarily separate volatility, correlation-breakdown and liquidity behavior, not average forward returns. Cross-method label agreement: HMM vs GMM 96%, HMM vs KMeans 87%.

## Outlook

This note describes historical and current statistical regime characteristics only. It is not investment advice and does not predict future returns.

---

*Generated automatically by the regime-detection-agent pipeline on 2026-10-27 01:03 UTC. Universe: SPY + XLY, XLP, XLE, XLF, XLV, XLI, XLB, XLK, XLU. This note is end-of-day, backward-looking, and not investment advice.*