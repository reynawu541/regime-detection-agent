# Daily market regime research note — 2026-11-06

**Current regime: 2 (elevated) -- annualized vol 19.8%, Sharpe 0.13, historically 29% of trading days.**

## Current regime

- Regime **2** of 4 (states are numbered 0 = calmest ... 3 = most turbulent)
- Model: Gaussian HMM (`hmmlearn`), state count chosen by BIC over candidates [2, 3, 4]
- Analyst narrative source: deterministic

## Regime comparison

regime 0 (calm): ann. return 22.4%, ann. vol 9.7%, Sharpe 2.31, max drawdown -7.6%, 38% of days; regime 1 (moderate): ann. return 14.0%, ann. vol 11.8%, Sharpe 1.18, max drawdown -9.7%, 24% of days; regime 2 (elevated): ann. return 2.5%, ann. vol 19.8%, Sharpe 0.13, max drawdown -32.9%, 29% of days; regime 3 (crisis-like): ann. return 31.8%, ann. vol 35.7%, Sharpe 0.89, max drawdown -28.3%, 8% of days

## Regime statistics

|   regime |   n_days | share_of_days   | ann_return   | ann_vol   |   sharpe | max_drawdown   |   skew |   kurtosis |   n_episodes |   avg_episode_days |
|---------:|---------:|:----------------|:-------------|:----------|---------:|:---------------|-------:|-----------:|-------------:|-------------------:|
|        0 |     1573 | 38.3%           | 22.4%        | 9.7%      |     2.31 | -7.6%          |  -0.31 |       1.42 |           17 |            92.5294 |
|        1 |     1004 | 24.4%           | 14.0%        | 11.8%     |     1.18 | -9.7%          |  -0.3  |       0.98 |            4 |           251      |
|        2 |     1202 | 29.2%           | 2.5%         | 19.8%     |     0.13 | -32.9%         |  -0.36 |       1.48 |           22 |            54.6364 |
|        3 |      332 | 8.1%            | 31.8%        | 35.7%     |     0.89 | -28.3%         |  -0.2  |       5.14 |            6 |            55.3333 |

![Benchmark price shaded by detected regime](2026-11-06_regime_timeline.png)

## Per-regime notes

- **Regime 0**: Calm regime: 17 distinct episodes historically, averaging 93 trading days each.
- **Regime 1**: Moderate regime: 4 distinct episodes historically, averaging 251 trading days each.
- **Regime 2**: Elevated regime: 22 distinct episodes historically, averaging 55 trading days each.
- **Regime 3**: Crisis-like regime: 6 distinct episodes historically, averaging 55 trading days each.

## Method cross-check

- HMM vs GMM label agreement: 85%
- HMM vs KMeans label agreement: 84%

## Historical event sanity check

- COVID crash onset (2020-02-19): nearest trading day 2020-02-19 was regime 0
- 2022 rate-hike selloff (2022-01-01): nearest trading day 2021-12-31 was regime 2

## Caveats

Regime separation by mean return is not statistically significant (ANOVA p=0.17); regimes here primarily separate volatility, correlation-breakdown and liquidity behavior, not average forward returns. Cross-method label agreement: HMM vs GMM 85%, HMM vs KMeans 84%.

## Outlook

This note describes historical and current statistical regime characteristics only. It is not investment advice and does not predict future returns.

---

*Generated automatically by the regime-detection-agent pipeline on 2026-11-07 01:31 UTC. Universe: SPY + XLY, XLP, XLE, XLF, XLV, XLI, XLB, XLK, XLU. This note is end-of-day, backward-looking, and not investment advice.*