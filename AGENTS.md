# AGENTS.md — 任何 AI agent 打开本仓库前请遵守

本文件定义 **仓库级硬约束**，与 IDE、模型、操作系统无关。
违反任何一条都可能导致部署失败、数据丢失或安全漏洞。

## 1. 路径与权限（最容易踩坑）

- **所有数据持久化只能放 `data/` 目录**，不能放源码根目录：
  - SQLite → `data/geo_data.db`
  - RAG 知识库 → `data/knowledge_base/`
  - 非敏感配置 → `data/config.json`
  - 源码根目录 `/app` 是 `root:root` bind mount，容器内非 root 用户 **没有写权限**
- **所有路径必须用绝对路径**，禁止相对 CWD 字符串：
  ```python
  # ✅ 正确
  BASE = Path(__file__).resolve().parent
  DATA_DIR = BASE / "data"
  storage = DataStorage(db_path=str(DATA_DIR / "geo_data.db"))

  # ❌ 错误（CWD 一变就炸）
  storage = DataStorage(db_path="data/geo_data.db")
  ```
- **SQLite connect 前必须确保父目录存在**：
  ```python
  db_dir = Path(db_path).parent
  db_dir.mkdir(parents=True, exist_ok=True)
  ```

## 2. Docker / Compose 硬约束

- **禁止使用 `docker compose down -v --rmi local`**：
  - `--rmi local` 会删除宿主机上 **所有** local label 镜像，可能影响同机器上别的应用
  - 清理本项目镜像请用：`docker rmi <image-name>`
- **compose 的 service key / volume key / network key 不能变量化**（compose 规范限制）：
  - ✅ 可以变量化：`container_name`、`image`、`ports`、volumes 的 `name:`、networks 的 `name:`
  - ❌ 不能变量化：`services:` 下的 key、`volumes:` 下的 key、`networks:` 下的 key
- **`pull_policy` 只能写在 service 顶层**，不能嵌在 `build:` 下面
- **Compose `network.external.name` 正确写法**（已弃用 `external: {name: ...}`）：
  ```yaml
  networks:
    my_net:
      external: true
      name: ${NETWORK_NAME:-1panel-network}
  ```

## 3. Streamlit + OpenResty 反代三件套

如果在反向代理后部署 Streamlit（8501 端口），反代必须：

```nginx
location / {
    proxy_pass         http://127.0.0.1:8501;
    proxy_http_version 1.1;
    # WebSocket / SSE 升级头
    proxy_set_header Upgrade    $http_upgrade;
    proxy_set_header Connection "Upgrade";
    proxy_set_header Host              $host;
    proxy_set_header X-Real-IP         $remote_addr;
    proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    # SSE 长连接必需
    proxy_buffering off;
    proxy_cache         off;
    proxy_read_timeout  86400s;
    proxy_send_timeout  86400s;
}
# 🔴 严禁开启 http2 on —— 它会把 HTTP/1.1 Upgrade 转成 HTTP/2 Extended CONNECT，
#    Streamlit 识别不到 → WebSocket onerror
```

## 4. SQLite 安全

- **Streamlit 单线程 rerun**，`sqlite3.connect(..., check_same_thread=True)` 就够了
- `check_same_thread=False` 会在多 session 并发写时产生 race condition → `database is locked`
- 用 try/except 包好 connect，异常要记录 **绝对路径** 方便排错

## 5. 安全（公开仓库必须遵守）

- **`.streamlit/secrets.toml` 里放 API Keys**，永远不要硬编码在 `.py` / `.toml` / 环境变量示例文件里
- **config.json（非敏感配置）放 `data/` 下**，已在 .gitignore，不要手动 `git add -f`
- **所有 JSON / DB / secrets 文件都在 .gitignore**（已包含 `*.db`、`knowledge_base/`、`secrets.toml`、`.env*`）
- **生产环境必须开启**：`STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=true`
  - 只有反代完全同源、且服务端口未暴露公网时才能设 false

## 6. 依赖安装（国内环境）

- **pypi 清华源最稳**：`https://pypi.tuna.tsinghua.edu.cn/simple`
- npmmirror / 中科大 / 阿里云源在某些 wheel 包上会返回 404
- **Python slim 镜像没有 wget/curl**，健康检查只能用 python 标准库 `urllib`

## 7. 代码风格

- 关键路径（LLM 调用、SQLite 写、config 持久化）的异常 **不要静默 `except: pass`**
  - 应该 `logger.error(...)` + `st.error(...)` 抛给用户
- 知识库 RAG 当前是关键词匹配（非 embedding），中文效果有限。如需升级：bge-small-zh-v1.5 + faiss

## 8. 项目常用命令（Makefile）

```bash
make up          # 启动，本地有镜像就秒过
make restart     # 重启容器（源码 bind mount 立即生效）
make rebuild     # 改了 requirements.txt 后重建镜像
make force-pull  # 强制拉最新基础镜像 + 无缓存重建
make wheelhouse  # 用 python 临时容器下载依赖到本地离线缓存
make shell       # 进容器调试
make logs        # 实时看 Streamlit 日志
make info        # 显示 compose 解析出的生效值
make copy-secrets # secrets.toml.example → secrets.toml
make clean       # 停容器 + 删本项目镜像（不影响其他项目）
```
