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
SEED_PASSWORD = "reach2024"
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
PRESET_TEMPLATES = [
    # 个人日记 —— 借鉴「三问法 / 感恩练习 / 晨页」等成熟反思框架
    {"type": "diary", "name": "每日心情日记", "icon": "🌤️", "content":
        "【✅ 今天顺利的事】\n- \n- \n\n【❌ 今天不太顺的】\n- \n\n【🔄 明天换个做法】\n- \n"},
    {"type": "diary", "name": "感恩日记", "icon": "🙏", "content":
        "今天值得感恩的三件事：\n1. \n2. \n3. \n\n为什么感恩：\n💡 今天的一件小确幸：\n"},
    {"type": "diary", "name": "自由书写", "icon": "✍️", "content":
        "此时此刻，脑海里浮现的是……\n\n（不评判、不修改、不停笔，想到什么写什么，写满就好。）"},
    # 工作日志 —— 借鉴日报最佳实践：成果 / 计划 / 问题 / 复盘
    {"type": "worklog", "name": "每日工作日报", "icon": "💼", "content":
        "【✅ 今日完成】\n- \n- \n\n【🔄 进行中】\n- \n\n【⚠️ 阻塞 / 风险】\n- \n\n【➡️ 明日计划】\n- \n\n【💡 今日收获 / 复盘】\n- \n"},
    {"type": "worklog", "name": "周报", "icon": "📈", "content":
        "【📌 本周成果】\n- \n- \n\n【🎯 下周重点】\n- \n\n【⚠️ 风险 / 需协调】\n- \n\n【🔍 本周复盘】\n- \n"},
    {"type": "worklog", "name": "会议纪要", "icon": "🗒️", "content":
        "【会议主题】\n【时间 / 地点】\n【参会人】\n\n【✅ 核心决议】\n- \n\n【📋 行动项（事项 / 负责人 / 截止）】\n- 事项：\n  负责人：\n  截止：\n\n【👀 待跟进】\n- \n"},
    # 读书笔记 —— 借鉴康奈尔笔记（笔记 / 线索 / 总结）+ 卡片法「连接与应用」
    {"type": "note", "name": "读书卡片", "icon": "📚", "content":
        "【📒 书中内容 / 笔记】\n（核心论点、案例、数据，用自己的话记）\n\n【❓ 我的提问 / 关键词】\n- \n\n【💡 我的思考 / 关联】\n（它让我想到……、和已有知识有何联系）\n\n【🧩 可以如何应用】\n（在生活 / 工作里怎么用）"},
    {"type": "note", "name": "金句摘抄", "icon": "💡", "content":
        "【原文】\n（逐字摘录，保留标点）\n\n【出处】（书名 · 章节 · 页码）\n【背景】（这句话出现的情境）\n\n【💭 我的感悟】\n【🔗 可迁移到】（哪类问题能用上这句话）"},
    {"type": "note", "name": "读后感", "icon": "📝", "content":
        "【一句话总结】\n【内容概览】（核心脉络 / 主线）\n\n【🌟 最大收获 / 颠覆认知的点】\n【❤️ 喜欢的角色 / 观点】\n【🙋 推荐给谁 & 理由】\n【🚀 我的行动】（读完后打算做的一件事）"},
]


async def seed_preset_templates():
    """内置模板：按 name 幂等更新（已存在则更新内容/图标，不存在则插入）。

    这样修改 PRESET_TEMPLATES 后，老用户重新启动时也会同步到新版模板。"""
    from sqlalchemy import select

    from .models import Template

    async with SessionLocal() as session:
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
