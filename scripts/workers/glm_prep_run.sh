#!/usr/bin/env bash

# glm_prep_run.sh
# Prepare model‑ready regressors and metadata for task GLMs.
# This script does not fit models, estimate betas, or perform inference.

# Required inputs:
# |-------------------+----------+---------------------------------------+------------------------------------|
# | Input             | Source   | Notes                                 | Suffix                             |
# |-------------------+----------+---------------------------------------+------------------------------------|
# | Preprocessed BOLD | fMRIPrep | Path only (used for metadata, timing) | space-T1w_desc-preproc_bold.nii.gz |
# | Events TSV        | BIDS     | Trial structure                       | events.tsv                         |
# | Confounds TSV     | fMRIPrep | Motion, aCompCor, etc.                | desc-confounds_timeseries.tsv      |
# |-------------------+----------+---------------------------------------+------------------------------------|
#
# Optional inputs:
# |---------------------------+--------------------+------------------------------------------|
# | Input                     | Source             | Notes                                    |
# |---------------------------+--------------------+------------------------------------------|
# | Tedana noise components   | Tedana derivatives | Noise Components only, not denoised data |
# | Confound selection config | YAML / JSON        | Optional convenience                     |
# |---------------------------+--------------------+------------------------------------------|
#
# Required metadata (arguments)
# * subject ID
# * run ID
# * TR
# * output directory
#
# Outputs (the contract)
# derivatives/glm_prep/
# └── sub-001/
#     └── run-01/
#         ├── design_matrix.tsv
#         ├── regressors.json
#         ├── timing.json
#         ├── quality_checks.json
#         └── README.md  (optional, but nice)
#
# 1. design_matrix.tsv
#    A fully expanded, time‑aligned regressor matrix ready for GLM fitting.
#
#    Properties:
#    ----
#    rows = timepoints
#    columns = regressors
#    numeric only
#    no NaNs
#    standardized where appropriate
#
#    Typical column groups:
#    ----
#    task regressors (one‑per‑trial if doing beta‑series)
#    nuisance regressors (motion, aCompCor, etc.)
#    tedana noise components (if enabled)
#    high‑pass / drift regressors (if used)
#
# 2. regressors.json
#    Maps column names in design_matrix.tsv to meaning
#
# 3. timing.json
#    TR, number of volumes, high/low/band-pass filter configuration, units of
#    time (BIDS records everything in seconds).
#
# 4. quality_checks.json
#    Minimal by high-value validation output. For example:
#      {
#        "n_regressors": 143,
#        "n_timepoints": 312,
#        "rank_deficient": false,
#        "max_condition_number": 534.1,
#        "empty_regressors": []
#      }

