# Frozen protocol and limitations

The authoritative pre-evaluation policy is ml/config/policy.json. Its hash is copied to the ingestion report, evaluation selection and registry metadata. Do not retune based on holdout.

Validation uses two expanding folds: 2022-07-01–2023-07-01 and 2023-07-01–2024-07-01. Estimator weights and standardization fit only pre-fold rows. Baseline state updates after each whole date, allowing known prior outcomes during the fold. Every fixture on a date receives features before any result on that date is applied. Final holdout is 2024-07-01–2025-07-01. Minimum league history is 40 accepted games.

League outcome prior is Dirichlet [4.5,2.5,3]. Elo uses K=20, 60-point home advantage, Davidson draw parameter .65 and .75 season retention; unseen teams start 1500. Poisson uses last 20 home/away games, eight pseudo-games of shrinkage, last 380 league results with 30 pseudo-games and fixed preseason means 1.5/1.2. Goal rates are clipped [.15,5]. 1X2 grid is normalized at 0..20; top-score probabilities retain raw mass and tail mass is reported. These are model expected goals, not provider xG.

Logistic uses training-only standardization and multinomial softmax + L2 C=1. XGBoost uses depth 2, 100 CPU rounds, eta .05, one thread and fixed seed. No hyperparameter search or post-holdout calibration is performed.

Choose the best baseline and challenger by pooled validation Log Loss. Challenger acceptance requires every league to have n>=300, improvement >=.005, Brier regression <=.002, ECE regression <=.02, wins in both folds, and paired date-cluster bootstrap delta upper bound below zero. Manual promotion remains mandatory even if all gates pass.

Brier is the sum of three squared errors, no division by three. Accuracy is secondary. Top-label ECE uses ten equal-width bins. Reliability is also recorded per class. 95% percentile bootstrap CIs resample match dates (500 fixed-seed repetitions). Correlation across seasons/teams may still make these intervals optimistic. No claim of statistically significant superiority on final holdout is made merely from point estimates.

The refitted deployment artifact includes data up to before 2026-07-01. Its metadata clearly separates that cutoff from the estimator cutoffs used for evaluation. Reported test metrics are not computed by scoring this deployment refit on its training data.

Retrospective source can contain later corrections and undetected bad dates. Timezones and cross-provider mapping remain unverified. Seasons require at least 95% usable result coverage; missing La Liga 2024/25 games introduce possible sample bias. The 66 misdated EPL games are quarantined and the remaining 314 games of that season withheld. No correction has been applied. Newer partial seasons are not accepted for training. Full enrichment files are excluded from labels to avoid double counting and target-match event leakage.
