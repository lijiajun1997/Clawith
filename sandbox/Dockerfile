# clawith-sandbox: 独立代码执行沙箱
# 基于 nikolaik/python-nodejs (Python 3.12 + Node.js 22)
FROM nikolaik/python-nodejs:python3.12-nodejs22-slim

# 国内镜像加速
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list 2>/dev/null || true

# 安装系统工具 + OfficeCLI 依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl libicu-dev && \
    rm -rf /var/lib/apt/lists/*

# 安装 OfficeCLI（AI 原生 Office 文档 CLI — .docx/.xlsx/.pptx）
RUN curl -fsSL https://raw.githubusercontent.com/iOfficeAI/OfficeCLI/main/install.sh | bash && \
    mv /root/.local/bin/officecli /usr/local/bin/officecli && \
    chmod +x /usr/local/bin/officecli || \
    echo "[WARN] OfficeCLI install skipped — will retry at runtime if needed"

# 预配置 OfficeCLI：关闭自动更新（避免每次调用检查网络）
RUN mkdir -p /home/pn/.officecli && \
    echo '{"autoUpdate":false,"log":false}' > /home/pn/.officecli/config.json && \
    chown -R pn:pn /home/pn/.officecli

# pip 镜像加速
ARG CLAWITH_PIP_INDEX_URL=https://pypi.org/simple
ARG CLAWITH_PIP_TRUSTED_HOST=pypi.org

# 安装 Python 依赖（先拷贝 requirements 利用缓存）
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir \
    --index-url "${CLAWITH_PIP_INDEX_URL}" \
    --trusted-host "${CLAWITH_PIP_TRUSTED_HOST}" \
    -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# 创建工作目录
RUN mkdir -p /data/shared-deps/pip /data/shared-deps/node_modules /data/agents && \
    chown -R pn:pn /data

# 拷贝服务代码
COPY service.py /app/service.py

WORKDIR /app

EXPOSE 8888

USER pn

CMD ["python3", "-m", "uvicorn", "service:app", "--host", "0.0.0.0", "--port", "8888"]
