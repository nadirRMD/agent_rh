#!/usr/bin/env bash

set -euo pipefail

BACKEND_PORT="${AGENT_RH_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
FRONTEND_AUTH_LOGIN="${FRONTEND_AUTH_LOGIN:-agent-rh}"
FRONTEND_AUTH_PASSWORD="${FRONTEND_AUTH_PASSWORD:-agent-rh}"
FRONTEND_AUTH_SECRET="${FRONTEND_AUTH_SECRET:-agent-rh-dev-secret}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME_DIR="${AGENT_RH_RUNTIME_DIR:-/tmp/agent-rh-dev}"
UV_CACHE_DIR="${RUNTIME_DIR}/uv-cache"
UV_DATA_HOME="${RUNTIME_DIR}/uv-data"
PID_DIR="${RUNTIME_DIR}/pids"
BACKEND_PID_FILE="${PID_DIR}/backend.pid"
FRONTEND_PID_FILE="${PID_DIR}/frontend.pid"
NEXT_RUNTIME_DIR="${ROOT_DIR}/frontend/.next"
FRONTEND_NODE_MODULES_DIR="${ROOT_DIR}/frontend/node_modules"

port_is_open() {
  local host="$1"
  local port="$2"
  (echo >/dev/tcp/"${host}"/"${port}") >/dev/null 2>&1
}

assert_port_free() {
  local name="$1"
  local port="$2"
  if port_is_open 127.0.0.1 "${port}"; then
    echo "${name} is already running on port ${port}. Stop it before starting dev.sh." >&2
    exit 1
  fi
}

pid_is_running() {
  local pid="$1"
  [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null
}

kill_tree() {
  local pid="$1"
  local child

  while read -r child; do
    [[ -n "${child}" ]] || continue
    kill_tree "${child}"
  done < <(ps -o pid= --ppid "${pid}" 2>/dev/null || true)

  kill "${pid}" 2>/dev/null || true
}

write_pid_file() {
  local file="$1"
  local pid="$2"
  mkdir -p "$(dirname "${file}")"
  printf '%s\n' "${pid}" > "${file}"
}

read_pid_file() {
  local file="$1"
  if [[ -f "${file}" ]]; then
    tr -d '[:space:]' < "${file}"
  fi
}

stop_from_pid_files() {
  local backend_pid frontend_pid
  backend_pid="$(read_pid_file "${BACKEND_PID_FILE}")"
  frontend_pid="$(read_pid_file "${FRONTEND_PID_FILE}")"

  if [[ -z "${backend_pid}" && -z "${frontend_pid}" ]]; then
    echo "No running Agent RH processes were found."
    return 0
  fi

  if [[ -n "${frontend_pid}" ]] && pid_is_running "${frontend_pid}"; then
    echo "Stopping frontend tree rooted at PID ${frontend_pid}"
    kill_tree "${frontend_pid}"
  fi

  if [[ -n "${backend_pid}" ]] && pid_is_running "${backend_pid}"; then
    echo "Stopping backend tree rooted at PID ${backend_pid}"
    kill_tree "${backend_pid}"
  fi

  sleep 1

  if [[ -n "${frontend_pid}" ]] && pid_is_running "${frontend_pid}"; then
    kill -9 "${frontend_pid}" 2>/dev/null || true
  fi

  if [[ -n "${backend_pid}" ]] && pid_is_running "${backend_pid}"; then
    kill -9 "${backend_pid}" 2>/dev/null || true
  fi

  rm -rf "${RUNTIME_DIR}"
  echo "Agent RH processes stopped and runtime environment cleaned."
}

start_mode() {
  prepare_runtime
  assert_port_free "Backend" "${BACKEND_PORT}"
  assert_port_free "Frontend" "${FRONTEND_PORT}"

  echo "Starting Agent RH backend on http://127.0.0.1:${BACKEND_PORT}"
  (
    cd "${ROOT_DIR}"
    UV_CACHE_DIR="${UV_CACHE_DIR}" XDG_DATA_HOME="${UV_DATA_HOME}" AGENT_RH_PORT="${BACKEND_PORT}" uv run python main.py
  ) &
  backend_pid=$!
  write_pid_file "${BACKEND_PID_FILE}" "${backend_pid}"

  echo "Starting Next.js frontend on http://127.0.0.1:${FRONTEND_PORT}"
  (
    cd "${ROOT_DIR}/frontend"
    if [[ ! -x "node_modules/.bin/next" ]]; then
      echo "Installing frontend dependencies..."
      npm install
    fi
    PORT="${FRONTEND_PORT}" \
    FRONTEND_AUTH_LOGIN="${FRONTEND_AUTH_LOGIN}" \
    FRONTEND_AUTH_PASSWORD="${FRONTEND_AUTH_PASSWORD}" \
    FRONTEND_AUTH_SECRET="${FRONTEND_AUTH_SECRET}" \
    npm run dev
  ) &
  frontend_pid=$!
  write_pid_file "${FRONTEND_PID_FILE}" "${frontend_pid}"

  cleanup() {
    local pid
    for pid in "${frontend_pid}" "${backend_pid}"; do
      if pid_is_running "${pid}"; then
        kill_tree "${pid}"
      fi
    done
    sleep 1
    for pid in "${frontend_pid}" "${backend_pid}"; do
      if pid_is_running "${pid}"; then
        kill -9 "${pid}" 2>/dev/null || true
      fi
    done
    rm -rf "${RUNTIME_DIR}"
  }

  trap cleanup EXIT INT TERM
  wait "${backend_pid}" "${frontend_pid}"
}

prepare_runtime() {
  rm -rf "${RUNTIME_DIR}"
  mkdir -p "${UV_CACHE_DIR}" "${UV_DATA_HOME}"
  rm -rf "${NEXT_RUNTIME_DIR}"
  rm -rf "${FRONTEND_NODE_MODULES_DIR}/.cache"
}

usage() {
  cat <<EOF
Usage:
  ./dev.sh
  ./dev.sh start
  ./dev.sh --stop
EOF
}

main() {
  local command="${1:-start}"

  case "${command}" in
    start)
      start_mode
      ;;
    --stop|stop)
      stop_from_pid_files
      ;;
    -h|--help|help)
      usage
      ;;
    *)
      echo "Unknown command: ${command}" >&2
      usage >&2
      exit 1
      ;;
  esac
}

main "$@"
