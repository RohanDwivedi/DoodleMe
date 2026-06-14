"""Spawns a URDF model into Gazebo Harmonic via ros_gz_sim."""

from __future__ import annotations

import subprocess
import threading
from pathlib import Path


class GazeboBridge:
    """Manages Gazebo launch and entity spawn for a given URDF."""

    def __init__(self) -> None:
        self._gz_proc: subprocess.Popen | None = None
        self._lock = threading.Lock()

    def launch_and_spawn(self, urdf_path: Path, model_name: str = "doodle_robot") -> None:
        """Start Gazebo (if not running) then spawn the URDF model."""
        thread = threading.Thread(
            target=self._do_launch_and_spawn,
            args=(urdf_path, model_name),
            daemon=True,
        )
        thread.start()

    def _do_launch_and_spawn(self, urdf_path: Path, model_name: str) -> None:
        with self._lock:
            if not self._gz_running():
                self._start_gazebo()

        urdf_xml = urdf_path.read_text()
        spawn_cmd = [
            "ros2",
            "run",
            "ros_gz_sim",
            "create",
            "-name",
            model_name,
            "-string",
            urdf_xml,
        ]
        try:
            subprocess.run(spawn_cmd, timeout=30, check=True)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            pass

    def _start_gazebo(self) -> None:
        try:
            self._gz_proc = subprocess.Popen(
                ["ros2", "launch", "ros_gz_sim", "gz_sim.launch.py", "gz_args:=-r empty.sdf"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            pass

    def _gz_running(self) -> bool:
        return self._gz_proc is not None and self._gz_proc.poll() is None

    def stop(self) -> None:
        with self._lock:
            if self._gz_proc and self._gz_proc.poll() is None:
                self._gz_proc.terminate()
            self._gz_proc = None

    def __del__(self) -> None:
        self.stop()
