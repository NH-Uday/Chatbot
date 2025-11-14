#!/usr/bin/env bash
set -euo pipefail

# --- Config ---
BACKEND_DIR="./"                # FastAPI app root (weaviate_rag)
FRONTEND_DIR="../../client"     # Next.js app (adjust if different)
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"

log() { echo -e "[$(date '+%H:%M:%S')] $*"; }

# --- Pick compose command (v2 or legacy) ---
if command -v docker compose >/dev/null 2>&1; then
  COMPOSE() { docker compose "$@"; }
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE() { docker-compose "$@"; }
else
  echo "❌ Docker Compose not found. Install Docker + docker compose." >&2
  exit 1
fi

# --- Get LAN IP (Linux-friendly, works on server/headless) ---
get_lan_ip() {
  # Preferred: use `ip route` if available
  if command -v ip >/dev/null 2>&1; then
    ip route get 1.1.1.1 2>/dev/null \
      | awk '/src/ {for(i=1;i<=NF;i++) if($i=="src") {print $(i+1); exit}}'
    return
  fi

  # Fallback: hostname -I
  if command -v hostname >/dev/null 2>&1; then
    hostname -I 2>/dev/null | awk '{print $1}'
    return
  fi
}

LAN_IP="${LAN_IP:-$(get_lan_ip || true)}"
LAN_IP="${LAN_IP:-127.0.0.1}"

# These env vars are read by next.config.ts / frontend
export SITE_HOST="$LAN_IP"
export BACKEND_ORIGIN="http://${LAN_IP}:${BACKEND_PORT}"

# --- Start Weaviate (detached) ---
log "Starting Weaviate (detached)…"
COMPOSE up -d weaviate || {
  log "Failed to start Weaviate via docker compose. (Permission issue? Try: sudo usermod -aG docker \$USER)"
  exit 1
}

# --- Wait for Weaviate to be READY ---
log "Waiting for Weaviate to report READY on :8080…"
for i in {1..60}; do
  if curl -fsS "http://localhost:8080/v1/.well-known/ready" >/dev/null; then
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
  if command -v lsof >/dev/null 2>&1 && lsof -ti :"$port" >/dev/null 2>&1; then
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

# --- Start backend (FastAPI) ---
log "Starting FastAPI backend on :$BACKEND_PORT"
pushd "$BACKEND_DIR" >/dev/null

# Activate venv if present (Linux: you had 'env')
if [[ -d "env" ]]; then
  # shellcheck source=/dev/null
  source env/bin/activate
elif [[ -d ".venv" ]]; then
  # shellcheck source=/dev/null
  source .venv/bin/activate
fi

uvicorn app.main:app --host 0.0.0.0 --port "$BACKEND_PORT" --reload &
BACKEND_PID=$!
BACKEND_PGID=$BACKEND_PID

popd >/dev/null

# --- Start frontend (Next.js) ---
log "Starting Next.js frontend on :$FRONTEND_PORT (SITE_HOST=$SITE_HOST, BACKEND_ORIGIN=$BACKEND_ORIGIN)"
pushd "$FRONTEND_DIR" >/dev/null

npm run dev -- -H 0.0.0.0 -p "$FRONTEND_PORT" &
FRONTEND_PID=$!
FRONTEND_PGID=$FRONTEND_PID

popd >/dev/null

# --- No 'open' on Linux: just log URLs ---
log "Backend:   http://${LAN_IP}:${BACKEND_PORT}"
log "Frontend:  http://${LAN_IP}:${FRONTEND_PORT}"

# --- Cleanup on exit ---
cleanup() {
  log "Stopping frontend/backend…"
  kill -TERM "-$FRONTEND_PGID" 2>/dev/null || true
  kill -TERM "-$BACKEND_PGID"  2>/dev/null || true
  sleep 1
  kill -KILL "-$FRONTEND_PGID" 2>/dev/null || true
  kill -KILL "-$BACKEND_PGID"  2>/dev/null || true

  log "Stopping Weaviate containers…"
  COMPOSE down
}

trap cleanup INT TERM

# Keep script running so Ctrl+C triggers cleanup
while :; do sleep 3600; done