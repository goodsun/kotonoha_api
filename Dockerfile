FROM runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends git curl zstd openssh-server && \
    rm -rf /var/lib/apt/lists/*

# Configure sshd
RUN mkdir -p /var/run/sshd && \
    sed -i 's/#PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config && \
    sed -i 's/#PubkeyAuthentication.*/PubkeyAuthentication yes/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config && \
    echo "PermitEmptyPasswords no" >> /etc/ssh/sshd_config && \
    ssh-keygen -A

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Copy files
COPY entrypoint.sh /entrypoint.sh
COPY Modelfile /Modelfile
RUN chmod +x /entrypoint.sh

ENV MODEL_NAME=kotonoha
ENV OLLAMA_HOST=0.0.0.0:11434

EXPOSE 11434 22

ENTRYPOINT ["/entrypoint.sh"]
