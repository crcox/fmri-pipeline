from pathlib import Path
from nilearn.glm.first_level import FirstLevelModel

from glm_prep.domain import RunKey
from glm_prep.figures import design_matrix_to_dataframe
from glm_prep.io import load_design_matrix

design = load_design_matrix(Path("derivatives/glm_prep/task-baseline-v1/sub-001/design"), RunKey(run=1, subject=1))

design_df = design_matrix_to_dataframe(design_matrix)

glm = FirstLevelModel(
    t_r=1.5,  # or timing_metadata.tr
    noise_model="ar1",
    standardize=False,
)

glm.fit(
    run.bold_data.path,
    design_matrices=design_df,
)
