#!/usr/bin/env bash
# Daily run for the American Exit Index.
# Deploy to Mac Mini cron: 0 6 * * *  bash ~/Projects/GoThere/exit_index/cron.sh
#
# Sequence: scrape → score → commit + push. Failures land in Telegram via
# the crew telegram_reporter if TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID are
# in the environment.

set -euo pipefail

cd "$(dirname "$0")"
LOG="cron.log"
PY="${PY:-./venv/bin/python}"  # repo-local venv interpreter; override with PY=python3 for system-Python boxes

notify() {
  local status=$1; shift
  local msg="$*"
  echo "[$(date -u +%FT%TZ)] [$status] $msg" >> "$LOG"
  if [[ -n "${TELEGRAM_BOT_TOKEN:-}" && -n "${TELEGRAM_CHAT_ID:-}" ]]; then
    curl -fsS --max-time 10 \
      -d "chat_id=${TELEGRAM_CHAT_ID}" \
      -d "text=Exit Index [$status]: $msg" \
      "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
      >/dev/null || true
  fi
}

run_step() {
  local name=$1; shift
  if ! "$@" >> "$LOG" 2>&1; then
    notify "FAIL" "$name failed; see $LOG"
    exit 1
  fi
}

run_step "scrape"  "$PY" scrape.py
run_step "score"   "$PY" score.py

if ! git diff --quiet -- data/; then
  git add data/
  git -c user.name="exit-index-bot" -c user.email="luxextenebries@gmail.com" \
    commit -m "exit_index: $(date +%F)" >> "$LOG" 2>&1
  git push >> "$LOG" 2>&1 || notify "WARN" "git push failed"
  notify "OK" "$(date +%F) ranking published"
else
  notify "OK" "$(date +%F) no data changes"
fi
