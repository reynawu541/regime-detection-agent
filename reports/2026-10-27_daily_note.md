# Daily market regime research note — 2026-10-27

**Current regime: 0 (calm) -- annualized vol 9.7%, Sharpe 2.20, historically 38% of trading days.**

## Current regime

- Regime **0** of 4 (states are numbered 0 = calmest ... 3 = most turbulent)
- Model: Gaussian HMM (`hmmlearn`), state count chosen by BIC over candidates [2, 3, 4]
- Analyst narrative source: deterministic

## Regime comparison

regime 0 (calm): ann. return 21.5%, ann. vol 9.7%, Sharpe 2.20, max drawdown -7.6%, 38% of days; regime 1 (moderate): ann. return 14.5%, ann. vol 11.7%, Sharpe 1.23, max drawdown -9.7%, 25% of days; regime 2 (elevated): ann. return 4.2%, ann. vol 19.7%, Sharpe 0.21, max drawdown -30.8%, 29% of days; regime 3 (crisis-like): ann. return 31.8%, ann. vol 35.7%, Sharpe 0.89, max drawdown -28.3%, 8% of days

## Regime statistics

|   regime |   n_days | share_of_days   | ann_return   | ann_vol   |   sharpe | max_drawdown   |   skew |   kurtosis |   n_episodes |   avg_episode_days |
|---------:|---------:|:----------------|:-------------|:----------|---------:|:---------------|-------:|-----------:|-------------:|-------------------:|
|        0 |     1556 | 37.9%           | 21.5%        | 9.7%      |     2.2  | -7.6%          |  -0.32 |       1.4  |           17 |            91.5294 |
|        1 |     1028 | 25.1%           | 14.5%        | 11.7%     |     1.23 | -9.7%          |  -0.3  |       1.01 |            5 |           205.6    |
|        2 |     1187 | 28.9%           | 4.2%         | 19.7%     |     0.21 | -30.8%         |  -0.34 |       1.44 |           21 |            56.5238 |
|        3 |      332 | 8.1%            | 31.8%        | 35.7%     |     0.89 | -28.3%         |  -0.2  |       5.14 |            6 |            55.3333 |

![Benchmark price shaded by detected regime](2026-10-27_regime_timeline.png)

## Per-regime notes

- **Regime 0**: Calm regime: 17 distinct episodes historically, averaging 92 trading days each.
- **Regime 1**: Moderate regime: 5 distinct episodes historically, averaging 206 trading days each.
- **Regime 2**: Elevated regime: 21 distinct episodes historically, averaging 57 trading days each.
- **Regime 3**: Crisis-like regime: 6 distinct episodes historically, averaging 55 trading days each.

## Method cross-check

- HMM vs GMM label agreement: 89%
- HMM vs KMeans label agreement: 84%

## Historical event sanity check

- COVID crash onset (2020-02-19): nearest trading day 2020-02-19 was regime 0
- 2022 rate-hike selloff (2022-01-01): nearest trading day 2021-12-31 was regime 2

## Caveats

Regime separation by mean return is not statistically significant (ANOVA p=0.25); regimes here primarily separate volatility, correlation-breakdown and liquidity behavior, not average forward returns. Cross-method label agreement: HMM vs GMM 89%, HMM vs KMeans 84%.

## Outlook

This note describes historical and current statistical regime characteristics only. It is not investment advice and does not predict future returns.

---

*Generated automatically by the regime-detection-agent pipeline on 2026-10-28 00:53 UTC. Universe: SPY + XLY, XLP, XLE, XLF, XLV, XLI, XLB, XLK, XLU. This note is end-of-day, backward-looking, and not investment advice.*