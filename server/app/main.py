import logging
import os

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import init_db
from .ratelimit import RateLimitMiddleware
from .security_headers import SecurityHeadersMiddleware
from .routers import (
    auth,
    calendar_feed,
    categories,
    goals,
    tasks,
    tags,
    stats,
    focus,
    records,
    templates,
    holidays,
    lunar,
    export,
    import_data,
    devices,
    settings as settings_router,
    trash,
)
from .scheduler import start as scheduler_start, stop as scheduler_stop

# 单体部署：前端(React)构建产物放在 server/public，由 FastAPI 静态托管。
# 参照 XIN-Wallet 思路（后端直接托管前端静态资源，单端口单镜像），
# 但保留 Python(FastAPI) + React 技术栈。


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup：日志级别 → 配置自检 → 建库 / 迁移 → seed → 调度器
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    # 把配置风险显式打到日志，自托管用户第一次启动就能看到该改什么
    settings.log_warnings()
    await init_db()
    await _maybe_seed_demo_data()
    scheduler_start()  # 启动后台到期提醒调度器（推送凭证未配置时自动 no-op）
    yield
    scheduler_stop()  # shutdown：取消调度器任务
    # 无持久连接需要显式释放，连接池由 engine 自动回收


async def _maybe_seed_demo_data():
    """按 SEED_DEMO_DATA 开关给 demo 账号灌演示数据。

    播种失败绝不能拖垮启动——演示数据只是锦上添花，
    真出问题时应用仍要能正常提供服务，日志里留痕即可。
    """
    if settings.seed_demo_data not in ("1", "true", "yes", "on", "force"):
        return
    try:
        from scripts.seed_demo_data import seed

        await seed(force=(settings.seed_demo_data == "force"))
    except Exception:  # noqa: BLE001
        logging.getLogger(__name__).exception("演示数据播种失败，已跳过")


app = FastAPI(
    title=settings.app_name, version=settings.app_version, lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
# 登录/注册/改密接口限速（防爆破）。阈值、窗口、受保护路径、Redis 地址
# 全部由配置中心提供（RATE_LIMIT_*），此处不再硬编码。
app.add_middleware(RateLimitMiddleware)
# 安全响应头中间件：为所有响应（含 SPA 静态文件）补充防护头，放在路由注册之前
app.add_middleware(SecurityHeadersMiddleware)

app.include_router(auth.router)
app.include_router(categories.router)
app.include_router(goals.router)
app.include_router(tasks.router)
app.include_router(stats.router)
app.include_router(focus.router)
app.include_router(records.router)
app.include_router(templates.router)
app.include_router(holidays.router)
app.include_router(lunar.router)
app.include_router(tags.router)
app.include_router(export.router)
app.include_router(import_data.router)
app.include_router(devices.router)
app.include_router(settings_router.router)
app.include_router(trash.router)
app.include_router(calendar_feed.router)


@app.get("/health")
async def health(deep: bool = False):
    """健康检查 / 配置自省。

    - ``GET /health`` 轻量探针：只报告进程存活与静态配置，不触库，可高频调用。
    - ``GET /health?deep=1`` 深度探针：额外做一次 ``SELECT 1`` 验证数据库连通性，
      数据库不可用时返回 503，可直接用于容器 healthcheck / 负载均衡摘除。

    输出中的密钥一律脱敏（见 ``Settings.describe``），可安全暴露给内网监控。
    """
    from .scheduler import is_running as scheduler_running

    body = {
        "status": "ok",
        **settings.describe(),
        "scheduler_running": scheduler_running(),
        "config_warnings": settings.warnings(),
    }

    if deep:
        from sqlalchemy import text

        from .database import engine

        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            body["database_status"] = "ok"
        except Exception as exc:  # noqa: BLE001
            body["status"] = "degraded"
            body["database_status"] = "error"
            # 只回错误类型，不回连接串等敏感细节
            body["database_error"] = type(exc).__name__
            return JSONResponse(body, status_code=503)

    return JSONResponse(body)


# ---------------------------------------------------------------------------
# 单体前端托管（生产镜像由 Dockerfile 把 web/dist 拷入 server/public）。
# 无论 server/public 是否存在都注册 catch-all：
#   - 存在时托管静态资源 + SPA history 回退；
#   - 不存在时未知路径返回 404（与「未注册该路由」行为一致）。
# 关键安全点：必须防止 `..` 路径穿越读取 PUBLIC_DIR 之外的文件（见 _spa_catch_all）。
# ---------------------------------------------------------------------------
PUBLIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "public")
PUBLIC_DIR_ABS = os.path.abspath(PUBLIC_DIR)


def _static_candidate_is_safe(full_path: str) -> str | None:
    """把请求路径解析为 PUBLIC_DIR 内的真实文件绝对路径。

    返回安全路径（绝对路径字符串）；若归一化后越出 PUBLIC_DIR（路径穿越）则返回 None。
    用 abspath 归一化 `..` 后再做前缀判定，杜绝读取根目录 / 其他目录下的文件。
    """
    candidate = os.path.abspath(os.path.join(PUBLIC_DIR, full_path))
    # 归一化后必须严格位于 PUBLIC_DIR 之内（或等于 PUBLIC_DIR 本身）
    if candidate == PUBLIC_DIR_ABS or candidate.startswith(PUBLIC_DIR_ABS + os.sep):
        return candidate
    return None


@app.get("/{full_path:path}")
async def _spa_catch_all(full_path: str):
    index = os.path.join(PUBLIC_DIR_ABS, "index.html")
    candidate = _static_candidate_is_safe(full_path)
    if candidate is not None and os.path.isfile(candidate):
        # 1) 命中真实静态文件（JS/CSS/图片等）直接返回
        return FileResponse(candidate)
    # 2) SPA history 路由回退到 index.html（/goals/123 等前端路由）。
    #    越界路径（路径穿越）一律不返回越界文件，统一走此回退或 404。
    if os.path.exists(index):
        return FileResponse(index)
    raise HTTPException(status_code=404, detail="Not found")
