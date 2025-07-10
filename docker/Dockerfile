# Base image
FROM ubuntu:22.04

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update && apt-get install -y \
    sudo \
    fluxbox \
    xterm \
    x11vnc \
    xvfb \
    xdotool \
    python3 \
    python3-pip \
    curl \
    git \
    nodejs \
    npm \
    websockify \
    --no-install-recommends && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Setup VNC password
RUN mkdir -p /root/.vnc && x11vnc -storepasswd agent /root/.vnc/passwd

# Setup noVNC from source
RUN curl -L "https://github.com/novnc/noVNC/archive/refs/tags/v1.4.0.tar.gz" | tar -xz -C /usr/local/ && \
    ln -s /usr/local/noVNC-1.4.0/vnc.html /usr/local/noVNC-1.4.0/index.html

# Create a non-root user 'agent'
RUN useradd -m -s /bin/bash agent && \
    echo "agent:agent" | chpasswd && \
    adduser agent sudo

# Set up home directory and copy agent files
WORKDIR /home/agent
COPY --chown=agent:agent ../agent ./agent
RUN pip3 install -r agent/requirements.txt --no-cache-dir

# Copy start script and make it executable
COPY docker/start.sh /home/agent/start.sh
RUN chown agent:agent /home/agent/start.sh && chmod +x /home/agent/start.sh

# Expose VNC and noVNC ports
EXPOSE 5900
EXPOSE 6080

# Switch to agent user
USER agent
WORKDIR /home/agent

# Set the entrypoint
ENTRYPOINT ["/home/agent/start.sh"] 