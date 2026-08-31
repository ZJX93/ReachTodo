"""后台到期提醒调度器 + 回收站过期清理。

在 app.main 的 lifespan 中 start/stop。每个周期（默认 60s）扫描一次：

    status=todo 且 due_date 非空 且 reminder_sent_at 为空 且未软删除
    且 now >= (due_datetime - lead_minutes)
  → 向该用户全部设备推送，并写入 reminder_sent_at 去重。

其中 ``lead_minutes`` 优先取任务自身的 ``remind_before_minutes``，
为空时回落到全局 ``REMINDER_LEAD_MINUTES``。

推送凭证未配置时 send_to_user 返回 0，本调度器不会写 reminder_sent_at，
待凭证就绪后下一个周期自然补发。

两处关键工程约束：

1. **时区**：全部用 UTC-aware 时间比较。任务的 ``due_date/due_time`` 是用户
   本地日历意图（"9 月 1 日 09:00"），按服务端配置时区 ``APP_TIMEZONE``
   解释后再转 UTC。改造前用 ``datetime.now()``（naive 本地时间）与
   DB 中的 aware 时间混比，在容器 UTC / 用户东八区的典型部署下会整体偏 8 小时。
2. **扫描窗口**：只查 ``due_date`` 落在 now ± ``REMINDER_SCAN_WINDOW_HOURS``
   的任务。改造前是无界查询，任务表越大每分钟的全表扫越慢。
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional

from sqlalchemy import select

from .config import settings
from .database import SessionLocal
from .models import Task
from .push import send_to_user

logger = logging.getLogger("reach.scheduler")

_task: Optional[asyncio.Task] = None
# 回收站清理远比提醒低频，用计数器控制（默认每 60 个周期 ≈ 1 小时一次）
_PURGE_EVERY_TICKS = 60
_tick_count = 0


def _tzinfo():
    """解析配置时区；非法或缺少 tzdata 时退化为 UTC 并告警一次。"""
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(settings.timezone)
    except Exception:  # noqa: BLE001
        logger.warning(
            "无法解析 APP_TIMEZONE=%r（缺少 tzdata？），提醒时间按 UTC 计算",
            settings.timezone,
        )
        return timezone.utc


def _due_datetime(task: Task, tz) -> Optional[datetime]:
    """把任务的「日期 + HH:MM」按业务时区解释成 UTC-aware 时间。"""
    if not task.due_date:
        return None
    if task.due_time:
        try:
            hh, mm = task.due_time.split(":")
            t = time(int(hh), int(mm))
        except (ValueError, AttributeError):
            t = time(0, 0)
    else:
        # 仅有日期的任务视为当天 00:00 到期
        t = time(0, 0)
    local = datetime.combine(task.due_date, t).replace(tzinfo=tz)
    return local.astimezone(timezone.utc)


def _lead_minutes(task: Task) -> int:
    """任务级提前量优先，未设置则用全局默认。"""
    if task.remind_before_minutes is not None:
        return max(0, task.remind_before_minutes)
    return settings.reminder_lead_minutes


def _body(task: Task) -> str:
    when = task.due_time or "今天"
    return f"「{task.title}」将于 {task.due_date} {when} 到期"


async def _tick() -> None:
    tz = _tzinfo()
    now = datetime.now(timezone.utc)
    window = timedelta(hours=settings.reminder_scan_window_hours)
    # due_date 是 Date 列，按日期粗筛（比 now 精确比较宽一天，避免边界漏掉）
    lo: date = (now - window).date()
    hi: date = (now + window).date()

    async with SessionLocal() as db:
        rows = (
            await db.execute(
                select(Task).where(
                    Task.status == "todo",
                    Task.deleted_at.is_(None),
                    Task.due_date.isnot(None),
                    Task.reminder_sent_at.is_(None),
                    Task.due_date >= lo,
                    Task.due_date <= hi,
                )
            )
        ).scalars().all()

        due = []
        for t in rows:
            dd = _due_datetime(t, tz)
            if dd is None:
                continue
            if now >= dd - timedelta(minutes=_lead_minutes(t)):
                due.append(t)

        for t in due:
            try:
                sent = await send_to_user(
                    t.user_id,
                    title=f"⏰ 任务提醒：{t.title}",
                    body=_body(t),
                    data={"taskId": str(t.id), "link": f"/tasks/{t.id}"},
                )
                if sent > 0:
                    t.reminder_sent_at = now
            except Exception:  # noqa: BLE001
                logger.exception("发送到期提醒失败 task=%s", t.id)
        await db.commit()


async def _purge_trash() -> None:
    """物理删除超过保留期的软删除数据。"""
    if not settings.feature_trash:
        return
    from .routers.trash import purge_expired

    async with SessionLocal() as db:
        removed = await purge_expired(db)
    if removed:
        logger.info("回收站清理：物理删除 %s 条超过 %s 天的数据", removed, settings.trash_retention_days)


async def _loop() -> None:
    global _tick_count
    while True:
        try:
            await _tick()
            _tick_count += 1
            if _tick_count % _PURGE_EVERY_TICKS == 0:
                await _purge_trash()
        except asyncio.CancelledError:
            # 正常停机路径，必须原样抛出，否则 stop() 无法真正取消
            raise
        except Exception:  # noqa: BLE001
            logger.exception("提醒调度器 tick 异常")
        await asyncio.sleep(settings.reminder_interval_seconds)


def start() -> None:
    """启动后台调度器（幂等）。"""
    global _task
    if not settings.reminder_enabled:
        logger.info("提醒调度器已关闭（REMINDER_ENABLED != 1）")
        return
    if _task is None or _task.done():
        _task = asyncio.create_task(_loop())
        logger.info(
            "提醒调度器已启动：间隔 %ss，默认提前 %s 分钟，时区 %s",
            settings.reminder_interval_seconds,
            settings.reminder_lead_minutes,
            settings.timezone,
        )


def stop() -> None:
    """取消后台调度器任务。"""
    global _task
    if _task is not None:
        _task.cancel()
        _task = None


def is_running() -> bool:
    """供 /health 报告调度器状态。"""
    return _task is not None and not _task.done()
