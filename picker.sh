#!/usr/bin/env bash
export FILE_CATALOG_REST_TOKEN=${FILE_CATALOG_REST_TOKEN:="$(make-token.sh)"}
export FILE_CATALOG_REST_URL=${FILE_CATALOG_REST_URL:="http://127.0.0.1:8888"}
export HEARTBEAT_PATCH_RETRIES=${HEARTBEAT_PATCH_RETRIES:="3"}
export HEARTBEAT_PATCH_TIMEOUT_SECONDS=${HEARTBEAT_PATCH_TIMEOUT_SECONDS:="30"}
export HEARTBEAT_SLEEP_DURATION_SECONDS=${HEARTBEAT_SLEEP_DURATION_SECONDS:="60"}
export LTA_REST_TOKEN=${LTA_REST_TOKEN:="$(make-token.sh)"}
export LTA_REST_URL=${LTA_REST_URL:="http://127.0.0.1:8080"}
export PICKER_NAME=${PICKER_NAME:="$(hostname)-picker"}
export WORK_RETRIES=${WORK_RETRIES:="3"}
export WORK_SLEEP_DURATION_SECONDS=${WORK_SLEEP_DURATION_SECONDS:="300"}
export WORK_TIMEOUT_SECONDS=${WORK_TIMEOUT_SECONDS:="30"}
python -m lta.picker
