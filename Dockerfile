# ─────────────────────────────────────────────────────────────────────────────
# DoodleMe — AI-assisted robot design (ROS2 Jazzy + Claude LLM)
# ─────────────────────────────────────────────────────────────────────────────
FROM osrf/ros:jazzy-desktop

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# ── Layer 1: system packages ──────────────────────────────────────────────────
# Grouped by concern; single RUN to minimise layers.
RUN apt-get update && apt-get install -y --no-install-recommends \
    # rqt + Qt5
    ros-jazzy-rqt \
    ros-jazzy-rqt-gui \
    ros-jazzy-rqt-gui-py \
    ros-jazzy-python-qt-binding \
    python3-pyqt5 \
    python3-pyqt5.qtwebengine \
    pyqt5-dev-tools \
    # ROS2 robot stack
    ros-jazzy-robot-state-publisher \
    ros-jazzy-joint-state-publisher-gui \
    ros-jazzy-rviz2 \
    ros-jazzy-ros-gz-sim \
    # Message generation
    ros-jazzy-rosidl-default-generators \
    ros-jazzy-rosidl-default-runtime \
    # Python runtime
    python3-pip \
    python3-lxml \
    python3-yaml \
    # OpenSCAD (headless STL rendering, no display needed)
    openscad \
    # OpenGL / VTK (for pyvistaqt 3-D viewer)
    libgl1 \
    libgl1-mesa-dri \
    libgles2 \
    mesa-utils \
    libglib2.0-0 \
    libxrender1 \
    libxext6 \
    libx11-xcb1 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-xinerama0 \
    libxcb-xkb1 \
    libxkbcommon-x11-0 \
    # Fallback virtual framebuffer (when no host display available)
    xvfb \
    # Utilities
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Layer 2: Python packages ──────────────────────────────────────────────────
# Installed before copying source so this layer is cached on code changes.
RUN pip3 install --no-cache-dir \
    "anthropic>=0.28" \
    pyvistaqt \
    pyvista \
    vtk

# ── Layer 3: workspace source ─────────────────────────────────────────────────
WORKDIR /ros2_ws
COPY ros2_ws/src ./src

# ── Layer 4: colcon build (only our 4 packages) ───────────────────────────────
RUN /bin/bash -c "\
    source /opt/ros/jazzy/setup.bash && \
    colcon build \
        --symlink-install \
        --packages-select doodle_msgs doodle_description doodle_agent rqt_doodle \
        --cmake-args -DCMAKE_BUILD_TYPE=Release \
    "

# ── Runtime environment ───────────────────────────────────────────────────────
ENV QT_X11_NO_MITSHM=1 \
    QT_API=pyqt5 \
    # Uncomment to force software rendering (no GPU / CI):
    # LIBGL_ALWAYS_SOFTWARE=1 \
    ROS_DOMAIN_ID=0

# Persistent directories created at build time so volume mounts work cleanly.
RUN mkdir -p \
    /root/.config/rqt_doodle \
    /root/.local/share/rqt_doodle/sessions \
    /root/doodle_workspace

# ── Docker helper scripts ─────────────────────────────────────────────────────
RUN mkdir -p /docker
COPY docker/setup_wizard.py /docker/setup_wizard.py
COPY docker/entrypoint.sh /docker/entrypoint.sh
RUN chmod +x /docker/entrypoint.sh

# Back-compat symlink so existing docs / scripts that reference /entrypoint.sh still work.
RUN ln -s /docker/entrypoint.sh /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
