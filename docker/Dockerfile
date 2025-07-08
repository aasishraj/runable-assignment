# Dockerfile for the agent container
FROM debian:bookworm-slim

# Set frontend to noninteractive
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # VNC and X server
    xvfb tigervnc-standalone-server novnc x11vnc tigervnc-tools net-tools \
    # GUI control
    xdotool \
    # Python and tools
    python3 python3-pip \
    # NodeJS and tools
    nodejs npm \
    # Other essentials
    curl git sudo \
    && rm -rf /var/lib/apt/lists/*

# Set up a non-root user 'agent'
RUN useradd -m -s /bin/bash agent && \
    adduser agent sudo && \
    echo "agent ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

# Set up VNC
RUN mkdir -p /home/agent/.vnc && \
    echo "agent_password" | vncpasswd -f > /home/agent/.vnc/passwd && \
    chown -R agent:agent /home/agent/.vnc && \
    chmod 600 /home/agent/.vnc/passwd

# Copy startup script
COPY docker/start.sh /home/agent/start.sh
RUN chown agent:agent /home/agent/start.sh && \
    chmod +x /home/agent/start.sh

# Copy agent code
COPY agent /home/agent/agent
RUN chown -R agent:agent /home/agent/agent

# Switch to the 'agent' user
USER agent
WORKDIR /home/agent/workspace

# Expose VNC port
EXPOSE 6080

# Command to run on startup
CMD ["/home/agent/start.sh"] 