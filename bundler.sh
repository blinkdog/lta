#!/usr/bin/env bash
export BUNDLER_NAME="$(hostname)-bundler"
export BUNDLER_SITE_SOURCE="WIPAC"
export HEARTBEAT_PATCH_RETRIES="3"
export HEARTBEAT_PATCH_TIMEOUT_SECONDS="5"
export HEARTBEAT_SLEEP_DURATION_SECONDS="30"
export LTA_REST_TOKEN="$(make-token.sh)"
export LTA_REST_URL="http://127.0.0.1:8080"
export LTA_SITE_CONFIG="etc/site.json"
export OUTBOX_PATH="/data/user/lta/bundler_out"
export WORK_RETRIES="3"
export WORK_SLEEP_DURATION_SECONDS="30"
export WORK_TIMEOUT_SECONDS="5"
export WORKBOX_PATH="/data/user/lta/bundler_work"
python -m lta.bundler
