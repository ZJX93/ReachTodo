"""集中配置中心。

设计约束（很关键，改动前请先读）：

1. **零破坏**：历史代码遍布 ``from .config import JWT_SECRET`` 这类模块级常量导入，
   因此本模块在最后仍导出全部同名常量作为 ``settings`` 的别名，既有 import 无需改动。
2. **单一真相源**：所有环境变量的读取、类型转换、默认值、取值范围都收口在
   ``Settings`` 内，不再让 ``ratelimit.py`` 这类模块自己 ``os.getenv``。
3. **可自省**：``settings.describe()`` 供 ``/health`` 输出（自动脱敏），
   ``settings.warnings()`` 在启动时打印生产环境配置风险，便于自托管用户自查。
"""

from __future__ import annotations

import logging
import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("reach.config")

# server/ 目录（本文件位于 server/app/）
BACKEND_DIR = Path(__file__).resolve().parent.parent

APP_NAME = "抵达 Reach API"
APP_VERSION = "0.3.0"

_TRUE = ("1", "true", "yes", "on")


# ---------------------------------------------------------------------------
# 读取原语
# ---------------------------------------------------------------------------
def _str(key: str, default: str = "") -> str:
    return (os.getenv(key) or default).strip()


def _bool(key: str, default: bool = False) -> bool:
    raw = _str(key)
    if not raw:
        return default
    return raw.lower() in _TRUE


def _int(key: str, default: int, *, lo: int | None = None, hi: int | None = None) -> int:
    raw = _str(key)
    try:
        val = int(raw) if raw else default
    except ValueError:
        logger.warning("%s=%r 不是合法整数，回退默认值 %s", key, raw, default)
        val = default
    if lo is not None:
        val = max(lo, val)
    if hi is not None:
        val = min(hi, val)
    return val


def _csv(key: str, default: str = "") -> list[str]:
    return [p.strip() for p in _str(key, default).split(",") if p.strip()]


