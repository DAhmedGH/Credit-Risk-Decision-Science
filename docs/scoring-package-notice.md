# Dataset-derived scoring artifact notice

This package contains a fitted benchmark model derived from:

Yeh, I. (2009). Default of Credit Card Clients [Dataset]. UCI Machine Learning
Repository. Creator: I-Cheng Yeh. DOI: https://doi.org/10.24432/C55S3H.
Source: https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients.
Dataset license: Creative Commons Attribution 4.0 International (CC BY 4.0):
https://creativecommons.org/licenses/by/4.0/.
Legal terms and warranty disclaimer:
https://creativecommons.org/licenses/by/4.0/legalcode.en.

The dataset was normalized and used to fit financial preprocessing and a
100-tree XGBoost model on development accounts. Policies were frozen separately
on policy validation. This distribution copies the accepted fitted pipeline
unchanged, copies its financial schema and projects only scenario/policy
definitions from the original policy evidence. No customer records, workbooks,
training labels or SHAP samples are included. New delivery metadata is separate
from original scientific acceptance. No endorsement by UCI or the creator is
implied. The artifact is supplied as-is for educational benchmark use; it does
not establish fitness for lending, causal effects, fairness or current populations.
Retain this attribution and license link when redistributing dataset-derived
material, and identify subsequent modifications.

Third-party libraries are not bundled. Install the pinned publication environment
separately. NumPy, pandas, SciPy, scikit-learn, joblib and threadpoolctl have BSD
licenses; XGBoost and PyArrow have Apache 2.0 licenses. Their installed distributions
retain their own notices and license texts. This dataset notice does not relicense
third-party software or establish a repository-wide software license.

Joblib serialization can execute code. A checksum verifies expected bytes, not
the safety of arbitrary models. Deserialize only the explicitly trusted package
distributed with matching publication code and verification metadata.
