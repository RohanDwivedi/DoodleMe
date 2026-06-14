"""Publishes robot_description and launches robot_state_publisher."""

from __future__ import annotations

import subprocess
import threading
from pathlib import Path


class URDFPublisher:
    """Manages the robot_state_publisher subprocess for live URDF preview."""

    def __init__(self) -> None:
        self._proc: subprocess.Popen | None = None
        self._lock = threading.Lock()

    def publish(self, urdf_path: Path) -> None:
        """(Re)launch robot_state_publisher with the given URDF."""
        with self._lock:
            self._stop_proc()
            urdf_xml = urdf_path.read_text()
            cmd = [
                "ros2",
                "run",
                "robot_state_publisher",
                "robot_state_publisher",
                "--ros-args",
                "-p",
                f"robot_description:={urdf_xml}",
            ]
            try:
                self._proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except FileNotFoundError:
                pass  # ROS2 not sourced; handled by status bar

    def stop(self) -> None:
        with self._lock:
            self._stop_proc()

    def is_running(self) -> bool:
        with self._lock:
            return self._proc is not None and self._proc.poll() is None

    def _stop_proc(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        self._proc = None

    def __del__(self) -> None:
        self.stop()