def _mask(value: str) -> str:
    """脱敏：仅保留首尾各 2 个字符，用于 /health 与日志输出。"""
    if not value:
        return ""
    if len(value) <= 6:
        return "***"
    return f"{value[:2]}***{value[-2:]}"


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Settings:
    # ---- 基础 ----
    app_name: str = APP_NAME
    app_version: str = APP_VERSION
    # dev | prod：prod 下 warnings() 会把「配置不安全」升级为 error 级日志
    env: str = field(default_factory=lambda: _str("APP_ENV", "dev").lower())
    log_level: str = field(default_factory=lambda: _str("LOG_LEVEL", "INFO").upper())
    # 应用默认时区（IANA）。客户端未提供偏好时用它渲染「今天」。
    timezone: str = field(default_factory=lambda: _str("APP_TIMEZONE", "Asia/Shanghai"))

    # ---- 数据库 ----
    database_url: str = field(
        default_factory=lambda: _str(
            "DATABASE_URL",
            f"sqlite+aiosqlite:///{(BACKEND_DIR / 'goalflow.db').as_posix()}",
        )
    )
    db_echo: bool = field(default_factory=lambda: _bool("DB_ECHO", False))
    db_pool_size: int = field(
        default_factory=lambda: _int("DB_POOL_SIZE", 5, lo=1, hi=100)
    )
    db_max_overflow: int = field(
        default_factory=lambda: _int("DB_MAX_OVERFLOW", 10, lo=0, hi=200)
    )

    # ---- 鉴权 ----
    jwt_algorithm: str = field(default_factory=lambda: _str("JWT_ALGORITHM", "HS256"))
    access_token_expire_minutes: int = field(
        default_factory=lambda: _int(
            "ACCESS_TOKEN_EXPIRE_MINUTES", 1440, lo=5, hi=60 * 24 * 90
        )
    )
    password_min_length: int = field(
        default_factory=lambda: _int("PASSWORD_MIN_LENGTH", 6, lo=6, hi=64)
    )

    # ---- CORS ----
    cors_origins: list[str] = field(
        default_factory=lambda: _csv("CORS_ORIGINS", "http://localhost:5173")
    )

    # ---- 限流 ----
    rate_limit_enabled: bool = field(
        default_factory=lambda: _bool("RATE_LIMIT_ENABLED", True)
    )
    rate_limit_max: int = field(
        default_factory=lambda: _int("RATE_LIMIT_MAX", 10, lo=1, hi=10000)
    )
    rate_limit_window: int = field(
        default_factory=lambda: _int("RATE_LIMIT_WINDOW", 60, lo=1, hi=3600)
    )
    rate_limit_paths: list[str] = field(default_factory=lambda: _csv("RATE_LIMIT_PATHS"))
    rate_limit_redis_url: str = field(
        default_factory=lambda: _str("RATE_LIMIT_REDIS_URL")
    )

    # ---- 分页 ----
    page_size_default: int = field(
        default_factory=lambda: _int("PAGE_SIZE_DEFAULT", 100, lo=1, hi=500)
    )
    page_size_max: int = field(
        default_factory=lambda: _int("PAGE_SIZE_MAX", 500, lo=1, hi=2000)
    )

    # ---- 种子数据 ----
    seed_demo_account: bool = field(
        default_factory=lambda: _bool("SEED_DEMO_ACCOUNT", False)
    )
    # "" | "1" | "force"：force 每次启动重建 demo 数据
    seed_demo_data: str = field(
        default_factory=lambda: _str("SEED_DEMO_DATA").lower()
    )

    # ---- 第三方日历数据源 ----
    apihz_id: str = field(default_factory=lambda: _str("APIHZ_ID", "88888888"))
    apihz_key: str = field(default_factory=lambda: _str("APIHZ_KEY", "88888888"))
    lunar_cache_ttl_hours: int = field(
        default_factory=lambda: _int("LUNAR_CACHE_TTL_HOURS", 24, lo=0, hi=24 * 30)
    )
    holiday_api_base: str = field(
        default_factory=lambda: _str(
            "HOLIDAY_API_BASE", "https://api.jiejiariapi.com/v1/holidays"
        )
    )
    upstream_timeout_seconds: int = field(
        default_factory=lambda: _int("UPSTREAM_TIMEOUT_SECONDS", 10, lo=1, hi=120)
    )

    # ---- 提醒调度 ----
    reminder_enabled: bool = field(
        # 兼容旧名 FCM_REMINDER_ENABLED
        default_factory=lambda: _bool(
            "REMINDER_ENABLED", _bool("FCM_REMINDER_ENABLED", True)
        )
    )
    reminder_lead_minutes: int = field(
        default_factory=lambda: _int(
            "REMINDER_LEAD_MINUTES",
            _int("FCM_REMINDER_LEAD_MINUTES", 10, lo=0, hi=60 * 24 * 7),
            lo=0,
            hi=60 * 24 * 7,
        )
    )
    reminder_interval_seconds: int = field(
        default_factory=lambda: _int("REMINDER_INTERVAL_SECONDS", 60, lo=10, hi=3600)
    )
    # 只扫描「到期时刻落在 now ± 该窗口」内的任务，避免每分钟全表扫。
    reminder_scan_window_hours: int = field(
        default_factory=lambda: _int("REMINDER_SCAN_WINDOW_HOURS", 48, lo=1, hi=24 * 30)
    )

    # ---- 推送：FCM（Android with GMS / Web） ----
    fcm_service_account_json: str = field(
        default_factory=lambda: _str("FCM_SERVICE_ACCOUNT_JSON")
    )
    fcm_project_id: str = field(default_factory=lambda: _str("FCM_PROJECT_ID"))
    fcm_client_email: str = field(default_factory=lambda: _str("FCM_CLIENT_EMAIL"))
    fcm_private_key: str = field(default_factory=lambda: _str("FCM_PRIVATE_KEY"))

    # ---- 推送：华为 Push Kit（HarmonyOS / HMS Android） ----
    hms_client_id: str = field(default_factory=lambda: _str("HMS_CLIENT_ID"))
    hms_client_secret: str = field(default_factory=lambda: _str("HMS_CLIENT_SECRET"))
    hms_oauth_url: str = field(
        default_factory=lambda: _str(
            "HMS_OAUTH_URL", "https://oauth-login.cloud.huawei.com/oauth2/v3/token"
        )
    )
    hms_push_url: str = field(
        default_factory=lambda: _str(
            "HMS_PUSH_URL", "https://push-api.cloud.huawei.com/v3/{app_id}/messages:send"
        )
    )
    # HarmonyOS 端点击通知要拉起的 Ability（PushKit clickAction 需要）
    hms_target_ability: str = field(
        default_factory=lambda: _str("HMS_TARGET_ABILITY", "EntryAbility")
    )

    # ---- 功能开关 ----
    feature_trash: bool = field(default_factory=lambda: _bool("FEATURE_TRASH", True))
    feature_ics_feed: bool = field(
        default_factory=lambda: _bool("FEATURE_ICS_FEED", True)
    )
    feature_import: bool = field(default_factory=lambda: _bool("FEATURE_IMPORT", True))
    trash_retention_days: int = field(
        default_factory=lambda: _int("TRASH_RETENTION_DAYS", 30, lo=1, hi=3650)
    )

    # ---- 运行期解析（非环境变量直读） ----
    jwt_secret: str = field(default_factory=lambda: _resolve_jwt_secret())

    # ------------------------------------------------------------------
    @property
    def is_prod(self) -> bool:
        return self.env in ("prod", "production")

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def fcm_configured(self) -> bool:
        if self.fcm_service_account_json and os.path.exists(
            self.fcm_service_account_json
        ):
            return True
        return bool(self.fcm_project_id and self.fcm_client_email and self.fcm_private_key)

    @property
    def hms_configured(self) -> bool:
        return bool(self.hms_client_id and self.hms_client_secret)

    @property
    def push_configured(self) -> bool:
        return self.fcm_configured or self.hms_configured

    def describe(self) -> dict:
        """给 /health 用的自省视图。**任何密钥都必须脱敏后再出现在这里。**"""
        return {
            "app": self.app_name,
            "version": self.app_version,
            "env": self.env,
            "timezone": self.timezone,
            "database": "sqlite" if self.is_sqlite else "postgresql",
            "cors_origins": self.cors_origins,
            "rate_limit": {
                "enabled": self.rate_limit_enabled,
                "max": self.rate_limit_max,
                "window": self.rate_limit_window,
                "backend": "redis" if self.rate_limit_redis_url else "memory",
            },
            "reminder": {
                "enabled": self.reminder_enabled,
                "lead_minutes": self.reminder_lead_minutes,
                "interval_seconds": self.reminder_interval_seconds,
            },
            "push": {
                "fcm": self.fcm_configured,
                "hms": self.hms_configured,
            },
            "features": {
                "trash": self.feature_trash,
                "ics_feed": self.feature_ics_feed,
                "import": self.feature_import,
            },
            "secrets": {
                "jwt_secret": _mask(self.jwt_secret),
                "apihz_id": _mask(self.apihz_id),
            },
        }

    def warnings(self) -> list[str]:
        """返回配置风险清单（生产环境自查用）。"""
        out: list[str] = []
        if not _str("JWT_SECRET"):
            out.append(
                "未显式设置 JWT_SECRET：已使用自动生成的随机密钥。"
                "生产环境请注入强随机值（openssl rand -hex 32），"
                "否则密钥文件泄露即可伪造任意用户令牌。"
            )
        if "*" in self.cors_origins:
            out.append(
                "CORS_ORIGINS 含通配符 '*'，与 allow_credentials=True 组合非法且危险，"
                "请显式列出前端源。"
            )
        if self.apihz_id == "88888888":
            out.append(
                "万年历接口正在使用公共测试账号（APIHZ_ID=88888888），"
                "量大会被限频，请到 https://www.apihz.cn 申请自有账号。"
            )
        if self.reminder_enabled and not self.push_configured:
            out.append(
                "提醒调度器已启用但未配置任何推送通道（FCM / HMS），"
                "云端提醒不会送达；移动端会退化为本机本地提醒。"
            )
        if self.is_prod and self.seed_demo_account:
            out.append("生产环境仍开启 SEED_DEMO_ACCOUNT，会创建弱口令 demo 账号。")
        if self.is_prod and self.is_sqlite:
            out.append("生产环境使用 SQLite：并发写入能力有限，建议改用 PostgreSQL。")
        return out

    def log_warnings(self) -> None:
        for w in self.warnings():
            (logger.error if self.is_prod else logger.warning)("配置提醒：%s", w)


