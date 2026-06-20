#!/usr/bin/env bash
set -euo pipefail

### ----------------------------
### Source lib/common.sh
### ----------------------------
ORCHESTRATORS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_ROOT="$(cd "${ORCHESTRATORS_DIR}/.." && pwd)"
WORKERS_DIR="${SCRIPTS_ROOT}/workers"
COMMON_LIB="${SCRIPTS_ROOT}/lib/common.sh"
if [[ ! -r "${COMMON_LIB}" ]]; then
  echo "ERROR: Cannot read common library: ${COMMON_LIB}" >&2
  exit 2
fi
# shellcheck source=lib/common.sh
source "${COMMON_LIB}"

### ----------------------------
### run_tedana_all.sh
### ----------------------------
# Orchestrates tedana across subjects and runs
#
# Tedana is being used to generate ICA components. This pipeline does not
# modify its input files nor does it create a "denoised" dataset. It only
# generates files that map voxels to ICA components for each run for each subject.

usage() {
    echo "Usage: $0"
}

info_banner() {
    echo "======================================"
    echo "Starting tedana batch"
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

run_banner() {
    echo
    echo "--------------------------------------"
    echo "  ${ICON_START} Starting run run-${RUN}"
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
    local fmriprep_derivs_root=$1
    find "${fmriprep_derivs_root}" -maxdepth 1 -type d -name 'sub-*' -printf '%f\n' |
        sed 's/^sub-//' |
        sort -n
}

validate_tedana_run_script() {
    if [[ ! -x "${TEDANA_RUN_SCRIPT}" ]]; then
        echo "ERROR: Run script not found or not executable: ${TEDANA_RUN_SCRIPT}"
        exit 3
    fi
}

tedana_run() {
    local subject="$1"
    local run="$2"

    "${TEDANA_RUN_SCRIPT}" \
        "${FMRIPREP_ROOT}" \
        "${TEDANA_ROOT}" \
        "${WORK_ROOT}" \
        "${TEDANA_IMAGE}" \
        "$subject" \
        "$run" \
        "$NUM_ECHOES"
}

### ----------------------------
### Ensure correct usage (no arguments)
### ----------------------------
if [[ $# -ne 0 ]]; then
    usage >&2
    exit 2
fi

### ----------------------------
### Configuration
### ----------------------------
RUNS=({01..08})
NUM_ECHOES=3

ROOT_DIR="/data/chriscox/MRI/semantic-multitask/York"
FMRIPREP_ROOT="${ROOT_DIR}/derivatives/fmriprep"
TEDANA_ROOT="${ROOT_DIR}/derivatives/tedana"
WORK_ROOT="${ROOT_DIR}/work/tedana"

TEDANA_RUN_SCRIPT="${WORKERS_DIR}/tedana_run.sh"
TEDANA_IMAGE="local/tedana:26.0.3"

LOG_ROOT="./logs/tedana"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

mkdir -p "${LOG_ROOT}"

validate_tedana_run_script

mapfile -t SUBJECTS < <(find_subjects "${FMRIPREP_ROOT}")

### ----------------------------
### Batch loop
### ----------------------------
info_banner

for SUBJECT in "${SUBJECTS[@]}"; do
    subject_banner

    for RUN in "${RUNS[@]}"; do
        run_banner
        LOG_FILE="${LOG_ROOT}/sub-${SUBJECT}_run-${RUN}_${TIMESTAMP}.log"

        # Run subject with logging
        if tedana_run "${SUBJECT}" "${RUN}" 2>&1 | tee "${LOG_FILE}"; then
            echo "${ICON_SUCCESS} sub-${SUBJECT} run-${RUN} completed successfully"
        else
            status=${PIPESTATUS[0]}
            case "$status" in
                2)
                    echo "${ICON_ERROR}  Usage error while running tedana."
                    echo "  This may indicate a bug in the orchestrator script."
                    echo "  See log: ${LOG_FILE}"
                    die_usage "Aborting batch due to orchestrator usage error"
                    ;;
                3)
                    echo "${ICON_ERROR}  Missing input error while running tedana for sub-${SUBJECT} run-${RUN}"
                    echo "  See log: ${LOG_FILE}"
                    die_missing_inputs "Aborting batch because inputs are missing."
                    ;;
                4)
                    echo "${ICON_FATAL}  Fatal infrastructure failure during tedana execution."
                    echo "  See log: ${LOG_FILE}"
                    die_external "Aborting batch due to an unrecoverable external execution failure."
                    ;;
                5)
                    echo "${ICON_SKIP}  sub-${SUBJECT} has already been successfully processed by tedana. Skipping."
                    continue
                    ;;
                130)
                    echo "${ICON_ERROR}  Interrupted by SIGINT"
                    exit 130
                    ;;
                143)
                    echo "${ICON_ERROR}  Terminated by SIGTERM"
                    exit 143
                    ;;
                *)
                    echo "${ICON_ERROR}  Unknown failure (exit status $status)"
                    echo "  See log: ${LOG_FILE}"
                    exit 1
                    ;;
            esac
        fi
    done
done

success_banner
