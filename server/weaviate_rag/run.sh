#!/usr/bin/env bash
set -euo pipefail

# --- Config (edit paths if needed) ---
BACKEND_DIR="./"
FRONTEND_DIR="../../client"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"

log() { echo -e "[$(date '+%H:%M:%S')] $*"; }

# Pick compose command (v2 or legacy)
if command -v docker compose >/dev/null 2>&1; then
  COMPOSE() { docker compose "$@"; }
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE() { docker-compose "$@"; }
else
  echo "❌ Docker Compose not found. Install Docker Desktop or 'brew install docker-compose'." >&2
  exit 1
fi

# --- Helper: find active LAN IPv4 (macOS) ---
get_lan_ip() {
  if command -v route >/dev/null 2>&1 && command -v ipconfig >/dev/null 2>&1; then
    local iface
    iface=$(route get default 2>/dev/null | awk '/interface:/{print $2}')
    if [[ -n "${iface:-}" ]]; then
      ipconfig getifaddr "$iface" 2>/dev/null || true
    fi
  fi
}

LAN_IP="${LAN_IP:-$(get_lan_ip)}"
if [[ -z "${LAN_IP:-}" ]]; then
  # Fallback to hostname resolution if needed
  LAN_IP=$(hostname -I 2>/dev/null | awk '{print $1}') || true
fi
LAN_IP="${LAN_IP:-127.0.0.1}"

# These env vars are read by next.config.ts
export SITE_HOST="$LAN_IP"
# export BACKEND_ORIGIN="http://localhost:${BACKEND_PORT}"
export BACKEND_ORIGIN="http://132.195.142.65:${BACKEND_PORT}"

# --- Start Weaviate (detached) ---
log "Starting Weaviate (detached)…"
COMPOSE up -d weaviate >/dev/null || true

# --- Wait for Weaviate to be READY ---
log "Waiting for Weaviate to report READY on :8080…"
for i in {1..60}; do
  # if curl -fsS http://localhost:8080/v1/.well-known/ready >/dev/null; then
  if curl -fsS http://132.195.142.65:8080/v1/.well-known/ready >/dev/null; then
    log "Weaviate is READY ✅"
    break
  fi
  sleep 1
  if [[ $i -eq 60 ]]; then
    log "Weaviate did not become ready in time ❌"
    COMPOSE logs --tail 100 weaviate || true
    exit 1
  fi
done

# --- Free a port if a stale process is holding it ---
free_port() {
  local port="$1"
  if lsof -ti :"$port" >/dev/null 2>&1; then
    log "Port $port is in use; trying to free it…"
    kill -TERM $(lsof -ti :"$port") 2>/dev/null || true
    sleep 1
    if lsof -ti :"$port" >/dev/null 2>&1; then
      kill -KILL $(lsof -ti :"$port") 2>/dev/null || true
    fi
  fi
}

free_port "$BACKEND_PORT"
free_port "$FRONTEND_PORT"

# --- Start backend ---
log "Starting FastAPI backend on :$BACKEND_PORT"
pushd "$BACKEND_DIR" >/dev/null
if [[ -d ".venv" ]]; then
  source .venv/bin/activate
fi
uvicorn app.main:app --host 0.0.0.0 --port "$BACKEND_PORT" --reload &
BACKEND_PID=$!
BACKEND_PGID=$BACKEND_PID
popd >/dev/null

# --- Start frontend ---
log "Starting Next.js frontend on :$FRONTEND_PORT (SITE_HOST=$SITE_HOST, BACKEND_ORIGIN=$BACKEND_ORIGIN)"
pushd "$FRONTEND_DIR" >/dev/null
# envs are already exported; pass host/port so other PCs can open it
npm run dev -- -H 0.0.0.0 -p "$FRONTEND_PORT" &
FRONTEND_PID=$!
FRONTEND_PGID=$FRONTEND_PID
popd >/dev/null

# --- Open browser (local machine) ---
sleep 2
# command -v open >/dev/null 2>&1 && open "http://localhost:$FRONTEND_PORT" || true
command -v open >/dev/null 2>&1 && open "http://132.195.142.65:$FRONTEND_PORT" || true

# --- Cleanup on exit (Ctrl+C, TERM, normal exit) ---
cleanup() {
  log "Stopping frontend/backend…"
  kill -TERM "-$FRONTEND_PGID" 2>/dev/null || true
  kill -TERM "-$BACKEND_PGID"  2>/dev/null || true
  sleep 1
  kill -KILL "-$FRONTEND_PGID" 2>/dev/null || true
  kill -KILL "-$BACKEND_PGID"  2>/dev/null || true

  log "Stopping Weaviate…"
  COMPOSE down
}

trap cleanup INT TERM

# Keep the script alive until interrupted
while :; do sleep 3600; done
