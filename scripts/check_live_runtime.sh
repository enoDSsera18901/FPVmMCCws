#!/usr/bin/env bash
set -euo pipefail

missing=0
check_command() {
  local command_name="$1"
  if command -v "$command_name" >/dev/null 2>&1; then
    printf 'FOUND command=%s path=%s\n' "$command_name" "$(command -v "$command_name")"
  else
    printf 'MISSING command=%s\n' "$command_name"
    missing=1
  fi
}

check_command ros2
check_command MicroXRCEAgent

if command -v gz >/dev/null 2>&1; then
  printf 'FOUND command=gz path=%s\n' "$(command -v gz)"
elif command -v gazebo >/dev/null 2>&1; then
  printf 'FOUND command=gazebo path=%s\n' "$(command -v gazebo)"
else
  printf 'MISSING command=gz-or-gazebo\n'
  missing=1
fi

if [[ -z "${PX4_AUTOPILOT_DIR:-}" ]]; then
  printf 'MISSING environment=PX4_AUTOPILOT_DIR\n'
  missing=1
elif [[ ! -x "${PX4_AUTOPILOT_DIR}/build/px4_sitl_default/bin/px4" ]]; then
  printf 'MISSING executable=%s/build/px4_sitl_default/bin/px4\n' "$PX4_AUTOPILOT_DIR"
  missing=1
else
  printf 'FOUND executable=%s/build/px4_sitl_default/bin/px4\n' "$PX4_AUTOPILOT_DIR"
fi

if [[ "$missing" -ne 0 ]]; then
  printf 'BLOCKED: live pair-2 PX4/Gazebo/ROS2 gate cannot run. No simulation result claimed.\n'
  exit 2
fi

printf 'READY: required executables detected; exact compatible revisions still require capture.\n'

