# glm\_prep

glm\_prep transforms heterogeneous inputs into a standardized, validated GLM
design representation.

## Design

The package does not reason about filesystem structure. It accepts typed path inputs.

### Invariant 1: Stateless execution

Identical inputs + policy must yield identical outputs.

* No randomness
* No hidden state
* No time-dependent behavior

### Invariant 2: Single source of truth for configuration

All modeling assumptions come from the policy object.

No implicit defaults buried in code.

### Invariant 3: Typed boundaries everywhere

At every layer:

| Layer            | Types                  |
|------------------|------------------------|
| Raw files        | I/O                    |
| Parsed data      | Typed input objects    |
| Policy           | Typed policy objects   |
| Core computation | Pure functions         |
| Outputs          | Typed artifact objects |
| Serialization    | I/O                    |

### Invariant 4: Artifact completeness

Each artifact object must be:

* self-consistent
* internally validated
* independent of external context

### Invariant 5: No path logic inside core code

Paths only exist in CLI or I/O layer.

Never inside design\_matrix logic, policy logic, etc.

## Layers

We separate the system into three (plus one) layers:

### Layer 1: Input and policy

* config.py
* inputs.py
* parsing.py
* validation.py

### Layer 2: Transformation (core logic)

* confounds.py
* events.py
* tedana.py
* drift.py
* design\_matrix.py

### Layer 3: Output

* artifacts.py
* quality.py
* io.py

### Orchestration layer

* cli.py
* orchestration.py

## Modules

### cli.py (entry point only)

#### Responsibility

* Parse CLI args
* Call orchestration
* Handle exit codes

#### Should NOT

* Do any logic
* Touch pandas/numpy

### config.py (policy system)

#### Responsibility

Parse YAML into typed dataclasses

#### Defines

```python
GLMPrepPolicy
MotionPolicy
ACompCorPolicy
TedanaPolicy
DriftPolicy
...
```

#### Key invariant

No raw dicts beyond this point

### inputs.py

Typed input domain objects

#### Responsibility

Represent validated data in structured form.

#### Defines

```python
BoldRun
ConfoundsTable
EventsTable
TedanaComponents
```

These contain:

* arrays / DataFrames
* metadata (TR, n\_volumes, etc.)

### parsing.py

I/O into raw structures

#### Responsibility

Read files from disk
Return unvalidated data

Returns:

pandas DataFrames
numpy arrays

No typing yet.

### validation.py

Validate inputs

#### Responsibility

Ensure all inputs are consistent

#### Checks

timepoints match
TR is consistent
no NaNs (or handled)
required columns exist

#### Output

constructs inputs.py objects

### confounds.py

Some text

#### Responsibility

Select and transform nuisance regressors from fMRIPrep.

#### Uses

ConfoundsTable
MotionPolicy
ACompCorPolicy

#### Produces

DataFrame / ndarray of confound regressors
list of regressor names

### events.py

Some text

#### Responsibility

Convert events.tsv into task regressors.

#### Handles

trial-wise regressors
HRF convolution (important: this ties to your policy decision!)

#### Produces

task regressor matrix
metadata about trials

### tedana.py

Some text

#### Responsibility

Extract rejected components
optionally orthogonalize

#### Input

TedanaComponents
TedanaPolicy

#### Output

noise component regressors

### drift.py (optional but recommended)

Some text

#### Responsibility

Generate low-frequency drift regressors.

#### Input

number of timepoints
TR
drift policy

#### Output

cosine basis matrix

### design\_matrix.py (central builder)

Some text

#### Responsibility

Combine all regressors into a single matrix.

#### Inputs

* task regressors
* confounds
* tedana
* drift

#### Output

```python
DesignMatrix
```

### artifacts.py

Output contracts

#### Defines

```python
@dataclass(frozen=True)
class DesignMatrix:
    matrix: np.ndarray
    column\_names: List[str]

@dataclass(frozen=True)
class RegressorMetadata:
    mapping: Dict[str, Dict]

@dataclass(frozen=True)
class TimingMetadata:
    tr: float
    n\_volumes: int

    high\_pass\_cutoff: float
    ...

@dataclass(frozen=True)
class QualityReport:
    n\_regressors: int
    rank\_deficient: bool
    ...

```

### quality.py

Some text

#### Responsibility

Compute QC metrics.

#### Input

DesignMatrix (at minimum)

#### Output

QualityReport

### io.py

Some text

#### Responsibility

Serialize artifacts to disk.

#### Contains

```python
write\_design_matrix(...)
write\_json(...)
```

#### Important

* no domain logic
* strictly serialization

### orchestration.py (the heart)

#### Defines

```python
build_artifacts(
    bold\_path,
    events\_path,
    confounds\_path,
    tedana\_path,
    policy\_path,
    out\_dir
):
```

#### Flow

1. Parse files (parsing.py)
2. Validate into typed inputs (validation.py)
3. Load policy (config.py)
4. Generate regressors
5. Build design matrix (design\_matrix.py)
6. Build metadata (artifacts.py)
7. Run QC (quality.py)
8. Write outputs (io.py)

## Dataclasses

Some text

### Data sources

* BoldRun
* ConfoundsTable
* EventsTable
* TedanaComponents

### Configuration

* GLMPrepPolicy
  * MotionPolicy
  * ACompCorPolicy
  * TedanaPolicy
  * etc.

### Outputs

* DesignMatrix
* RegressorMetadata
* TimingMetadata
* QualityReport
