#!/usr/bin/env bash

cleanup_empty_tedana_dirs() {
    find derivatives/tedana -mindepth 1 -type d -empty -exec rmdir '{}' +
}

preview_empty_tedana_dirs() {
    find derivatives/tedana -mindepth 1 -type d -empty -print
}

run_shellcheck() {
    shellcheck scripts/*/*.sh
}

