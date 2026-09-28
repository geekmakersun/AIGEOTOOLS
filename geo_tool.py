import streamlit as st
from pathlib import Path
import json
from typing import Optional
from modules.data_storage import DataStorage
from modules.keyword_tool import KeywordTool
from modules.roi_analyzer import ROIAnalyzer
from modules.knowledge_base import KnowledgeBase
from modules.ui import (
    tab_keywords,
    tab_autowrite,
    tab_optimize,
    tab_validation,
    tab_history,
    tab_reports,
    tab_workflow,
    tab_resources,
    tab_platform_sync,
    tab_config_optimizer,
)
from modules.ui.tab_knowledge import render_tab_knowledge
from modules.ui.state import ss_init, init_session_state
from modules.ui.theme import inject_global_theme

APP_TITLE = "GEO 智能内容优化平台"

# ------------------- 页面配置 & 极简美学 CSS（产品级精修，仍然克制） -------------------
st.set_page_config(page_title="GEO 智能内容优化平台", layout="wide", initial_sidebar_state="expanded")

inject_global_theme()
init_session_state()
st.title(APP_TITLE)

st.caption("🚀 AI 驱动的品牌内容策略 · 让您的品牌在 AI 对话中脱颖而出")

# ------------------- 基础路径（统一用绝对路径，不依赖 CWD）--------------------
# 容器里 WORKDIR=/app 且 ./ 被 bind mount 覆盖；直接算相对 __file__ 的绝对路径
# 就不怕 Streamlit 切换目录、也不怕 python geo_tool.py 直接跑
BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ------------------- 初始化数据存储（SQLite） -------------------
# SQLite 文件放在 data/ 下（compose bind mount 已授权宿主 chown 1000:1000）
storage = DataStorage(storage_type="sqlite", db_path=str(DATA_DIR / "geo_data.db"))

# ------------------- 初始化知识库（RAG） -------------------
# 同上：data/knowledge_base/ 已在容器内可写
kb = KnowledgeBase(storage_path=str(DATA_DIR / "knowledge_base"))

