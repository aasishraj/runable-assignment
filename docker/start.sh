#!/bin/bash
set -ex

# Start Xvfb
Xvfb :1 -screen 0 1024x768x16 &

# Start VNC server
x11vnc -display :1 -nopw -forever &

# Start noVNC
/usr/share/novnc/utils/launch.sh --vnc localhost:5900 --listen 6080 &

# Start the agent
python3 /home/agent/agent/main.py > /home/agent/workspace/agent.log 2>&1 &

# Keep the container running and show logs
tail -f /home/agent/workspace/agent.log 