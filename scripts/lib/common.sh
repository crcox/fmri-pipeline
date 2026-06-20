#!/usr/bin/env bash
set -euo pipefail

# Source only once per process ---
if [[ -n ${_COMMON_SOURCED:-} ]]; then
    return 0
fi
_COMMON_SOURCED=1


# Pipeline modes ---
DEBUG="${DEBUG:-false}"
DRY_RUN="${DRY_RUN:-false}"

debug() {
    if [[ "${DEBUG}" == true ]]; then
        echo "[DEBUG] $*" >&2
    fi
}


# Exit helpers ---
die_usage()          { echo "$*" >&2; exit 2; }
die_missing_inputs() { echo "$*" >&2; exit 3; }
die_external()       { echo "$*" >&2; exit 4; }


# Signal handling ---
install_signal_traps() {
    trap 'DO_CLEANUP=true; exit 130' SIGINT
    trap 'DO_CLEANUP=true; exit 143' SIGTERM
}



# Unicode glyphs ---
USE_COLOR="${USE_COLOR:-true}"
USE_UNICODE="${USE_UNICODE:-true}"

# shellcheck disable=SC2034
if [[ "${USE_UNICODE}" == true ]]; then
    ICON_SUCCESS="✅"
    ICON_ERROR="❌"
    ICON_SKIP="⏭"
    ICON_WARNING="⚠️"
    ICON_FATAL="🔥"
    ICON_DONE="🎉"
    ICON_START="▶"
    ICON_INFO="ℹ️"
else
    ICON_SUCCESS="[OK]"
    ICON_ERROR="[ERROR]"
    ICON_SKIP="[SKIP]"
    ICON_WARNING="[WARNING]"
    ICON_FATAL="[FATAL]"
    ICON_DONE="[DONE]"
    ICON_START="[START]"
    ICON_INFO="[INFO]"
fi

