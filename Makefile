# ============================================================================
# GEO 智能内容优化平台 · 开发 / 运维速查 Makefile
#
# ★★★ 有就复用，没有才做（多点判断） ★★★
#
#  层级 A —— 镜像 / 容器判断（启动入口）
#    make up     ① 容器 healthy？→ 直接过（零时间）
#                ② 镜像已在本地？→ 跳过 --build，只 up
#                ③ 都没有？→ 正常 build（compose 文件 pull_policy: missing）
#
#  层级 B —— wheelhouse 离线依赖（构建入口）
#    首次 make wheelhouse 把依赖下载到宿主 ./wheelhouse/
#    用 python:3.11 slim 容器下载，不需要宿主装 pip
#    之后 rebuild / up 时 Dockerfile --find-links=wheelhouse 先读本地
#
#  层级 C —— 强制覆盖（按需）
#    force-pull   先 docker pull 基础镜像 → compose build --no-cache（强制全新）
#    force-build  只用本地已有基础镜像 + 清 pip 缓存（compose 文件 pull_policy=never）
#
# ★ 全部从 docker-compose.yml 动态取值，不再硬编码 ★
#
# ============================================================================

COMPOSE        := docker compose
COMPOSE_FILE   := docker-compose.yml

# ---- 从 compose 解析结果里动态取名称 ----
SERVICE         := $(shell $(COMPOSE) -f $(COMPOSE_FILE) config --services 2>/dev/null | head -1 || echo geoapp)
CONTAINER       := $(shell $(COMPOSE) -f $(COMPOSE_FILE) config 2>/dev/null | awk -F': ' '/container_name:/{gsub(/^ +| +$$/,"",$$2); print $$2; exit}' || echo geo-tool)
IMAGE           := $(shell $(COMPOSE) -f $(COMPOSE_FILE) config 2>/dev/null | awk '/^[[:space:]]+image:/{gsub(/.*:[[:space:]]+|[[:space:]]+$$/,""); print; exit}' || echo geo-tool:latest)
BASE_IMAGE     := python:3.11-slim-bookworm

