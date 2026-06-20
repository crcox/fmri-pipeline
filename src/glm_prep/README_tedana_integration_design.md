# GLM Prep: Tedana (ME-ICA) Integration Design

## Overview

This document describes how multi-echo ICA (ME-ICA) outputs from Tedana are
incorporated into the GLM design matrix in `glm_prep`.

The guiding principle of this system is:

> **All nuisance structure is modeled explicitly within a single GLM. No
> variance is removed from the data prior to modeling.**

This design differs from pipelines that perform denoising as a preprocessing
step (e.g., ICA-AROMA, ME-ICA denoised outputs), and instead treats nuisance
signals as regressors that compete with task regressors during model
estimation.

---

## Core Design Principles

### 1. Single Modeling Space

All regressors must be defined in the same data space as the dependent
variable.

- The GLM operates on **optimally combined multi-echo data**
- Regressors must therefore also be expressed in this space
- Echo-specific signals (e.g., per-echo ICA-AROMA components) are not
  compatible with this modeling framework

---

### 2. No Pre-GLM Denoising

We do not perform any irreversible variance removal prior to GLM estimation.

- No projection of data onto a reduced subspace
- No removal of ICA components before modeling
- No orthogonalization of nuisance regressors with respect to task regressors

This ensures that:

- All variance remains visible to the GLM
- Task and nuisance signals are jointly estimated
- Variance sharing and ambiguity are preserved and interpretable

---

### 3. Explicit Nuisance Modeling

All nuisance structure is represented as regressors in the design matrix.

For Tedana:

- Rejected ME-ICA components are treated as nuisance regressors
- These are included directly in the GLM without modification

---

## Tedana Policy (Current Implementation)

At present, we expose a single, minimal policy for Tedana integration.

### Configuration

    tedana:
      include=True
      selection:
        strategy: classification
        value: rejected
        

### Behavior

- mode: rejected
  - Include all rejected ME-ICA components as regressors
  - No subsetting or filtering is performed
  - No orthogonalization is applied

- mode: none
  - Do not include any ME-ICA-derived regressors

---

## Rationale

### Why include all rejected components?

- ME-ICA provides a classification of components into:
  - accepted (BOLD-like)
  - rejected (non-BOLD-like)

- This classification is grounded in TE-dependence and is the most principled
  separation available

- Including all rejected components:
  - preserves completeness of the nuisance model
  - avoids arbitrary truncation
  - aligns with the “model everything in GLM” philosophy

---

### Why not subset ICA components?

Unlike PCA (e.g., aCompCor), ICA components:

- are **not ordered**
- are **not orthogonal**
- do **not admit a natural truncation criterion**

Therefore:

- Selecting the “top N components” is not theoretically grounded
- Ordering by variance, rho, or other metrics is heuristic
- Truncation introduces arbitrary modeling decisions

For this reason:

> **ICA component subsetting is intentionally not implemented at this time.**

---

### Why not orthogonalize?

Orthogonalization modifies nuisance regressors before the GLM sees them.

This:

- removes shared variance between task and nuisance regressors
- imposes a constraint not present in the data
- reduces transparency of variance attribution

This violates the core design principle:

> All variance relationships should be visible to the GLM and resolved through
> model estimation.

---

## Comparison to Alternative Pipelines

### Pre-denoising pipelines (e.g., ICA-AROMA, MEPrep)

Typical workflow:

    data → denoising → cleaned data → GLM

In contrast, our workflow is:

    data → construct regressors → GLM (joint estimation)

Key differences:

| Property                    | Pre-denoising pipelines  | glm_prep            |
|-----------------------------+--------------------------+---------------------|
| Variance removal            | before GLM               | within GLM          |
| Reversibility               | irreversible             | fully modeled       |
| Interpretability            | reduced                  | high                |
| Treatment of ICA components | removed or projected out | explicit regressors |

---

## Future Directions

The following areas are intentionally left as future work:

### 1. ICA Component Subsetting

Possible strategies (not yet implemented):

- Ordering by variance explained
- Ordering by tedana metrics (e.g., rho, kappa)
- Hybrid ranking criteria

Any subsetting method must:

- be deterministic
- have a clear interpretation
- be validated empirically

---

### 2. Regularization and Model Stability

Including all ICA components may introduce:

- collinearity
- increased model complexity

Future work may explore:

- regularized GLM variants
- diagnostics for overfitting
- principled pruning strategies

---

### 3. Alternative Integration Strategies

Potential extensions:

- ICA components as priors or constraints
- hybrid pipelines combining denoising and regression
- dataset-dependent policy adaptation

---

## Summary

This design adopts a strict and principled stance:

- No pre-modeling denoising
- All nuisance structure expressed as regressors
- ME-ICA components included in full, without modification

Where the literature does not provide a clear or principled method (e.g., ICA
component subsetting), we:

> **defer implementation rather than encode ambiguous behavior**

This ensures clarity, reproducibility, and extensibility of the pipeline.