# ------------------- 成本记录辅助函数 -------------------
def estimate_tokens(text: str) -> int:
    """估算文本的 token 数量：中文约 1.5 字符 = 1 token，英文约 4 字符 = 1 token"""
    if not text:
        return 0
    chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
    other_chars = len(text) - chinese_chars
    estimated_tokens = int(chinese_chars / 1.5 + other_chars / 4)
    return max(estimated_tokens, len(text) // 4)

def record_api_cost(operation_type: str, provider: str, model: str, input_text: str, output_text: str, keyword: Optional[str] = None, platform: Optional[str] = None, brand: Optional[str] = None):
    """记录 API 调用成本"""
    try:
        roi_analyzer = ROIAnalyzer()
        input_tokens = estimate_tokens(input_text)
        output_tokens = estimate_tokens(output_text)
        total_tokens = input_tokens + output_tokens
        cost_usd, cost_cny = roi_analyzer.calculate_cost(provider, model, input_tokens, output_tokens)
        storage.save_api_call(operation_type=operation_type, provider=provider, model=model, input_tokens=input_tokens, output_tokens=output_tokens, total_tokens=total_tokens, cost_usd=cost_usd, cost_cny=cost_cny, keyword=keyword, platform=platform, brand=brand)
    except Exception as e:
        import logging
        logging.warning(f"记录 API 成本失败: {e}")

with st.expander("📖 关于 GEO（Generative Engine Optimization）", expanded=False):
    st.markdown("""
### 🎯 什么是 GEO？

**GEO（Generative Engine Optimization，生成式引擎优化）** 是针对 AI 搜索引擎的内容优化策略。

传统 SEO 优化的是 Google、百度等传统搜索引擎的排名；而 GEO 优化的是 ChatGPT、Perplexity、Google SGE 等 AI 搜索引擎在回答用户问题时，**是否会引用您的品牌和内容**。

### 💡 为什么需要 GEO？

当用户向 AI 提问时（例如"最好的 XX 软件是什么？"），AI 会从互联网内容中检索信息并生成回答。如果您的品牌没有出现在 AI 可检索的高质量内容中，就会在 AI 时代失去曝光机会。

**GEO 的目标**：让您的品牌在 AI 回答中被优先、准确、可信地提及。

---

### 🔄 GEO 优化工作流

本工具提供完整的 GEO 优化闭环：

| 阶段 | 功能 | 说明 |
|------|------|------|
| 1️⃣ 关键词策略 | 关键词蒸馏 | 生成针对 AI 搜索的口语化、长尾关键词 |
| 2️⃣ 内容创作 | 自动创作 | 基于知识库生成结构化、专业的内容 |
| 3️⃣ 内容优化 | 文章优化 | E-E-A-T 强化、事实密度增强、Schema 生成 |
| 4️⃣ 效果验证 | 多模型验证 | 用多个 AI 模型验证品牌是否被提及 |
| 5️⃣ 数据分析 | AI 数据报表 | 提及率趋势、ROI 分析、竞品对比 |
| 6️⃣ 内容分发 | 平台同步 | 多平台发布，扩大 AI 可检索内容 |

---

### 📊 GEO 核心指标

| 指标 | 说明 |
|------|------|
| **品牌提及率** | AI 回答中提及品牌的频率 |
| **E-E-A-T 评分** | 专业性、经验性、权威性、可信度 |
| **事实密度** | 内容中可验证信息的密度 |
| **引用位置** | 品牌在 AI 回答中的位置（前 1/3 优先） |

---

### 🌐 支持平台

**内容发布平台（20+）**：知乎、小红书、CSDN、B站、GitHub、微信公众号等

**AI 验证平台（7）**：DeepSeek、OpenAI、通义千问、Groq、Moonshot、豆包、文心一言

---

### 📚 更多资源

- [GEO 学术论文](https://arxiv.org/abs/2311.09735) - GEO 原始研究
- [项目文档](DOCS.md) - 完整功能文档
- [快速开始](docs/guides/QUICK_START_GUIDE.md) - 新手入门指南
""")

def load_default_cfg():
    """
    从项目 data/config.json 读取默认配置，如果不存在则使用内置默认值。
    敏感信息（API Keys）优先从 .streamlit/secrets.toml 读取。
    """
    base_cfg = {
        "gen_provider": "DeepSeek",
        "gen_api_key": "",
        "verify_providers": ["DeepSeek"],
        "verify_keys": {
            "DeepSeek": ""
        },
        "tongyi_wanxiang_api_key": "",
        "deepseek_image_api_key": "",
        "default_brand": "",
        "temperature": 0.7,
    }

    # 从 data/config.json 读取非敏感配置（和 save_cfg_to_file 路径一致）
    config_path = DATA_DIR / "config.json"
    if config_path.exists():
        try:
            with config_path.open("r", encoding="utf-8") as f:
                file_cfg = json.load(f)
            if isinstance(file_cfg, dict):
                base_cfg.update(file_cfg)
        except Exception as e:
            import logging
            logging.warning(f"配置文件加载失败: {e}")

    # 从 st.secrets 读取敏感信息（优先级更高）
    try:
        if hasattr(st, 'secrets') and st.secrets:
            # 读取 API Keys
            if "api_keys" in st.secrets:
                api_keys = st.secrets["api_keys"]
                if "deepseek" in api_keys and api_keys["deepseek"]:
                    base_cfg["gen_api_key"] = api_keys["deepseek"]
                    base_cfg["verify_keys"]["DeepSeek"] = api_keys["deepseek"]
                if "tongyi_wanxiang" in api_keys and api_keys["tongyi_wanxiang"]:
                    base_cfg["tongyi_wanxiang_api_key"] = api_keys["tongyi_wanxiang"]
            
            # 读取应用配置（如果存在）
            if "app_config" in st.secrets:
                app_config = st.secrets["app_config"]
                for key in ["brand", "advantages", "competitors", "temperature"]:
                    if key in app_config and app_config[key]:
                        base_cfg[key] = app_config[key]
    except FileNotFoundError:
        # secrets.toml 不存在时静默忽略，用户可通过侧边栏配置
        pass
    except Exception as e:
        import logging
        logging.warning(f"读取 secrets.toml 失败: {e}")

    return base_cfg


def save_cfg_to_file(cfg: dict) -> None:
    """
    将当前生效的非敏感配置写入本地 config.json。
    敏感信息（API Keys）不会保存到此文件，仅保存到 .streamlit/secrets.toml。
    """
    # config.json 放在 data/ 下，跟 SQLite 放在同一个已授权可写目录；
    # 不能放源码根目录 —— 宿主没写权限（root:root）、容器里 geoapp 写不了
    config_path = DATA_DIR / "config.json"
    try:
        data = {}
        if config_path.exists():
            try:
                with config_path.open("r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    data.update(loaded)
            except Exception as e:
                import logging
                logging.warning(f"读取配置文件失败: {e}")
                data = {}
        
        # 只保存非敏感配置
        sensitive_keys = {"gen_api_key", "verify_keys", "tongyi_wanxiang_api_key"}
        for key in ["gen_provider", "verify_providers", "brand", "advantages", "competitors", "temperature"]:
            if key in cfg:
                data[key] = cfg[key]
        
        with config_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # 提示用户如何保存 API Keys
        if any(key in cfg for key in sensitive_keys):
            try:
                st.info("💡 API Keys 需要在 `.streamlit/secrets.toml` 文件中手动配置。")
            except Exception:
                pass
                
    except Exception as e:
        import logging
        logging.error(f"保存配置文件失败: {e}")
        try:
            st.warning("⚠️ 无法将配置写入本地 config.json，但当前会话已生效。请检查文件权限。")
        except Exception:
            pass


ss_init("cfg", load_default_cfg())

# 模块1：关键词（补充 init_session_state 中未包含的）
ss_init("keyword_tool", KeywordTool())  # 托词工具实例

# 模块2：内容（补充 init_session_state 中未包含的）
ss_init("multimodal_descriptions", {})  # 多模态描述（配图描述、视频脚本等）
ss_init("image_descriptions", [])  # 图片描述列表
ss_init("detail_tab_active", "🎨 增强工具")  # 保存当前激活的详情Tab

# ------------------- 工具函数 -------------------
def validate_cfg(cfg: dict):
    """验证配置完整性，返回 (是否有效, 错误列表)。"""
    errors = []
    warnings = []
    
    if not cfg.get("gen_api_key", "").strip():
        errors.append("生成&优化 LLM 的 API Key 未填写")

    verify_providers = cfg.get("verify_providers", [])
    verify_keys = cfg.get("verify_keys", {})
    if not verify_providers:
        errors.append("至少选择一个验证模型")

    for vp in verify_providers:
        if not verify_keys.get(vp, "").strip():
            errors.append(f"验证模型 {vp} 的 API Key 未填写")
    
    if not cfg.get("brand", "").strip():
        warnings.append("品牌名称未填写（部分功能需要）")
    if not cfg.get("advantages", "").strip():
        warnings.append("核心优势未填写（部分功能需要）")

    return (len(errors) == 0), errors + warnings


def model_defaults(provider: str) -> str:
    from modules.llm_factory import get_default_model
    return get_default_model(provider)


# ------------------- 缓存 LLM 客户端（显著降低“频繁 Loading”） -------------------
@st.cache_resource(show_spinner=False)
def build_llm(provider: str, api_key: str, model: str, temperature: float):
    """
    - 使用 cache_resource 缓存客户端，避免每次 rerun 重建
    - 统一使用 llm_factory 模块构建 LLM
    """
    from modules.llm_factory import build_llm as _build_llm
    return _build_llm(provider, api_key, model, temperature)


# ------------------- 侧边栏：全局配置（分组折叠） -------------------
with st.sidebar:
    st.header("⚙️ 全局配置")
    
    # LLM 配置组
    with st.expander("🤖 LLM 配置", expanded=True):
        PROVIDER_LIST = ["DeepSeek", "OpenAI (GPT)", "Tongyi (通义千问)", "Groq", "Moonshot (Kimi)", "豆包（字节跳动）", "文心一言（百度）"]
        
        gen_provider = st.selectbox(
            "生成&优化 LLM",
            PROVIDER_LIST,
            index=PROVIDER_LIST.index(st.session_state.cfg["gen_provider"]) if st.session_state.cfg["gen_provider"] in PROVIDER_LIST else 0,
            key="sb_gen_provider",
        )
        
        # API Key 输入提示
        api_key_help = ""
        if gen_provider == "豆包（字节跳动）":
            api_key_help = "格式：access_key:secret_key:endpoint_id（用冒号分隔）"
        elif gen_provider == "文心一言（百度）":
            api_key_help = "格式：app_key:app_secret（用冒号分隔）"
        
        gen_api_key = st.text_input(
            f"{gen_provider} API Key（生成&优化用）",
            type="password",
            value=st.session_state.cfg.get("gen_api_key", ""),
            key="sb_gen_api_key",
            help=api_key_help if api_key_help else None,
        )
    
    # 验证配置组
    with st.expander("🔍 验证配置", expanded=False):
        verify_providers = st.multiselect(
            "选择验证模型",
            PROVIDER_LIST,
            default=st.session_state.cfg.get("verify_providers", []),
            key="sb_verify_providers",
        )

        verify_keys = {}
        old_keys = st.session_state.cfg.get("verify_keys", {})
        for vp in verify_providers:
            vp_help = ""
            if vp == "豆包（字节跳动）":
                vp_help = "格式：access_key:secret_key:endpoint_id（用冒号分隔）"
            elif vp == "文心一言（百度）":
                vp_help = "格式：app_key:app_secret（用冒号分隔）"
            
            verify_keys[vp] = st.text_input(
                f"{vp} API Key（验证用）",
                type="password",
                value=old_keys.get(vp, ""),
                key=f"sb_verify_key_{vp}",
                help=vp_help if vp_help else None,
            )

    # 品牌信息组
    with st.expander("🏢 品牌信息", expanded=True):
        brand = st.text_input("主品牌名称", value=st.session_state.cfg.get("brand", ""), key="sb_brand")
        
        advantages = st.text_area(
            "核心优势/卖点（AI专属）",
            value=st.session_state.cfg.get("advantages", ""),
            height=120,
            key="sb_advantages",
        )
        
        competitors = st.text_area(
            "竞品品牌（每行一个）",
            value=st.session_state.cfg.get("competitors", ""),
            height=100,
            key="sb_competitors",
        )

    # 高级设置组
    with st.expander("⚙️ 高级设置", expanded=False):
        temperature = st.slider(
            "生成温度（更稳→更低）",
            0.0,
            1.0,
            float(st.session_state.cfg.get("temperature", 0.7)),
            0.05,
            key="sb_temperature",
        )
        
        tongyi_wanxiang_api_key = st.text_input(
            "通义万相 API Key（图片生成）",
            type="password",
            value=st.session_state.cfg.get("tongyi_wanxiang_api_key", ""),
            key="sb_tongyi_wanxiang_api_key",
            help="阿里云 DashScope API Key，用于生成文章配图。",
        )
    
    # 应用配置按钮
    apply_cfg = st.button("应用配置", use_container_width=True, type="primary")

    if apply_cfg or not st.session_state.cfg_applied:
        # 优先从主 key 读取值（如果使用了临时 key 更新，值已同步到主 key）
        brand_value = st.session_state.get("sb_brand", brand)
        advantages_value = st.session_state.get("sb_advantages", advantages)

        st.session_state.cfg = {
            "gen_provider": gen_provider,
            "gen_api_key": gen_api_key,
            "verify_providers": verify_providers,
            "verify_keys": verify_keys,
            "tongyi_wanxiang_api_key": tongyi_wanxiang_api_key,
            "brand": brand_value,
            "advantages": advantages_value,
            "competitors": competitors,
            "temperature": temperature,
        }

        ok, errs = validate_cfg(st.session_state.cfg)
        st.session_state.cfg_valid = ok
        st.session_state.cfg_errors = errs

        if ok:
            # 仅在配置合法时才写入本地配置文件，并标记为已应用
            save_cfg_to_file(st.session_state.cfg)
            st.session_state.cfg_applied = True
        else:
            st.session_state.cfg_applied = False

    if not st.session_state.cfg_valid:
        with st.container(border=True):
            st.markdown("**⚠️ 完成配置后即可使用全部功能**")
            for err in st.session_state.cfg_errors:
                st.markdown(f"• {err}")
    else:
        with st.container(border=True):
            st.markdown("**✅ 配置已就绪**")
            st.caption("所有功能已解锁，可以开始使用")

    st.markdown("---")
    if st.button("重置全部结果（不删除配置）", use_container_width=True, key="sb_reset_all"):
        st.session_state.keywords = []
        st.session_state.generated_contents = []
        st.session_state.zip_bytes = None
        st.session_state.zip_filename = ""
        st.session_state.optimized_article = ""
        st.session_state.opt_changes = ""
        st.session_state.verify_combined = None
        st.session_state.config_optimization_result = None
        st.session_state.config_hash = None
        st.toast("已重置全部结果。")

    st.caption("闭环：关键词 → 创作 → 优化 → 验证")

cfg = st.session_state.cfg
brand = cfg["brand"]
advantages = cfg["advantages"]
temperature = float(cfg.get("temperature", 0.7))

competitor_list = [c.strip() for c in cfg["competitors"].split("\n") if c.strip()]
_seen = set()
clean_competitors = []
for c in competitor_list:
    cl = c.lower()
    if cl == brand.lower():
        continue
    if cl in _seen:
        continue
    _seen.add(cl)
    clean_competitors.append(c)
competitor_list = clean_competitors

# ------------------- 初始化 LLM（仅在 cfg_valid 时；且 build_llm 已缓存） -------------------
gen_llm = None
verify_llms = {}

if st.session_state.cfg_valid:
    try:
        gen_llm = build_llm(cfg["gen_provider"], cfg["gen_api_key"], model_defaults(cfg["gen_provider"]), temperature)
    except Exception as e:
        st.error(f"生成LLM加载失败：{e}")

    for vp in cfg["verify_providers"]:
        key = cfg["verify_keys"].get(vp, "").strip()
        if not key:
            continue
        try:
            verify_llms[vp] = build_llm(vp, key, model_defaults(vp), temperature)
        except Exception as e:
            st.error(f"{vp}验证LLM加载失败：{e}")

# ------------------- KPI 总览（极简但更像产品） -------------------
k1, k2, k3, k4 = st.columns(4)
k1.metric("关键词", len(st.session_state.keywords), border=True)
k2.metric("内容包", len(st.session_state.generated_contents), border=True)
k3.metric("文章优化", "已生成" if bool(st.session_state.optimized_article) else "未生成", border=True)
k4.metric("验证结果", "已生成" if st.session_state.verify_combined is not None else "未生成", border=True)

st.markdown("---")

# ------------------- 主导航：Tabs（流程更清晰） -------------------
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11 = st.tabs([
    "🎯 关键词蒸馏", 
    "✍️ 自动创作", 
    "🔧 文章优化",
    "✅ 多模型验证",
    "📚 历史记录",
    "📊 AI 数据报表",
    "⚙️ 工作流自动化",
    "📦 GEO 资源库",
    "🔄 平台同步",
    "🛠️ 配置优化助手",
    "📚 品牌知识库"
])

# =======================
# Tab1：关键词蒸馏
# =======================
with tab1:
    tab_keywords.render_tab_keywords(
        storage,
        ss_init,
        gen_llm,
        brand,
        advantages
    )


# =======================
# Tab2：自动创作内容（含批量 ZIP / GitHub 模板）
# =======================
with tab2:
    tab_autowrite.render_tab_autowrite(
        storage,
        ss_init,
        gen_llm,
        brand,
        advantages,
        cfg,
        record_api_cost,
        model_defaults
    )


# =======================
# Tab3：文章优化
# =======================
with tab3:
    tab_optimize.render_tab_optimize(
        storage,
        ss_init,
        gen_llm,
        brand,
        advantages,
        cfg,
        record_api_cost,
        model_defaults,
    )


# =======================
# Tab4：多模型验证 & 竞品对比
# =======================
with tab4:
    tab_validation.render_tab_validation(
        storage,
        ss_init,
        brand,
        advantages,
        competitor_list,
        verify_llms,
        record_api_cost,
        model_defaults,
    )


# =======================
# Tab5：历史记录
# =======================
with tab5:
    tab_history.render_tab_history(storage, brand)


# =======================
# Tab6：AI 数据报表
# =======================
with tab6:
    tab_reports.render_tab_reports(
        storage,
        ss_init,
        gen_llm,
        brand,
        advantages,
        competitor_list,
        verify_llms,
        record_api_cost,
        model_defaults,
    )


# =======================
# Tab7：工作流自动化
# =======================
with tab7:
    tab_workflow.render_tab_workflow(
        storage,
        ss_init,
        gen_llm,
        brand,
        advantages,
        competitor_list,
        verify_llms,
        record_api_cost,
        model_defaults,
    )

# =======================
# Tab8：GEO 资源库
# =======================
with tab8:
    tab_resources.render_tab_resources(storage, brand)


# =======================
# Tab9：平台同步
# =======================
with tab9:
    tab_platform_sync.render_tab_platform_sync(storage, brand)


# =======================
# Tab10：配置优化助手
# =======================
with tab10:
    tab_config_optimizer.render_tab_config_optimizer(
        storage,
        cfg,
        brand,
        advantages,
        competitor_list,
        build_llm,
        model_defaults,
    )


# =======================
# Tab11：品牌知识库（RAG）
# =======================
with tab11:
    render_tab_knowledge(kb)

st.caption("最完整版：GitHub模板 + 真实多模型验证 + 现有文章优化 + RAG知识库 • GEO全闭环，专注AI品牌影响力")
