from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from .config import DATABASE_URL, settings


def _engine_kwargs() -> dict:
    """按方言拼装 engine 参数。

    SQLite（aiosqlite）不接受 pool_size / max_overflow —— 它用的是
    ``StaticPool``/``NullPool`` 家族，传入会直接 TypeError。
    因此连接池参数只对 PostgreSQL 等真正的网络数据库生效。
    """
    kwargs: dict = {"echo": settings.db_echo, "future": True}
    if not settings.is_sqlite:
        kwargs["pool_size"] = settings.db_pool_size
        kwargs["max_overflow"] = settings.db_max_overflow
        # 回收长连接，避免云数据库侧空闲断连后拿到坏连接
        kwargs["pool_pre_ping"] = True
        kwargs["pool_recycle"] = 1800
    return kwargs


engine = create_async_engine(DATABASE_URL, **_engine_kwargs())
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@event.listens_for(engine.sync_engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    """SQLite 默认 foreign_keys=OFF，导致 ondelete="CASCADE" 在 DB 层不生效。
    仅对 SQLite 生效；PostgreSQL 天然强制外键，无需处理。

    注意：不能用 try/except 屏蔽异常——asyncpg 的同步游标会把
    ``PRAGMA foreign_keys=ON`` 真的发往 PostgreSQL 服务端，触发语法错误并使
    当前事务 abort，进而导致后续所有语句报 InFailedSQLTransactionError。
    因此必须按方言显式跳过非 SQLite 连接。"""
    if engine.dialect.name != "sqlite":
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class Base(DeclarativeBase):
    pass


async def get_db():
    async with SessionLocal() as session:
        yield session


# 初始演示账号（仅在用户表为空时创建一次）
SEED_USERNAME = "demo"
SEED_PASSWORD = "reach2026"
SEED_CATEGORIES = [
    {"name": "工作", "color": "#3B82F6", "icon": "💼", "sort_order": 0},
    {"name": "健康", "color": "#10B981", "icon": "💪", "sort_order": 1},
    {"name": "学习", "color": "#06B6D4", "icon": "📚", "sort_order": 2},
    {"name": "生活", "color": "#F59E0B", "icon": "🏠", "sort_order": 3},
]


async def seed_demo_account():
    """数据库无用户时，自动创建一个初始账号并预置四个维度。
    发布版（默认 SQLite）默认开启；PostgreSQL 版需 SEED_DEMO_ACCOUNT=1 才开启。"""
    from sqlalchemy import select

    from .config import DATABASE_URL, SEED_DEMO_ACCOUNT
    from .models import Category, User
    from .security import hash_password

    enabled = SEED_DEMO_ACCOUNT or DATABASE_URL.startswith("sqlite")
    if not enabled:
        return

    async with SessionLocal() as session:
        existing = await session.scalar(select(User).limit(1))
        if existing:
            return  # 已有用户，不再重复创建

        demo = User(
            username=SEED_USERNAME,
            hashed_password=hash_password(SEED_PASSWORD),
        )
        session.add(demo)
        await session.flush()
        for c in SEED_CATEGORIES:
            session.add(Category(user_id=demo.id, **c))
        await session.commit()


# 内置记录模板（全局，user_id 为 NULL，用户不可改不可删）
# 设计原则：
# - 拒绝【✅】【❌】这类指令式填空，避免把日记变成「答题卡」；
# - 参考 Day One / Journey / Apple Journal：用氛围头部 + 开放式引导语
#   作为写作起点，正文留足自由空间；
# - 工作 / 读书笔记保留最小必要结构，但用问题或短语引导，而非表格。
PRESET_TEMPLATES = [
    # 个人日记 —— 情绪与氛围优先
    {"type": "diary", "name": "每日心情日记", "icon": "🌤️", "content": ""},
    {"type": "diary", "name": "感恩日记", "icon": "🙏", "content": "今天让我心存感激的一件事：\n\n"},
    {"type": "diary", "name": "自由书写", "icon": "✍️", "content": ""},
    # 工作日志 —— 轻结构，问题引导
    {"type": "worklog", "name": "工作日报", "icon": "💼", "content": "今天完成了什么？明天重点推进什么？\n\n"},
    {"type": "worklog", "name": "周报", "icon": "📈", "content": "本周最重要的进展与下周打算：\n\n"},
    {"type": "worklog", "name": "会议记录", "icon": "🗒️", "content": "本次会议的关键结论与待办：\n\n"},
    # 读书笔记 —— 卡片式轻引导
    {"type": "note", "name": "读书卡片", "icon": "📚", "content": "摘录一段打动你的文字，并写下你的想法：\n\n"},
    {"type": "note", "name": "金句摘抄", "icon": "💡", "content": "一句话与一点思考：\n\n"},
    {"type": "note", "name": "读后感", "icon": "📝", "content": "这本书带给你最重要的启发是什么？\n\n"},
]


async def seed_preset_templates():
    """内置模板：按 name 幂等更新（已存在则更新内容/图标，不存在则插入），
    并清理 PRESET_TEMPLATES 中已移除的旧预设模板，保持模板列表干净。"""
    from sqlalchemy import delete, select

    from .models import Template

    async with SessionLocal() as session:
        preset_names = {t["name"] for t in PRESET_TEMPLATES}

        # 同步当前预设
        for t in PRESET_TEMPLATES:
            existing = await session.scalar(
                select(Template).where(
                    Template.is_preset == True,  # noqa: E712
                    Template.name == t["name"],
                )
            )
            if existing:
                existing.type = t["type"]
                existing.icon = t["icon"]
                existing.content = t["content"]
            else:
                session.add(
                    Template(
                        user_id=None,
                        is_preset=True,
                        type=t["type"],
                        name=t["name"],
                        icon=t["icon"],
                        content=t["content"],
                    )
                )

        # 删除已废弃的旧预设（Record 表不保留 template_id 外键，可安全删除）
        await session.execute(
            delete(Template).where(
                Template.is_preset == True,  # noqa: E712
                Template.name.notin_(preset_names),
            )
        )
        await session.commit()


async def _run_migrations():
    """Alembic 迁移（事件循环安全，可在 pytest-asyncio 等已运行 loop 中调用）：

    - 全新库（无 users 表）：upgrade 到 head，建表并写入版本；
    - 手写 migrate 时代的旧库（已有 users 表）：仅 stamp head，不重复建表。

    不走 `alembic.command.upgrade/stamp`，因为它们内部会 `asyncio.run()`，
    在已运行的事件循环里会抛 RuntimeError；这里改用 EnvironmentContext 在
    `conn.run_sync` 提供的同步连接上直接执行，天然兼容当前 loop。
    后续 schema 变更统一走 `alembic revision --autogenerate` + `alembic upgrade head`。"""
    from pathlib import Path

    from alembic import script as alembic_script
    from alembic.config import Config
    from alembic.runtime.environment import EnvironmentContext
    from sqlalchemy import inspect as sa_inspect

    backend_dir = Path(__file__).resolve().parent.parent
    cfg = Config(str(backend_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
    cfg.set_main_option("path_separator", "os")
    script_dir = alembic_script.ScriptDirectory.from_config(cfg)

    def _do(connection):
        tables = set(sa_inspect(connection).get_table_names())
        from sqlalchemy import text

        if "users" in tables:
            # 既有数据库：
            # 1) 确保 alembic_version 表存在；
            # 2) 若版本表为空（手写 migrate 时代的旧库 / 从未戳记过），先把版本
            #    戳记到 baseline 根，使后续 `upgrade head` 仅执行增量迁移
            #    （如 parent_id），而不会针对已存在的表重跑 baseline 的
            #    CREATE TABLE（否则会报 "table already exists"）。
            connection.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS alembic_version ("
                    "version_num VARCHAR(32) NOT NULL, PRIMARY KEY (version_num))"
                )
            )
            cnt = connection.execute(text("SELECT COUNT(*) FROM alembic_version")).scalar() or 0
            if cnt == 0:
                root = _find_root(script_dir)
                connection.execute(
                    text("INSERT INTO alembic_version (version_num) VALUES (:v)"),
                    {"v": root.revision},
                )

        # 新库与既有库统一：升级到 head。
        # - 新库：从 baseline 起建全部表；
        # - 既有库：仅执行尚未应用的增量迁移（已到 head 则为空操作）。
        def _fn(rev, context):
            return context.script._upgrade_revs("head", rev)

        ctx = EnvironmentContext(cfg, script_dir)
        ctx.configure(connection=connection, fn=_fn, target_metadata=Base.metadata)
        with ctx.begin_transaction():
            ctx.run_migrations()

    async with engine.begin() as conn:
        await conn.run_sync(_do)


def _find_root(script_dir):
    """返回无 down_revision 的根迁移（即 baseline）。"""
    for r in script_dir.walk_revisions():
        if r.down_revision is None:
            return r
    raise RuntimeError("Alembic: 未找到根迁移（baseline）")


async def init_db():
    # 导入模型以确保注册到 Base.metadata（Alembic env.py 亦依赖）
    from . import models  # noqa: F401

    await _run_migrations()
    await seed_demo_account()
    await seed_preset_templates()
