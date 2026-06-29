# Daily market regime research note — 2026-06-29

**Current regime: 2 (elevated) -- annualized vol 21.2%, Sharpe 0.26, historically 29% of trading days.**

## Current regime

- Regime **2** of 4 (states are numbered 0 = calmest ... 3 = most turbulent)
- Model: Gaussian HMM (`hmmlearn`), state count chosen by BIC over candidates [2, 3, 4]
- Analyst narrative source: deterministic

## Regime comparison

regime 0 (calm): ann. return 21.2%, ann. vol 10.1%, Sharpe 2.10, max drawdown -10.0%, 40% of days; regime 1 (moderate): ann. return 13.5%, ann. vol 11.8%, Sharpe 1.14, max drawdown -9.7%, 25% of days; regime 2 (elevated): ann. return 5.4%, ann. vol 21.2%, Sharpe 0.26, max drawdown -27.4%, 29% of days; regime 3 (crisis-like): ann. return 34.9%, ann. vol 35.6%, Sharpe 0.98, max drawdown -24.8%, 7% of days

## Regime statistics

|   regime |   n_days | share_of_days   | ann_return   | ann_vol   |   sharpe | max_drawdown   |   skew |   kurtosis |   n_episodes |   avg_episode_days |
|---------:|---------:|:----------------|:-------------|:----------|---------:|:---------------|-------:|-----------:|-------------:|-------------------:|
|        0 |     1590 | 39.6%           | 21.2%        | 10.1%     |     2.1  | -10.0%         |  -0.42 |       1.83 |           13 |            122.308 |
|        1 |     1004 | 25.0%           | 13.5%        | 11.8%     |     1.14 | -9.7%          |  -0.31 |       0.98 |            3 |            334.667 |
|        2 |     1156 | 28.8%           | 5.4%         | 21.2%     |     0.26 | -27.4%         |   0.07 |       4.23 |           17 |             68     |
|        3 |      270 | 6.7%            | 34.9%        | 35.6%     |     0.98 | -24.8%         |  -0.55 |       5.07 |            3 |             90     |

![Benchmark price shaded by detected regime](2026-06-29_regime_timeline.png)

## Per-regime notes

- **Regime 0**: Calm regime: 13 distinct episodes historically, averaging 122 trading days each.
- **Regime 1**: Moderate regime: 3 distinct episodes historically, averaging 335 trading days each.
- **Regime 2**: Elevated regime: 17 distinct episodes historically, averaging 68 trading days each.
- **Regime 3**: Crisis-like regime: 3 distinct episodes historically, averaging 90 trading days each.

## Method cross-check

- HMM vs GMM label agreement: 89%
- HMM vs KMeans label agreement: 80%

## Historical event sanity check

- COVID crash onset (2020-02-19): nearest trading day 2020-02-19 was regime 0
- 2022 rate-hike selloff (2022-01-01): nearest trading day 2021-12-31 was regime 2

## Caveats

Regime separation by mean return is not statistically significant (ANOVA p=0.29); regimes here primarily separate volatility, correlation-breakdown and liquidity behavior, not average forward returns. Cross-method label agreement: HMM vs GMM 89%, HMM vs KMeans 80%.

## Outlook

This note describes historical and current statistical regime characteristics only. It is not investment advice and does not predict future returns.

---

*Generated automatically by the regime-detection-agent pipeline on 2026-06-29 22:24 UTC. Universe: SPY + XLY, XLP, XLE, XLF, XLV, XLI, XLB, XLK, XLU. This note is end-of-day, backward-looking, and not investment advice.*