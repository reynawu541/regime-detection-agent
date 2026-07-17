# Daily market regime research note — 2026-07-17

**Current regime: 2 (elevated) -- annualized vol 22.1%, Sharpe 0.09, historically 24% of trading days.**

## Current regime

- Regime **2** of 4 (states are numbered 0 = calmest ... 3 = most turbulent)
- Model: Gaussian HMM (`hmmlearn`), state count chosen by BIC over candidates [2, 3, 4]
- Analyst narrative source: deterministic

## Regime comparison

regime 0 (calm): ann. return 22.9%, ann. vol 10.0%, Sharpe 2.29, max drawdown -10.0%, 35% of days; regime 1 (moderate): ann. return 14.3%, ann. vol 12.2%, Sharpe 1.17, max drawdown -9.7%, 33% of days; regime 2 (elevated): ann. return 1.9%, ann. vol 22.1%, Sharpe 0.09, max drawdown -27.4%, 24% of days; regime 3 (crisis-like): ann. return 31.6%, ann. vol 34.3%, Sharpe 0.92, max drawdown -25.0%, 7% of days

## Regime statistics

|   regime |   n_days | share_of_days   | ann_return   | ann_vol   |   sharpe | max_drawdown   |   skew |   kurtosis |   n_episodes |   avg_episode_days |
|---------:|---------:|:----------------|:-------------|:----------|---------:|:---------------|-------:|-----------:|-------------:|-------------------:|
|        0 |     1427 | 35.4%           | 22.9%        | 10.0%     |     2.29 | -10.0%         |  -0.48 |       1.91 |           12 |           118.917  |
|        1 |     1331 | 33.0%           | 14.3%        | 12.2%     |     1.17 | -9.7%          |  -0.27 |       1.05 |           10 |           133.1    |
|        2 |      976 | 24.2%           | 1.9%         | 22.1%     |     0.09 | -27.4%         |   0.15 |       4.1  |           14 |            69.7143 |
|        3 |      299 | 7.4%            | 31.6%        | 34.3%     |     0.92 | -25.0%         |  -0.57 |       5.54 |            4 |            74.75   |

![Benchmark price shaded by detected regime](2026-07-17_regime_timeline.png)

## Per-regime notes

- **Regime 0**: Calm regime: 12 distinct episodes historically, averaging 119 trading days each.
- **Regime 1**: Moderate regime: 10 distinct episodes historically, averaging 133 trading days each.
- **Regime 2**: Elevated regime: 14 distinct episodes historically, averaging 70 trading days each.
- **Regime 3**: Crisis-like regime: 4 distinct episodes historically, averaging 75 trading days each.

## Method cross-check

- HMM vs GMM label agreement: 97%
- HMM vs KMeans label agreement: 87%

## Historical event sanity check

- COVID crash onset (2020-02-19): nearest trading day 2020-02-19 was regime 0
- 2022 rate-hike selloff (2022-01-01): nearest trading day 2021-12-31 was regime 2

## Caveats

Regime separation by mean return is not statistically significant (ANOVA p=0.20); regimes here primarily separate volatility, correlation-breakdown and liquidity behavior, not average forward returns. Cross-method label agreement: HMM vs GMM 97%, HMM vs KMeans 87%.

## Outlook

This note describes historical and current statistical regime characteristics only. It is not investment advice and does not predict future returns.

---

*Generated automatically by the regime-detection-agent pipeline on 2026-07-17 22:43 UTC. Universe: SPY + XLY, XLP, XLE, XLF, XLV, XLI, XLB, XLK, XLU. This note is end-of-day, backward-looking, and not investment advice.*