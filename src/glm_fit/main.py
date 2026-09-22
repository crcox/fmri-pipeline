from collections import defaultdict
from pathlib import Path

import nibabel
import numpy as np
from nilearn.glm.first_level import FirstLevelModel

from glm_prep.artifacts import DesignMatrix, RegressorSource
from glm_prep.domain import RunKey
from glm_prep.figures import design_matrix_to_dataframe
from glm_prep.io import load_design_matrix


def columns_by_source(design: DesignMatrix) -> dict[RegressorSource, list[str]]:
    result: dict[RegressorSource, list[str]] = defaultdict(list)

    for info in design.regressors:
        result[info.source].append(info.name)

    return result


glm_prep_root = Path("derivatives/glm_prep/task-baseline-v1")
run = RunKey(run=1, subject=1)
design = load_design_matrix(glm_prep_root, run)

cols = columns_by_source(design)

design_df = design_matrix_to_dataframe(design, standardized=True)

mask_path = Path(
    "derivatives/fmriprep/sub-001/func/sub-001_task-semjudge_acq-domain_run-01_space-T1w_desc-brain_mask.nii.gz"
)

mask = nibabel.load(mask_path)

glm = FirstLevelModel(
    noise_model="ar1",
    signal_scaling=0,  # by time
    mask_img=mask,
)

{k: len(v) for k, v in cols.items()}

glm.fit(
    design.provenance.bold_data_file,
    design_matrices=design_df[
        cols[RegressorSource.STIMULUS]
        + cols[RegressorSource.DRIFT]
        + cols[RegressorSource.MOTION]
        + cols[RegressorSource.TEDANA]
    ],
)

beta = glm.compute_contrast(
    "bear",
    output_type="effect_size",
)

x = beta.get_fdata()

print(np.count_nonzero(x) / float(x.size))
print(np.nanmin(x))
print(np.nanmax(x))
print(
    np.percentile(x[np.nonzero(x)], [0, 0.01, 0.1, 1, 5, 50, 95, 99, 99.9, 99.99, 100])
)

np.sum(x <= -100)
np.sum(x >= 100)

mask = glm.masker_.mask_img_

np.linalg.cond(design.matrix)
np.linalg.cond(design.standardized_matrix)

condition_by_source = {}
for source in RegressorSource:
    z = [info.source != source for info in design.regressors]
    cond = condition_by_source[source.value] = np.linalg.cond(
        design.standardized_matrix[:, z]
    )
    print(f"{source:s}: {cond:f}")

print(condition_by_source)


z = [info.source != RegressorSource.DRIFT for info in design.regressors]
np.linalg.cond(design.matrix[:, z])

z = [info.source != RegressorSource.TEDANA for info in design.regressors]
np.linalg.cond(design.matrix[:, z])

z = [info.source != RegressorSource.ACOMPCOR for info in design.regressors]
np.linalg.cond(design.matrix[:, z])

z = [info.source != RegressorSource.MOTION for info in design.regressors]
np.linalg.cond(design.matrix[:, z])

z = [info.source != RegressorSource.STIMULUS for info in design.regressors]
np.linalg.cond(design.matrix[:, z])

design.regressors[0]


corr = np.corrcoef(design.matrix.T)

np.max(np.abs(corr - np.eye(corr.shape[0])))

s = np.linalg.svd(
    design.matrix,
    compute_uv=False,
)

print(s[:10])
print(s[-80:])


corr = np.corrcoef(design.matrix.T)

# Ignore diagonal
np.fill_diagonal(corr, 0)

ix = np.unravel_index(
    np.argmax(np.abs(corr)),
    corr.shape,
)

ix

design.regressors[ix[0]].name
design.regressors[ix[1]].name
corr[ix]


mask = glm.masker_.mask_img_.get_fdata()

print("beta:", np.count_nonzero(x))
print("mask:", np.count_nonzero(mask))


for info in design.regressors:
    if info.source == RegressorSource.MOTION:
        print(
            info.name,
            info.diagnostics.std,
        )
