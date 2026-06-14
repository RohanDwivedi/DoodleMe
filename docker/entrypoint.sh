#!/usr/bin/env bash
set -eo pipefail

# ── Source ROS2 and the built workspace ──────────────────────────────────────
source /opt/ros/jazzy/setup.bash
source /ros2_ws/install/setup.bash

# ── Display setup ─────────────────────────────────────────────────────────────
if [ -z "${DISPLAY:-}" ]; then
    echo "[doodle] DISPLAY not set — starting virtual framebuffer on :99"
    echo "[doodle] For a real window on your host, run:"
    echo "[doodle]   xhost +local:docker && DISPLAY=\$DISPLAY docker compose up"
    Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp &
    XVFB_PID=$!
    export DISPLAY=:99
    # Give Xvfb a moment to start
    sleep 1
    trap "kill $XVFB_PID 2>/dev/null || true" EXIT
fi

# ── Secret availability check (informational only) ────────────────────────────
if [ -f /run/secrets/anthropic_api_key ]; then
    echo "[doodle] API key loaded from Docker secret."
elif [ -n "${ANTHROPIC_API_KEY:-}" ]; then
    echo "[doodle] API key loaded from environment variable."
else
    echo "[doodle] No API key found. Enter it via Settings → API on first launch."
fi

# ── Workspace directory ───────────────────────────────────────────────────────
mkdir -p /root/doodle_workspace
mkdir -p /root/.local/share/rqt_doodle/sessions
mkdir -p /root/.config/rqt_doodle

echo "[doodle] Launching DoodleMe …"
exec rqt --standalone DoodleMe --force-discover "$@"
