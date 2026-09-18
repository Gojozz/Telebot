# VCPM v1 — RESEARCH FREEZE

Status: FROZEN RESEARCH FEATURE
Asset / timeframe: SOLUSDT 1H
Dataset: 20,000 real OHLCV rows
OOS status: CONSUMED / CLOSED
Freeze date: 2026-09-18

## 1. Hypothesis

VCPM (Volatility-Conditioned Participation Magnitude) tests whether
abnormal market participation contains information about the magnitude
of the next 24-hour price movement after conditioning on current volatility.

VCPM is a MAGNITUDE feature.

It is NOT a directional signal.

It must not be interpreted as:
- high volume -> BUY
- high volume -> SELL
- high volatility -> automatic trade

## 2. Frozen Definitions

Current volatility:
- RMS of the preceding 24 completed 1H returns.

Participation:
- current volume divided by the causal median volume for the same UTC hour.
- baseline uses prior observations only.
- minimum 20 historical observations required.

Future magnitude:
- abs(close[t+24] / close[t] - 1).

Within each current-volatility state:
- participation is evaluated using Q1 through Q5.
- primary contrast: Q5 minus Q1.

## 3. Frozen Dataset Split

TRAIN:
- indices 0–11999
- 12,000 rows
- 2024-06-07 09:00 UTC -> 2025-10-20 08:00 UTC

VALIDATION:
- indices 12000–15999
- 4,000 rows
- 2025-10-20 09:00 UTC -> 2026-04-05 00:00 UTC

OOS:
- indices 16000–19999
- 4,000 rows
- 2026-04-05 01:00 UTC -> 2026-09-18 16:00 UTC

The OOS period has been tested and is permanently considered consumed.

## 4. Primary Evidence

TRAIN:
- N = 11,520
- Q5 magnitude = 3.686260%
- Q1 magnitude = 2.952605%
- Q5-Q1 edge = +0.733656 pp
- Spearman rho = +0.113955
- Spearman p < 0.001

VALIDATION:
- N = 4,000
- Q5 magnitude = 3.190334%
- Q1 magnitude = 2.282008%
- Q5-Q1 edge = +0.908325 pp
- Spearman rho = +0.122757
- Spearman p < 0.001

TRUE OOS:
- N = 3,976
- Q5 magnitude = 2.309417%
- Q1 magnitude = 1.766803%
- Q5-Q1 edge = +0.542613 pp
- Spearman rho = +0.225472
- Spearman p < 0.001
- permutation p = 0.000200
- permutations = 5,000
- seed = 20260918

Conclusion:
- TRUE OOS MAGNITUDE EFFECT = PASS.

## 5. Temporal Robustness

Validation was divided chronologically into 10 blocks of 400 observations.

Q5-Q1 magnitude edge:
- B01 +0.951041 pp
- B02 +0.127854 pp
- B03 +1.898729 pp
- B04 +0.492160 pp
- B05 +0.027801 pp
- B06 +0.338184 pp
- B07 +2.248393 pp
- B08 +0.380759 pp
- B09 -0.035291 pp
- B10 -0.069345 pp

- positive blocks = 8/10
- mean = +0.636028 pp
- median = +0.359471 pp
- minimum = -0.069345 pp
- maximum = +2.248393 pp

STATUS: PASS — TEMPORALLY ROBUST

## 6. Incremental Information

After controlling for current volatility:

TRAIN:
- volatility -> magnitude rho = +0.088323
- participation -> magnitude rho = +0.113955
- participation -> volatility-residual magnitude rho = +0.070381

VALIDATION:
- volatility -> magnitude rho = +0.086367
- participation -> magnitude rho = +0.122757
- participation -> volatility-residual magnitude rho = +0.078529

STATUS: PASS — PARTICIPATION ADDS INCREMENTAL INFORMATION

## 7. True Train -> Validation Predictive Test

Model A:
- volatility only

Model B:
- volatility + participation

Validation results:

Model A:
- MAE = 2.077612%
- R² = -0.014563
- rho = +0.086367

Model B:
- MAE = 2.071177%
- R² = -0.004070
- rho = +0.124561

Increment:
- MAE improvement = 0.006434 pp
- R² improvement = +0.010493
- rho improvement = +0.038194

STATUS: PASS — INCREMENTAL PREDICTIVE VALUE

Important limitation:
R² remains negative. VCPM is therefore not an accurate absolute
magnitude forecasting model. Evidence supports incremental ranking /
information value, not precise point forecasting.

## 8. Volatility-State Interaction

TRAIN Q5-Q1 edges by volatility state:
- State 1: -0.143568 pp
- State 2: +0.778695 pp
- State 3: +0.115199 pp
- State 4: +0.439129 pp
- State 5: +2.478823 pp

VALIDATION Q5-Q1 edges:
- State 1: +0.464532 pp
- State 2: +0.465877 pp
- State 3: +0.458365 pp
- State 4: +1.107412 pp
- State 5: +2.045441 pp

State-edge rank correlation:
- Spearman rho = +0.700000
- p = 0.188120

Interpretation:
The strongest effect appears in high-volatility states, but the
monotonic state -> edge relationship is NOT statistically established.

This remains a hypothesis, not a proven law.

## 9. VCPM Interaction Temporal Test

Validation: 10 chronological blocks x 400 observations.

State 5 edge minus State 1 edge:
- B01 +1.715221 pp
- B02 +1.769205 pp
- B03 -0.829536 pp
- B04 -1.242664 pp
- B05 +0.955656 pp
- B06 -2.229260 pp
- B07 +1.894518 pp
- B08 +2.999718 pp
- B09 +1.576347 pp
- B10 +2.015697 pp

- positive blocks = 7/10
- mean = +0.862490 pp
- median = +1.645784 pp

STATUS: PASS — TEMPORALLY STABLE VCPM INTERACTION

Interpretation:
The interaction is supportive evidence, not a deterministic rule.

## 10. Operational Restrictions

VCPM v1 MUST NOT:

1. Generate BUY by itself.
2. Generate SELL by itself.
3. Treat high participation as directional alpha.
4. Automatically trade State 5.
5. Be tuned using consumed OOS data.
6. Reuse SOLUSDT 1H OOS for parameter selection.
7. Change thresholds, quantiles, costs, or definitions merely to improve
   OOS performance.
8. Be used to retroactively select a strategy after observing OOS.
9. Be treated as proof of future profitability.

VCPM v1 MAY:

- provide magnitude context;
- provide risk/opportunity context;
- become an input to a future decision engine;
- be combined with independently validated directional evidence.

## 11. OOS Firewall

The SOLUSDT 1H OOS period is CLOSED.

Any future research involving VCPM must use:
- new data, or
- previously unused TRAIN / VALIDATION data,
- without modifying the frozen VCPM definition.

The consumed OOS results must not be used to select parameters,
thresholds, strategy variants, or hypotheses.

## 12. BTC Firewall

BTC research is CLOSED.

No new BTC testing, tuning, signal search, or feature search is permitted
under this research track.

## 13. Final Status

VCPM v1 is:

FROZEN RESEARCH FEATURE

Evidence supports:
- reproducible magnitude association;
- true OOS magnitude effect;
- temporal robustness;
- incremental information beyond volatility;
- incremental train -> validation predictive value.

Evidence does NOT support:
- directional alpha;
- precise magnitude forecasting;
- universal monotonic volatility-state behavior;
- automatic trading.

Next research phase:
find independently validated directional information.

VCPM remains a context/risk layer only.