def _resolve_jwt_secret() -> str:
    """解析 JWT 签名密钥。

    - 显式设置 ``JWT_SECRET`` 时优先使用（忽略历史占位值 change-me-in-prod）；
    - 否则在 ``BACKEND_DIR/.jwt_secret`` 持久化一个随机密钥，保证重启后 token 仍有效。
    """
    env = _str("JWT_SECRET")
    if env and env != "change-me-in-prod":
        return env

    secret_file = BACKEND_DIR / ".jwt_secret"
    if secret_file.exists():
        try:
            existing = secret_file.read_text(encoding="utf-8").strip()
            if existing:
                return existing
        except OSError:
            pass

    token = secrets.token_urlsafe(48)
    try:
        secret_file.write_text(token, encoding="utf-8")
        secret_file.chmod(0o600)
        logger.warning(
            "未设置 JWT_SECRET，已自动生成随机密钥并保存到 %s（生产环境请改用环境变量）",
            secret_file,
        )
    except OSError:
        logger.warning("无法持久化 JWT 密钥，本次启动使用临时随机密钥（重启将失效）")
    return token


settings = Settings()

# ---------------------------------------------------------------------------
# 向后兼容别名：历史模块直接 import 这些常量，保持不变。
# 新代码请统一使用 ``from .config import settings``。
# ---------------------------------------------------------------------------
DATABASE_URL = settings.database_url
JWT_SECRET = settings.jwt_secret
JWT_ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
CORS_ORIGINS = settings.cors_origins
SEED_DEMO_ACCOUNT = settings.seed_demo_account
SEED_DEMO_DATA = settings.seed_demo_data
APIHZ_ID = settings.apihz_id
APIHZ_KEY = settings.apihz_key
FCM_SERVICE_ACCOUNT_JSON = settings.fcm_service_account_json
FCM_PROJECT_ID = settings.fcm_project_id
FCM_CLIENT_EMAIL = settings.fcm_client_email
FCM_PRIVATE_KEY = settings.fcm_private_key
FCM_REMINDER_LEAD_MINUTES = settings.reminder_lead_minutes
FCM_REMINDER_ENABLED = settings.reminder_enabled

__all__ = [
    "settings",
    "Settings",
    "BACKEND_DIR",
    "APP_NAME",
    "APP_VERSION",
    # 兼容别名
    "DATABASE_URL",
    "JWT_SECRET",
    "JWT_ALGORITHM",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "CORS_ORIGINS",
    "SEED_DEMO_ACCOUNT",
    "SEED_DEMO_DATA",
    "APIHZ_ID",
    "APIHZ_KEY",
    "FCM_SERVICE_ACCOUNT_JSON",
    "FCM_PROJECT_ID",
    "FCM_CLIENT_EMAIL",
    "FCM_PRIVATE_KEY",
    "FCM_REMINDER_LEAD_MINUTES",
    "FCM_REMINDER_ENABLED",
]
