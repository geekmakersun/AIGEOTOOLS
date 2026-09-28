# ============================================================================
# GEO 智能内容优化平台 · 生产镜像（多阶段构建，镜像小、可二次开发）
#
# ★★★ 有就复用，没有才安装（三层缓存） ★★★
#   1) Docker 层缓存：COPY requirements.txt 之后才 RUN pip install ——
#      requirements.txt 没变就整条层跳过
#   2) 本地 wheelhouse 复用：
#      ./wheelhouse/ 目录里预先放好 .whl / .tar.gz，构建时 --find-links 优先读这里
#      （首次 make wheelhouse 会帮你下载到本地，后续全离线构建）
#   3) 宿主 pip 镜像：PIP_INDEX_URL 指向清华源（国内最快）
# ============================================================================

# ---------- 阶段 1：构建 ----------
FROM python:3.11-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # pip 国内镜像（清华源；npmmirror 在某些包上返回 404，已弃用）
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    PIP_NO_CACHE_DIR=0

WORKDIR /build

# wheelhouse/ 已经在 .dockerignore 里排除，不会进 build context。
# pip 直接从 PIP_INDEX_URL 联网安装；离线构建请先 make wheelhouse，
# 然后手动把 wheelhouse/ 暂移出 .dockerignore 再 build。

# 只拷贝 requirements.txt 触发缓存：文件没变 → 整个 pip install 层跳过
COPY requirements.txt .

# 安装依赖到独立的虚拟环境，后续 runner 阶段直接复制 venv
# --require-hashes 强制校验 wheel 的 sha256 与 requirements.txt 里的 --hash 行完全一致，
# 防止依赖替换攻击（需要 make lock / make wheelhouse 先把 hash 填上）
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip setuptools wheel \
    && /opt/venv/bin/pip install \
        --require-hashes \
        -r requirements.txt

# ---------- 阶段 2：运行时 ----------
FROM python:3.11-slim-bookworm AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_ENABLE_CORS=false \
    STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# 非 root 用户跑服务（降低权限风险）
# 注意：/app 后续会被 compose bind mount 覆盖，这里的 mkdir/chown 会失效。
# 所以下面显式为 data 目录做 geoapp 权限，作为 bind mount 宿主权限不对时的兜底。
RUN groupadd -r geoapp && useradd -r -g geoapp -u 1000 geoapp \
    && mkdir -p /app /app/.streamlit /app/data /app/data/knowledge_base \
    && chown -R geoapp:geoapp /app

# 从 builder 阶段复制 venv
COPY --from=builder /opt/venv /opt/venv

# 拷贝源码（注意：docker-compose 会用 volume 把 /opt/1panel/www/源代码/AIGEOTOOLS
#  覆盖到容器内的 /app，这样二次开发时改宿主文件即可热生效）
WORKDIR /app
COPY --chown=geoapp:geoapp . .

USER geoapp

EXPOSE 8501

# 健康检查：用容器内已有的 python 标准库，不依赖 wget/curl（slim 镜像里没有）
HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health').read() else 1)"

ENTRYPOINT ["streamlit", "run", "geo_tool.py", \
            "--server.port=8501", \
            "--server.address=0.0.0.0"]
