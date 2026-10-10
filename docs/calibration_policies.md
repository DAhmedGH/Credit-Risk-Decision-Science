# Calibration and simulated policies

This workflow assesses probability quality and compares explicit hypothetical
accept/abstain decisions. It estimates neither actual profit nor the causal
effect of changing lending. The observed label concerns existing accounts, not
new-applicant approval or rejection outcomes.

## Probability fitting and selection

The development-selected base model remains fixed. Sigmoid and isotonic mappings
fit 4,500 separate calibration rows using the pinned scikit-learn fixed-estimator
API. The raw mapping is identity. Selection uses log loss on 3,000 separate
policy-validation rows, with an absolute 0.005 simplicity tolerance. Mappings
within 0.005 of the minimum loss are ordered raw, sigmoid, then isotonic.

| Probability mapping | Policy-validation AP | Log loss | Brier score | Selection |
| --- | ---: | ---: | ---: | --- |
| Raw | 0.54858 | 0.43299 | 0.13617 | Retained |
| Sigmoid | 0.54858 | 0.43623 | 0.13708 | Not retained |
| Isotonic | 0.52875 | 0.45599 | 0.13671 | Not retained |

Reliability uses ten fixed equal-width bins on [0, 1], with probability 1 in the
last bin. Counts below 100 are marked sparse, and empty-bin means/rates remain
undefined. Log loss and Brier score measure overall probability quality, not
calibration alone; reliability bins provide the calibration diagnostic.

Raw minimized log loss and won the declared rule. This does not show that
calibration never helps or identify a globally best mapping. The
[exact calibration table](../reports/phase4_runs/9ca62eca2665438c9c97b4889413acfa/calibration_comparison.csv)
and [reliability bins](../reports/phase4_runs/9ca62eca2665438c9c97b4889413acfa/reliability_bins.csv)
retain the measured evidence. A full-data base refit would be a new bundle and
could not inherit the old calibrator or held-out evidence unqualified.

## Utility contract

For probability `p`, nondefault gain `G`, default loss `L` and accepted-account
processing cost `C`, the dimensionless payoff model is:

```text
EU(accept) = (1 - p) * G - p * L - C
EU(abstain) = 0
analytic cutoff = 0 if G <= C; otherwise (G - C) / (G + L)
```

Gain, loss and cost must be finite nonnegative values, with finite `G + L > 0`.
Gain/loss are net of their respective outcome costs; the separate processing cost
is charged once per accepted account. When `G <= C`, analytic acceptance is empty.
The label-based benchmark is `sum(a_i * ((1-y_i)*G - y_i*L - C))`, where `a_i`
is the frozen acceptance decision. Per-customer utility includes abstentions.

The design's nominal 1,000-unit exposure motivates the illustrative payoffs.
The delivered `Scenario` stores `G`, `L` and `C`; it has no customer-level
principal/exposure input and does not scale the payoff by a bill or credit limit.

Base values are `G=50`, `L=500`, `C=0`; the analytic cutoff is `50/550`, about
0.090909. Acceptance requires `p < cutoff`; boundary ties abstain. Label-based
benchmark utility assigns gain/loss using observed outcomes and assumes those
outcomes remain unchanged under hypothetical allocation. The exposure is
standardized and synthetic, not a customer's historical bill or a new loan.

## Frozen policy definitions

| Policy | Definition | Selection boundary |
| --- | --- | --- |
| Accept all / abstain all | Explicit all/none actions | Fixed references |
| Low-risk fractions 25% / 50% / 75% | First excluded validation order statistic; ties abstain | Numerical cutoffs frozen on policy validation |
| Probability 0.5 | Strict cutoff at 0.5 | Fixed reference, not an optimized lending rule |
| Analytic | Strict cutoff from the utility equation | Declared scenario values |
| Empirical | Grid 0 through 1 in steps of 0.005, plus explicit all/none | Maximum policy-validation benchmark utility; ties prefer fewer acceptances |

Fraction cutoffs use the first excluded order statistic at position
`floor(fraction * n_validation)`. Strict inequality accepts at most that many
validation records; boundary ties may reduce the achieved share.

At equal utility and acceptance count, empirical selection uses the deterministic
order none, increasing cutoff, all. Zero-acceptance winners are explicit
abstain-all policies. Fraction cutoffs remain scalar values on the final test;
they do not reselect test percentiles or guarantee the same acceptance share.

The base fraction cutoffs are 0.08965142071247101, 0.1460030972957611 and
0.2732357978820801. Base empirical cutoff is 0.085. The frozen table covers
eight policies across the base scenario, nine gain/loss grid cells (`G` 25/50/100,
`L` 250/500/750, `C=0`) and the secondary `G=50/L=500/C=5` scenario: 88 rows.
Base and the identically valued grid cell retain distinct scenario IDs.

## Final interpretation under base payoffs

| Frozen policy | Accepted test accounts | Accepted default rate | Benchmark units/customer |
| --- | ---: | ---: | ---: |
| Empirical, cutoff 0.085 | 1,028 / 4,500 (22.844%) | 55 / 1,028 (5.350%) | 4.70 [2.9012, 6.3711] |
| Analytic, cutoff 50/550 | 1,160 / 4,500 (25.778%) | 64 / 1,160 (5.517%) | 5.0667 |
| Abstain all | 0 / 4,500 | N/A | 0 |
| Accept all | 4,500 / 4,500 | 22.133% | −71.7333 |

The empirical policy produces 21,150 total benchmark units; predicted EU is
3.6581 units per customer. Empirical-minus-analytic utility is −0.3667 with
paired interval [−0.9862, 0.4165]. These reported final-test comparisons do not
choose a replacement policy. Under `G=25/L=750/C=0`, validation-selected
empirical abstain-all remains published, with accepted default rate N/A.

[All frozen policies](../reports/phase5/policies.csv),
[sensitivity and uncertainty](../reports/results.md#payoff-sensitivity-fixed-validation-selected-empirical-policies)
and [the selection-stage report](../reports/phase4.md) retain full definitions
and measurements. In high-risk detection tables, abstention is the positive
action; default `1` remains the positive outcome. Undefined accepted default
rates stay N/A rather than zero.