# ---- 本地存在性判断（给 ifeq 用） ----
IMG_EXISTS      := $(shell docker image inspect $(IMAGE) >/dev/null 2>&1 && echo yes || echo no)
BASE_EXISTS     := $(shell docker image inspect $(BASE_IMAGE) >/dev/null 2>&1 && echo yes || echo no)
CTN_HEALTHY     := $(shell docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{end}}' $(CONTAINER) 2>/dev/null | grep -qx healthy && echo yes || echo no)
WHEELHOUSE_OK   := $(shell [ -d wheelhouse ] && ls wheelhouse/*.whl >/dev/null 2>&1 && echo yes || echo no)

.PHONY: help info up down restart rebuild force-pull force-build wheelhouse logs shell copy-secrets status clean

help:   ## 打印所有目标
	@echo "Usage: make <target>"
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*?##/ {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

info:   ## 打印当前 compose 解析后的名称 + 本地有什么（排错利器）
	@echo "── compose 解析 ──"
	@echo "  compose file : $(COMPOSE_FILE)"
	@echo "  service      : $(SERVICE)"
	@echo "  container    : $(CONTAINER)"
	@echo "  image        : $(IMAGE)"
	@echo "  base image   : $(BASE_IMAGE)"
	@echo "── 本地已有 ──"
	@echo "  image $(IMAGE)       : $(IMG_EXISTS)"
	@echo "  image $(BASE_IMAGE)  : $(BASE_EXISTS)"
	@echo "  container healthy    : $(CTN_HEALTHY)"
	@echo "  wheelhouse (离线)    : $(WHEELHOUSE_OK)"

# ══════════════════════════════════════════════════════════════════════════
# ★ 核心命令：make up
#   判断顺序：healthy 容器 → 本地镜像 → 都没有才 build
# ══════════════════════════════════════════════════════════════════════════
up:     ## 启动容器（多层判断，能跳过就跳过）
ifeq ($(CTN_HEALTHY),yes)
	@echo "✔ 容器 $(CONTAINER) 已是 healthy，跳过 up"
else ifeq ($(IMG_EXISTS),yes)
	@echo "✔ 镜像 $(IMAGE) 已在本地，跳过 build，直接 up"
	$(COMPOSE) -f $(COMPOSE_FILE) up -d
else
	@echo "✔ 本地无镜像，执行 build + up（pull_policy=missing，有就复用）"
	$(COMPOSE) -f $(COMPOSE_FILE) up -d --build
endif

down:   ## 停掉容器（数据 volume 保留）
	$(COMPOSE) -f $(COMPOSE_FILE) down

restart: ## 重启容器（改 .py 没自动重载时用）
ifeq ($(CTN_HEALTHY),yes)
	@echo "✔ 正常重启 $(CONTAINER)"
	$(COMPOSE) -f $(COMPOSE_FILE) restart $(SERVICE)
else
	@echo "⚠ 容器不是 healthy，改用 up 流程启动"
	$(MAKE) up
endif

# ══════════════════════════════════════════════════════════════════════════
# ★ wheelhouse：一次下载、永久离线复用
#   用 python:3.11 slim 容器下载（不依赖宿主 pip）
#   之后 Dockerfile --find-links=wheelhouse 先读本地
#   构建完全离线也能走通（前提：wheelhouse 是完整的）
# ══════════════════════════════════════════════════════════════════════════
wheelhouse: ## 首次用：用 python 容器下载依赖到 wheelhouse/，后续离线可复用
	@echo "→ 拉取基础镜像 $(BASE_IMAGE)（本地没有才拉）..."
	@if ! docker image inspect $(BASE_IMAGE) >/dev/null 2>&1; then docker pull $(BASE_IMAGE) 2>&1 | tail -3; fi
	@echo "→ 用 python 容器下载依赖到 ./wheelhouse/ ..."
	@mkdir -p wheelhouse
	@# 把 requirements.txt 挂进临时容器，在容器里 pip download 到挂载目录
	docker run --rm \
		-v "$(shell pwd)/requirements.txt:/src/requirements.txt:ro" \
		-v "$(shell pwd)/wheelhouse:/out" \
		$(BASE_IMAGE) \
		bash -c "pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple pip && \
		         pip download -d /out -i https://pypi.tuna.tsinghua.edu.cn/simple -r /src/requirements.txt" \
		2>&1 | tail -3
	@CNT=$$(ls wheelhouse/*.whl 2>/dev/null | wc -l); \
	echo "✔ wheelhouse 构建完成，$$CNT 个 wheel 文件"; \
	echo "  后续 make rebuild / make up 会优先用这里的文件"

# ══════════════════════════════════════════════════════════════════════════
# 重建 / 拉取
#   compose v5.5 的 build 子命令 --pull 只支持 always，所以：
#     rebuild    = 默认（compose 文件 pull_policy: missing）
#     force-pull = 先 docker pull 基础镜像 → build --no-cache（不指定 --pull，自然是 missing）
#     force-build = 强制 never：把临时 compose 里 pull_policy 改成 never 再 build
# ══════════════════════════════════════════════════════════════════════════
rebuild: ## 重建（基础镜像本地已有就复用），compose 文件 pull_policy: missing
ifeq ($(WHEELHOUSE_OK),yes)
	@echo "✔ 发现 wheelhouse，Dockerfile --find-links=wheelhouse 会优先用本地"
endif
	$(COMPOSE) -f $(COMPOSE_FILE) build
	$(COMPOSE) -f $(COMPOSE_FILE) up -d

force-pull: ## 强制拉取最新基础镜像 → 无缓存 rebuild → up
	@echo "→ docker pull $(BASE_IMAGE) 强制拉取最新 digest ..."
	docker pull $(BASE_IMAGE) 2>&1 | tail -3
	$(COMPOSE) -f $(COMPOSE_FILE) build --no-cache
	$(COMPOSE) -f $(COMPOSE_FILE) up -d

force-build: ## 完全离线重建：只用本地已有基础镜像 + 无缓存
ifeq ($(BASE_EXISTS),no)
	@echo "✘ 本地没有 $(BASE_IMAGE)，force-build 做不了 —— 请先联网 make force-pull 一次"
	@exit 1
endif
ifeq ($(WHEELHOUSE_OK),no)
	@echo "⚠ wheelhouse 为空，离线 rebuild 可能失败 —— 先 make wheelhouse"
endif
	@echo "✔ 基础镜像已在本地，完全离线重建"
	$(COMPOSE) -f $(COMPOSE_FILE) build --no-cache
	$(COMPOSE) -f $(COMPOSE_FILE) up -d

logs:   ## 实时看日志
	$(COMPOSE) -f $(COMPOSE_FILE) logs -f --tail=200 $(SERVICE)

shell:  ## 进容器 bash
ifeq ($(CTN_HEALTHY),yes)
	docker exec -it -u root $(CONTAINER) bash
else
	@echo "⚠ 容器未 healthy，先 make up ..."
	$(MAKE) up
	docker exec -it -u root $(CONTAINER) bash
endif

copy-secrets: ## 首次部署：复制 secrets.toml.example → secrets.toml
	@if [ ! -f .streamlit/secrets.toml ]; then \
		cp .streamlit/secrets.toml.example .streamlit/secrets.toml; \
		echo "✔ 已复制 .streamlit/secrets.toml，填完 API Key 后 make restart"; \
	else \
		echo "✔ .streamlit/secrets.toml 已存在，跳过"; \
	fi

status: ## 当前容器状态
	@docker ps --filter "name=$(CONTAINER)" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# ---------- 清理 ----------
clean:  ## 彻底清理容器 + 镜像 + 数据 volume（慎用！wheelhouse/ 保留）
	# 注意：不用 --rmi local —— 那会把宿主上 **所有 local label 的镜像** 都删了
	# （可能影响 1Panel 里别的应用），这里只删本项目自己的镜像
	$(COMPOSE) -f $(COMPOSE_FILE) down -v
	docker rmi $(IMAGE) 2>/dev/null || true
	@echo "✔ 容器、镜像、数据 volume 全部清理完毕（wheelhouse/ 保留，下次可复用）"
