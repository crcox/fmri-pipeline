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
### run_fmriprep_all.sh
### ----------------------------
# Runs fMRIPrep for all subjects in a BIDS dataset.
#
# If derivatives/fmriprep/sub-${SUBJECT}.html exists, the assumption is that
# the subject has already been processed and should be skipped.


usage() {
    echo "Usage: $0"
}

info_banner() {
    echo "======================================"
    echo "Starting fMRIPrep batch"
    echo "Timestamp: ${TIMESTAMP}"
    echo "Subjects:  ${SUBJECTS[*]}"
    echo "======================================"
}

subject_banner() {
    echo
    echo "--------------------------------------"
    echo "${ICON_START} Starting subject sub-${SUBJECT}"
    echo "--------------------------------------"
}

success_banner() {
    echo
    echo "======================================"
    echo "${ICON_DONE} Batch completed successfully"
    echo "Log directory: ${LOG_ROOT}"
    echo "======================================"
}

find_subjects() {
    local bids_root=$1
    find "${bids_root}" -maxdepth 1 -type d -name 'sub-*' -printf '%f\n' |
        sed 's/^sub-//' |
        sort -n
}

validate_subject_script() {
    if [[ ! -x "${SUBJECT_SCRIPT}" ]]; then
        echo "${ICON_ERROR} Could not execute ${SUBJECT_SCRIPT} for processing a single subject with fMRIPrep."
        echo "    It is either missing or you lack execute permissions for the script."
        die_missing_inputs "Subject script not found or not executable: ${SUBJECT_SCRIPT}"
    fi
}

run_fmriprep_subject() {
    local subject="$1"

    "${SUBJECT_SCRIPT}" \
        "${BIDS_ROOT}" \
        "${DERIV_ROOT}" \
        "${WORK_ROOT}" \
        "${FS_LICENSE_DIR}" \
        "${IMAGE}" \
        "$subject"
}

### ----------------------------
### Ensure correct usage (no arguments)
### ----------------------------
if [[ $# -ne 0 ]]; then
    usage >&2
    die_usage
fi

### ----------------------------
### Configuration
### ----------------------------
SUBJECT_SCRIPT="${SCRIPTS_ROOT}/workers/fmriprep_subject.sh"
ROOT_DIR="/data/chriscox/MRI/semantic-multitask/York"
BIDS_ROOT="${ROOT_DIR}/bids"
DERIV_ROOT="${ROOT_DIR}/derivatives/fmriprep"
WORK_ROOT="${ROOT_DIR}/work/fmriprep"
FS_LICENSE_DIR="${ROOT_DIR}/license"
IMAGE="docker.io/nipreps/fmriprep:25.2.5"

LOG_ROOT="./logs"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

mkdir -p "${LOG_ROOT}"

validate_subject_script

mapfile -t SUBJECTS < <(find_subjects "${BIDS_ROOT}")

### ----------------------------
### Batch loop
### ----------------------------
info_banner

for SUBJECT in "${SUBJECTS[@]}"; do
    subject_banner

    LOG_FILE="${LOG_ROOT}/sub-${SUBJECT}_${TIMESTAMP}.log"

    # Run subject with logging
    if run_fmriprep_subject "${SUBJECT}" 2>&1 | tee "${LOG_FILE}"; then
        echo "${ICON_SUCCESS} sub-${SUBJECT} completed successfully"
    else
        status=${PIPESTATUS[0]}
        case "$status" in
            2)
                echo "${ICON_ERROR} Usage error while running fmriprep."
                echo "  This may indicate a bug in the orchestrator script."
                echo "  See log: ${LOG_FILE}"
                die_usage "Aborting batch due to orchestrator usage error"
                ;;
            3)
                echo "${ICON_ERROR} Missing input error while running fmriprep for sub-${SUBJECT}"
                echo "  See log: ${LOG_FILE}"
                die_missing_inputs "Aborting batch because inputs are missing."
                ;;
            4)
                echo "${ICON_FATAL} Fatal infrastructure failure during fmriprep execution."
                echo "  See log: ${LOG_FILE}"
                die_external "Aborting batch due to an unrecoverable external execution failure."
                ;;
            5)
                echo "${ICON_SKIP} sub-${SUBJECT} has already been successfully processed by fmriprep. Skipping."
                continue
                ;;
            130)
                echo "${ICON_ERROR} Interrupted by SIGINT"
                exit 130
                ;;
            143)
                echo "${ICON_ERROR} Terminated by SIGTERM"
                exit 143
                ;;
            *)
                echo "${ICON_ERROR} Unknown failure (exit status $status)"
                echo "  See log: ${LOG_FILE}"
                exit 1
                ;;
        esac
    fi
done

success_banner
