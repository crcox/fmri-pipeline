#!/usr/bin/env bash
set -euo pipefail

### ----------------------------
### Source lib/common.sh
### ----------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMMON_LIB="${SCRIPTS_ROOT}/lib/common.sh"
if [[ ! -r "${COMMON_LIB}" ]]; then
  echo "ERROR: Cannot read common library: ${COMMON_LIB}" >&2
  exit 2
fi
# shellcheck source=lib/common.sh
source "${COMMON_LIB}"


### ----------------------------
# run_fmriprep_subject.sh
### ----------------------------
# Runs fMRIPrep for a single subject in a BIDS dataset.
#
# Exit codes:
#   0: Success
#   2: Usage error
#   3: Missing inputs
#   4: External execution failure
#   5: Skipped intentionally
#   130: Interrupted by SIGINT
#   143: Terminated by SIGTERM

CLEANUP_MODE="${CLEANUP_MODE:-auto}"
DO_CLEANUP="${DO_CLEANUP:-false}"
DRY_RUN="${DRY_RUN:-false}"
DEBUG="${DEBUG:-false}"
IGNORE_COMPLETION="${IGNORE_COMPLETION:-false}"


usage() {
  echo "Usage: $0 <bids-root> <derivatives-root> <work-root> <fs-license-dir> <fmriprep-image> <participant-label>"
  echo "Example:"
  echo "$0 \\"
  echo "    /path/to/bids \\"
  echo "    /path/to/derivatives \\"
  echo "    /path/to/work \\"
  echo "    /path/to/fs-license-dir \\"
  echo "    docker.io/nipreps/fmriprep:25.2.5 \\"
  echo "    001"
}

info_banner() {
    echo "======================================"
    echo "Running fMRIPrep"
    echo "Subject: sub-${SUBJECT}"
    echo "BIDS:    ${BIDS_ROOT}"
    echo "Derivs:  ${DERIV_ROOT}"
    echo "Work:    ${WORK_DIR}"
    echo "======================================"
}

# Cleanup function is invoked via exit trap
# shellcheck disable=SC2317
cleanup() {
    if [[ -d "${WORK_DIR}" && ${DO_CLEANUP} == true ]]; then
        echo "Cleaning up work directory for sub-${SUBJECT}" >&2
        rm -rf "${WORK_DIR}"
    else
        echo "Preserving ${WORK_DIR} for debugging" >&2
    fi
}

debug() {
    if [[ "${DEBUG}" == true ]]; then
        echo "[DEBUG] $*" >&2
    fi
}

validate_complete() {
    if [[ -f "${DERIV_ROOT}/sub-${SUBJECT}.html" ]]; then
        if [[ "${IGNORE_COMPLETION}" == "true" ]]; then
            echo "[IGNORE_COMPLETION] sub-${SUBJECT}.html exists, but fmriprep will run."
        else
            echo "sub-${SUBJECT} already processed. Skipping." >&2
            exit 5
        fi
    fi
}

validate_bids() {
    if [[ ! -d "${BIDS_ROOT}/sub-${SUBJECT}" ]]; then
        die_missing_inputs "ERROR: Subject 'sub-${SUBJECT}' not found in '${BIDS_ROOT}'."
    fi
}

validate_license() {
    if [[ ! -f "${FS_LICENSE_DIR}/license.txt" ]]; then
        die_missing_inputs  "ERROR: FreeSurfer license not found at '${FS_LICENSE_DIR}/license.txt'"
    fi
}

validate_podman() {
    command -v podman >/dev/null 2>&1 || {
        die_missing_inputs "ERROR: podman not found in PATH"
    }
}

run_fmriprep() {
    debug "Constructing podman command"
    local fs_subj_dir_container="/out/sourcedata/freesurfer"
    debug "fs_subj_dir_container=${fs_subj_dir_container}"
    local cmd=(
        podman run --rm
        -v "${BIDS_ROOT}:/data:ro,Z"
        -v "${DERIV_ROOT}:/out:Z"
        -v "${WORK_DIR}:/work:Z"
        -v "${FS_LICENSE_DIR}:/fs:ro,Z"
        "${IMAGE}"
        /data /out participant
        --participant-label "${SUBJECT}"
        --fs-license-file /fs/license.txt
        --fs-subjects-dir "${fs_subj_dir_container}"
        --dummy-scans 6
        --output-spaces T1w MNI152NLin2009cAsym
        --me-output-echos
        -w /work
    )

    if [[ "${DRY_RUN}" == true ]]; then
        echo "[DRY-RUN] ${cmd[*]}"
        return 0
    fi

    debug "Executing podman command"
    "${cmd[@]}"
}

trap cleanup EXIT
trap 'DO_CLEANUP=true; exit 130' SIGINT
trap 'DO_CLEANUP=true; exit 143' SIGTERM

### ----------------------------
### Parse arguments
### ----------------------------
if [[ $# -ne 6 ]]; then
    usage >&2
    exit 2
fi

BIDS_ROOT="$1"
DERIV_ROOT="$2"
WORK_ROOT="$3"
FS_LICENSE_DIR="$4"
IMAGE="$5"
SUBJECT="$6"

debug "Using image ${IMAGE}"

### ----------------------------
### Derive paths and create output directories
### ----------------------------
WORK_DIR="${WORK_ROOT}/sub-${SUBJECT}"
debug "Derived WORK_DIR=${WORK_DIR}"
mkdir -p "${WORK_DIR}" "${DERIV_ROOT}"

### ----------------------------
### Validate inputs
### ----------------------------
validate_complete
validate_bids
validate_license
validate_podman

info_banner

### ----------------------------
### Run fMRIPrep
### ----------------------------
if run_fmriprep; then
    DO_CLEANUP=true
    exit 0
else
    echo "Podman fmriprep failed for sub-${SUBJECT}" >&2
    exit 4
fi
