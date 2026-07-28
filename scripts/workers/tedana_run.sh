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

# run_tedana_subject.sh
#
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

DO_CLEANUP="${DO_CLEANUP:-false}"
DRY_RUN="${DRY_RUN:-false}"
DEBUG="${DEBUG:-false}"
IGNORE_COMPLETION="${IGNORE_COMPLETION:-false}"


usage() {
    echo "Usage: $0 <fmriprep-derivs> <tedana-derivs> <work-root> <tedana-image> <participant-label> <run> <num-echoes>"
    echo "Example:"
    echo "$0 \\"
    echo "    /path/to/derivatives/fmriprep \\ # input"
    echo "    /path/to/derivatives/tedana \\ # output"
    echo "    /path/to/work \\"
    echo "    local/tedana:26.0.3 \\"
    echo "    001 \\"
    echo "    01 \\"
    echo "    3"
}

info_banner() {
    echo "======================================"
    echo "Running Tedana"
    echo "Subject:         sub-${SUBJECT}"
    echo "fMRIPrep derivs: ${FMRIPREP_SUBJ_DIR}"
    echo "Tedana derivs:   ${TEDANA_RUN_DIR}"
    echo "Work:            ${WORK_DIR}"
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

find_echo_func_files() {
    local func_dir="$1"
    local run=${2:-"??"}
    local echo_glob="sub-${SUBJECT}_*_run-${run}_echo-?_desc-preproc_bold.nii.gz"
    local echo_re="sub-${SUBJECT}_task-semjudge_acq-[a-z]\+_run-[0-9]\{2\}_echo-[1-3]_desc-preproc_bold.nii.gz"
    debug "Find Echo .nii.gz Files ---"
    debug "fMRI Prep Func. Dir  : $func_dir"
    debug "File selection glob  : $echo_glob"
    debug "File verification re : $echo_re"

    find "${func_dir}" -maxdepth 1 -type f -name "${echo_glob}" -printf '%f\n' |
        sed -n /"${echo_re}"/p |
        sort --field-separator='_' --key='4,5'
}

find_echo_json_files() {
    local func_dir="$1"
    local run=${2:-"??"}
    local echo_glob="sub-${SUBJECT}_*_run-${run}_echo-?_desc-preproc_bold.json"
    local echo_re="sub-${SUBJECT}_task-semjudge_acq-[a-z]\+_run-[0-9]\{2\}_echo-[1-3]_desc-preproc_bold.json"
    debug "Find Echo JSON Files ---"
    debug "fMRI Prep Func. Dir  : $func_dir"
    debug "File selection glob  : $echo_glob"
    debug "File verification re : $echo_re"

    find "${func_dir}" -maxdepth 1 -type f -name "${echo_glob}" -printf '%f\n' |
        sed -n /"${echo_re}"/p |
        sort --field-separator='_' --key='4,5'
}

find_input_mask_files() {
    local func_dir="$1"
    local run=${2:-"??"}
    local mask_glob="sub-${SUBJECT}_*_run-${run}_desc-brain_mask.nii.gz"
    local mask_re="sub-${SUBJECT}_task-semjudge_acq-[a-z]\+_run-[0-9]\{2\}_desc-brain_mask.nii.gz"
    debug "Find input brainmask Files ---"
    debug "fMRI Prep Func. Dir  : $func_dir"
    debug "File selection glob  : $mask_glob"
    debug "File verification re : $mask_re"

    find "${func_dir}" -maxdepth 1 -type f -name "${mask_glob}" -printf '%f\n' |
        sed -n /"${mask_re}"/p |
        sort --field-separator='_' --key='4,5'
}

find_T1_mask_files() {
    local func_dir="$1"
    local run=${2:-"??"}
    local mask_glob="sub-${SUBJECT}_*_run-${run}_space-T1w_desc-brain_mask.nii.gz"
    local mask_re="sub-${SUBJECT}_task-semjudge_acq-[a-z]\+_run-[0-9]\{2\}_space-T1w_desc-brain_mask.nii.gz"
    debug "Find T1 brainmask Files ---"
    debug "fMRI Prep Func. Dir  : $func_dir"
    debug "File selection glob  : $mask_glob"
    debug "File verification re : $mask_re"

    find "${func_dir}" -maxdepth 1 -type f -name "${mask_glob}" -printf '%f\n' |
        sed -n /"${mask_re}"/p |
        sort --field-separator='_' --key='4,5'
}

find_MNI_mask_files() {
    local func_dir="$1"
    local run=${2:-"??"}
    local mask_glob="sub-${SUBJECT}_*_run-${run}_space-MNI152NLin2009cAsym_desc-brain_mask.nii.gz"
    local mask_re="sub-${SUBJECT}_task-semjudge_acq-[a-z]\+_run-[0-9]\{2\}_space-MNI152NLin2009cAsym_desc-brain_mask.nii.gz"
    debug "Find MNI brainmask Files ---"
    debug "fMRI Prep Func. Dir  : $func_dir"
    debug "File selection glob  : $mask_glob"
    debug "File verification re : $mask_re"

    find "${func_dir}" -maxdepth 1 -type f -name "${mask_glob}" -printf '%f\n' |
        sed -n /"${mask_re}"/p |
        sort --field-separator='_' --key='4,5'
}

validate_complete() {
    local sentinal_file="sub-${SUBJECT}_run-${RUN}_tedana_report.html"
    if [[ -f "${TEDANA_RUN_DIR}/${sentinal_file}" ]]; then
        if [[ "${IGNORE_COMPLETION}" == "true" ]]; then
            echo "[IGNORE_COMPLETION] ${sentinal_file} exists, but tedana will run."
        else
            echo "sub-${SUBJECT} already processed. Skipping." >&2
            exit 5
        fi
    fi
}

validate_inputs() {
    local func_dir="${FMRIPREP_SUBJ_DIR}/func"
    local echo_files
    if [[ ! -d "${func_dir}" ]]; then
        die_missing_inputs "ERROR: '${func_dir}' does not exist."
    fi

    mapfile -t echo_func_files < <(find_echo_func_files "$func_dir" "${RUN}")
    if [[ "${#echo_func_files[@]}" -ne "$NUM_ECHOES" ]]; then
        die_missing_inputs "ERROR: Expected ${NUM_ECHOES} echo nii.gz files, but found ${#echo_func_files[@]}."
    fi
     
    mapfile -t echo_json_files < <(find_echo_json_files "$func_dir" "${RUN}")
    if [[ "${#echo_json_files[@]}" -ne "$NUM_ECHOES" ]]; then
        die_missing_inputs "ERROR: Expected ${NUM_ECHOES} echo json files, but found ${#echo_json_files[@]}."
    fi

    mapfile -t input_mask_files < <(find_input_mask_files "$func_dir" "${RUN}")
    if [[ "${#input_mask_files[@]}" -ne 1 ]]; then
        die_missing_inputs \
            "ERROR: Expected 1 input brain mask, but found ${#input_mask_files[@]}."
    fi

    mapfile -t T1_mask_files < <(find_T1_mask_files "$func_dir" "${RUN}")
    if [[ "${#T1_mask_files[@]}" -ne 1 ]]; then
        die_missing_inputs \
            "ERROR: Expected 1 T1 brain mask, but found ${#T1_mask_files[@]}."
    fi

    mapfile -t MNI_mask_files < <(find_MNI_mask_files "$func_dir" "${RUN}")
    if [[ "${#MNI_mask_files[@]}" -ne 1 ]]; then
        die_missing_inputs \
            "ERROR: Expected 1 MNI brain mask, but found ${#MNI_mask_files[@]}."
    fi
}

validate_podman() {
    command -v podman >/dev/null 2>&1 || {
        echo "ERROR: podman not found in PATH" >&2
        exit 3
    }
}

run_tedana() {
    local func_dir="${FMRIPREP_SUBJ_DIR}/func"
    debug "Running tedana for sub-${SUBJECT} run-${RUN}"
    local echo_files
    local echo_files_container=()
    local echo_times=()
    mapfile -t echo_files < <(find_echo_func_files "$func_dir" "${RUN}")
    for func in "${echo_files[@]}"; do
        json="${func_dir}/${func%.nii.gz}.json"
        etime=$(jq -er '.EchoTime' "${json}") || die_missing_inputs "Missing 'EchoTime' in ${json}"
        echo_times+=("$etime")
        echo_files_container+=("/data/$func")
    done

    local first_echo="${echo_files[0]}"
    local stem=${first_echo%_echo-?_desc-preproc_bold.nii.gz}
    local input_mask_file="${stem}_desc-brain_mask.nii.gz"

    local cmd=(
        podman run --rm
        -v "${func_dir}:/data:ro,Z"
        -v "${TEDANA_RUN_DIR}:/out:Z"
        -v "${WORK_DIR}:/work:Z"
        "${TEDANA_IMAGE}"
        -d "${echo_files_container[@]}"
        -e "${echo_times[@]}"
        --mask "/data/$input_mask_file"
        --out-dir "/out"
        --prefix "sub-${SUBJECT}_run-${RUN}"
        --verbose
    )

    if [[ "${IGNORE_COMPLETION}" == true ]]; then
        cmd+=(--overwrite)
    fi

    if [[ "${DRY_RUN}" == true ]]; then
        printf '[DRY-RUN] %q ' "${cmd[@]}"
        echo
        return 0
    fi

    debug "Executing tedana command"
    "${cmd[@]}"
}

trap cleanup EXIT
trap 'DO_CLEANUP=true; exit 130' SIGINT
trap 'DO_CLEANUP=true; exit 143' SIGTERM

### ----------------------------
### Parse arguments
### ----------------------------
if [[ $# -ne 7 ]]; then
    usage >&2
    exit 2
fi

FMRIPREP_ROOT="$1"
TEDANA_ROOT="$2"
WORK_ROOT="$3"
TEDANA_IMAGE="$4"
SUBJECT="$5"
RUN="$6"
NUM_ECHOES="$7"

### ----------------------------
### Derive paths and create output directories
### ----------------------------
FMRIPREP_SUBJ_DIR="${FMRIPREP_ROOT}/sub-${SUBJECT}"
TEDANA_RUN_DIR="${TEDANA_ROOT}/sub-${SUBJECT}/run-${RUN}"
WORK_DIR="${WORK_ROOT}/sub-${SUBJECT}/run-${RUN}"

debug "Derived FMRIPREP_SUBJ_DIR=${FMRIPREP_SUBJ_DIR}"
debug "Derived TEDANA_RUN_DIR=${TEDANA_RUN_DIR}"
debug "Derived WORK_DIR=${WORK_DIR}"
mkdir -p "${WORK_DIR}" "${TEDANA_RUN_DIR}"

debug "Using image ${TEDANA_IMAGE}"


### ----------------------------
### Validate inputs
### ----------------------------
validate_complete
validate_inputs
validate_podman

info_banner

### ----------------------------
### Run tedana
### ----------------------------

if run_tedana; then
    DO_CLEANUP=true
    exit 0
else
    die_external "Tedana failed for sub-${SUBJECT} run-${RUN}"
fi
