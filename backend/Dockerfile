# ─── Backend Dockerfile (Optimized) ─────────────────────
# Multi-stage: deps → production
FROM python:3.12-slim AS deps

WORKDIR /app
# 清除可能存在的代理配置，避免 apt 连接失败
RUN rm -f /etc/apt/apt.conf.d/*proxy* 2>/dev/null || true && \
    unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY && \
    apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# 配置 pip 使用清华镜像（避免代理问题）
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn

COPY pyproject.toml ./
ARG CLAWITH_PIP_INDEX_URL
ARG CLAWITH_PIP_TRUSTED_HOST
# 清除代理环境变量，避免 pip 连接代理失败
ENV http_proxy= \
    https_proxy= \
    HTTP_PROXY= \
    HTTPS_PROXY= \
    NO_PROXY=*
RUN if [ -n "$CLAWITH_PIP_INDEX_URL" ] && [ -n "$CLAWITH_PIP_TRUSTED_HOST" ]; then \
        pip install --no-cache-dir --proxy="" --index-url "$CLAWITH_PIP_INDEX_URL" --trusted-host "$CLAWITH_PIP_TRUSTED_HOST" .; \
    elif [ -n "$CLAWITH_PIP_INDEX_URL" ]; then \
        pip install --no-cache-dir --proxy="" --index-url "$CLAWITH_PIP_INDEX_URL" .; \
    else \
        pip install --no-cache-dir --proxy="" .; \
    fi

# ─── Production ─────────────────────────────────────────
FROM python:3.12-slim AS production

WORKDIR /app
# 清除可能存在的代理配置，避免 apt 连接失败
RUN rm -f /etc/apt/apt.conf.d/*proxy* 2>/dev/null || true && \
    unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY && \
    apt-get update && \
    apt-get install -y --no-install-recommends libpq5 curl shadowsocks-libev gosu && \
    rm -rf /var/lib/apt/lists/*

# Copy installed packages from deps stage
COPY --from=deps /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY --from=deps /usr/local/bin/ /usr/local/bin/

# Copy application code
COPY . .

# ═══════════════════════════════════════════════════════════
# 配置 pip 全局镜像源（清华镜像）和 Skill 依赖目录
# ═══════════════════════════════════════════════════════════

# 创建全局 Skill 依赖目录
RUN mkdir -p /data/skill_packages && \
    chmod 777 /data/skill_packages

# 配置 pip 全局镜像源（清华镜像）
RUN mkdir -p /etc/pip && \
    echo "[global]" > /etc/pip/pip.conf && \
    echo "index-url = https://pypi.tuna.tsinghua.edu.cn/simple" >> /etc/pip/pip.conf && \
    echo "trusted-host = pypi.tuna.tsinghua.edu.cn" >> /etc/pip/pip.conf

# ═══════════════════════════════════════════════════════════

RUN useradd --create-home clawith && \
    mkdir -p /data/agents && \
    chmod +x /app/entrypoint.sh && \
    chown -R clawith:clawith /app /data

# Note: USER is removed to allow entrypoint.sh to fix permissions of mounted volumes
# at runtime. The entrypoint script will drop privileges to 'clawith' after fixing permissions.

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

EXPOSE 8000
# entrypoint.sh runs `alembic upgrade head` then `uvicorn`
ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]
