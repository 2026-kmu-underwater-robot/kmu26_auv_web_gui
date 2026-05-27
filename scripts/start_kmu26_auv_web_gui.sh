#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
WORKSPACE_DIR="$(cd "${PACKAGE_DIR}/.." && pwd)"

HOST="${KMU26_WEB_GUI_HOST:-0.0.0.0}"
PORT="${KMU26_WEB_GUI_PORT:-8080}"
ROBOT_PACKAGE="${KMU26_ROBOT_PACKAGE:-hit25_auv_ros2}"
ROBOT_LAUNCH="${KMU26_ROBOT_LAUNCH:-localization_test.launch.py}"

source_if_exists() {
  local setup_file="$1"
  if [[ -f "${setup_file}" ]]; then
    # shellcheck source=/dev/null
    source "${setup_file}"
  fi
}

if [[ -z "${ROS_DISTRO:-}" ]]; then
  if [[ -f "/opt/ros/humble/setup.bash" ]]; then
    source_if_exists "/opt/ros/humble/setup.bash"
  elif [[ -f "/opt/ros/jazzy/setup.bash" ]]; then
    source_if_exists "/opt/ros/jazzy/setup.bash"
  fi
fi

source_if_exists "${WORKSPACE_DIR}/install/setup.bash"

if ! command -v ros2 >/dev/null 2>&1; then
  echo "[kmu26_auv_web_gui] ros2 command not found."
  echo "Source ROS 2 first, or build/source this workspace:"
  echo "  source /opt/ros/humble/setup.bash"
  echo "  source ${WORKSPACE_DIR}/install/setup.bash"
  exit 1
fi

python3 - <<'PY'
import importlib.util
import sys

missing = [name for name in ("fastapi", "uvicorn") if importlib.util.find_spec(name) is None]
if missing:
    print("[kmu26_auv_web_gui] Missing Python packages: " + ", ".join(missing))
    print("Install on the Ubuntu robot PC:")
    print("  python3 -m pip install fastapi uvicorn")
    sys.exit(1)
PY

echo "[kmu26_auv_web_gui] Starting server"
echo "[kmu26_auv_web_gui] Open from Mac: http://<ubuntu-robot-ip>:${PORT}"
echo "[kmu26_auv_web_gui] Host=${HOST} Port=${PORT}"

if ros2 pkg prefix kmu26_auv_web_gui >/dev/null 2>&1; then
  exec ros2 run kmu26_auv_web_gui server \
    --host "${HOST}" \
    --port "${PORT}" \
    --robot-package "${ROBOT_PACKAGE}" \
    --robot-launch "${ROBOT_LAUNCH}"
fi

export PYTHONPATH="${PACKAGE_DIR}:${PYTHONPATH:-}"
export KMU26_WEB_GUI_WEB_DIR="${PACKAGE_DIR}/web"
exec python3 -m kmu26_auv_web_gui.server \
  --host "${HOST}" \
  --port "${PORT}" \
  --robot-package "${ROBOT_PACKAGE}" \
  --robot-launch "${ROBOT_LAUNCH}"
