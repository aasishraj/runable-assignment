#!/bin/bash
set -e

# Start Xvfb
Xvfb :1 -screen 0 1024x768x16 &
XVFB_PID=$!
export DISPLAY=:1

# Start window manager
fluxbox &
FLUXBOX_PID=$!

# Start VNC server
x11vnc -display :1 -nopw -listen 0.0.0.0 -forever -xkb &
X11VNC_PID=$!

# Start noVNC
websockify -D --web=/usr/local/noVNC-1.4.0/ 6080 localhost:5900 &
WEBSOCKIFY_PID=$!

# Start the agent
python3 /home/agent/agent/main.py

# Clean up on exit
kill $WEBSOCKIFY_PID
kill $X11VNC_PID
kill $FLUXBOX_PID
kill $XVFB_PID 