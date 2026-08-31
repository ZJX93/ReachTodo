"""ICS 日历订阅（RFC 5545）。

价值：把待办投射进系统日历 / 手机日历 / Outlook，用户无需打开本应用就能看到日程。
主流产品都提供（滴答清单为会员功能），本项目改造前完全缺失。

鉴权特殊性：日历客户端**无法携带 Authorization 头**，只能在 URL 里带凭证。
因此这里用独立的 ``feed_token``（见 ``models/setting.py``）而非 JWT：
- 与登录令牌隔离，泄露不会导致账号被接管；
- 泄露面仅限「任务标题 + 到期时间」；
- 用户可在设置里一键重置作废旧链接。
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config import settings as app_settings
from ..database import get_db
from ..models import Task, UserSetting

router = APIRouter(tags=["calendar-feed"])

# 订阅窗口：过去 90 天 + 未来 365 天。全量导出会让日历客户端每次刷新都拉几 MB。
_PAST_DAYS = 90
_FUTURE_DAYS = 365


def _fold(line: str) -> str:
    """RFC 5545 要求单行不超过 75 字节，超出需折行（续行以单个空格开头）。

    必须按**字节**而非字符折——中文一个字符 3 字节，按字符折会超限，
    部分严格的客户端（如 macOS 日历）会直接拒绝整个文件。
    """
    raw = line.encode("utf-8")
    if len(raw) <= 73:
        return line
    chunks: list[bytes] = []
    buf = b""
    for ch in line:
        b = ch.encode("utf-8")
        # 首行 73 字节，续行 72 字节（留给前导空格）
        limit = 73 if not chunks else 72
        if len(buf) + len(b) > limit:
            chunks.append(buf)
            buf = b
        else:
            buf += b
    if buf:
        chunks.append(buf)
    head = chunks[0].decode("utf-8")
    rest = "".join("\r\n " + c.decode("utf-8") for c in chunks[1:])
    return head + rest


def _esc(text: str) -> str:
    """转义 ICS 文本值：反斜杠、分号、逗号、换行。顺序很重要，反斜杠必须先处理。"""
    return (
        (text or "")
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
        .replace("\r", "\\n")
    )


def _dt_utc(d: date, hhmm: str) -> str:
    """把「日期 + HH:MM」按服务器配置时区解释后转成 UTC 的 ICS 时间戳。"""
    try:
        h, m = (int(x) for x in hhmm.split(":"))
        naive = datetime.combine(d, time(hour=h, minute=m))
    except (ValueError, AttributeError):
        naive = datetime.combine(d, time(9, 0))
    try:
        from zoneinfo import ZoneInfo

        aware = naive.replace(tzinfo=ZoneInfo(app_settings.timezone))
    except Exception:
        # 时区库缺失 / 时区名非法时退化为 UTC，宁可时间偏移也不要 500
        aware = naive.replace(tzinfo=timezone.utc)
    return aware.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


@router.get("/api/calendar.ics")
async def calendar_feed(
    token: str = Query(..., min_length=8, max_length=64, description="订阅令牌"),
    done: bool = Query(False, description="是否包含已完成任务"),
    db: AsyncSession = Depends(get_db),
):
    if not app_settings.feature_ics_feed:
        raise HTTPException(status_code=404, detail="日历订阅未启用")

    row = await db.scalar(select(UserSetting).where(UserSetting.feed_token == token))
    if row is None:
        # 统一 404 而非 401：不向未授权方暴露「令牌格式对不对」的信息
        raise HTTPException(status_code=404, detail="订阅链接无效")

    today = date.today()
    q = (
        select(Task)
        .where(
            Task.user_id == row.user_id,
            Task.deleted_at.is_(None),
            Task.due_date.isnot(None),
            Task.due_date >= today - timedelta(days=_PAST_DAYS),
            Task.due_date <= today + timedelta(days=_FUTURE_DAYS),
        )
        .options(selectinload(Task.category))
        .order_by(Task.due_date)
    )
    if not done:
        q = q.where(Task.status == "todo")
    tasks = (await db.scalars(q)).unique().all()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines: list[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Reach Todo//Calendar Feed//ZH",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_esc('抵达 Reach 待办')}",
        f"X-WR-TIMEZONE:{app_settings.timezone}",
    ]

    for t in tasks:
        uid = f"task-{t.id}@reach-todo"
        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{uid}")
        lines.append(f"DTSTAMP:{stamp}")

        if t.due_time:
            # 有具体时刻 → 定时事件，默认时长 30 分钟
            start = _dt_utc(t.due_date, t.due_time)
            end_dt = datetime.strptime(start, "%Y%m%dT%H%M%SZ") + timedelta(minutes=30)
            lines.append(f"DTSTART:{start}")
            lines.append(f"DTEND:{end_dt.strftime('%Y%m%dT%H%M%SZ')}")
        else:
            # 仅日期 → 全天事件。DTEND 是排他的，必须 +1 天，
            # 否则多数客户端会把全天事件显示成前一天结束。
            lines.append(f"DTSTART;VALUE=DATE:{t.due_date.strftime('%Y%m%d')}")
            lines.append(
                "DTEND;VALUE=DATE:"
                + (t.due_date + timedelta(days=1)).strftime("%Y%m%d")
            )

        prefix = "✔ " if t.status == "done" else ""
        lines.append(_fold(f"SUMMARY:{_esc(prefix + t.title)}"))

        desc_parts = []
        if t.category:
            desc_parts.append(f"维度：{t.category.name}")
        desc_parts.append(f"紧急度：{t.priority} / 重要度：{t.importance}")
        if t.tags:
            desc_parts.append("标签：" + "、".join(x.name for x in t.tags))
        if t.note:
            desc_parts.append(t.note)
        # 先 join 再转义：_esc 会把真实换行转成字面 "\n"，符合 ICS 的 TEXT 值规范。
        # （不能写进 f-string 表达式里——Python 3.11 及更早不允许其中出现反斜杠）
        description = "\n".join(desc_parts)
        lines.append(_fold("DESCRIPTION:" + _esc(description)))

        if t.category:
            lines.append(_fold(f"CATEGORIES:{_esc(t.category.name)}"))
        lines.append("STATUS:" + ("CONFIRMED" if t.status == "todo" else "CANCELLED"))

        # 提醒：按任务自身提前量，缺省用全局默认
        lead = (
            t.remind_before_minutes
            if t.remind_before_minutes is not None
            else app_settings.reminder_lead_minutes
        )
        if t.due_time and lead > 0:
            lines.append("BEGIN:VALARM")
            lines.append(f"TRIGGER:-PT{lead}M")
            lines.append("ACTION:DISPLAY")
            lines.append(_fold(f"DESCRIPTION:{_esc(t.title)}"))
            lines.append("END:VALARM")

        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    body = "\r\n".join(lines) + "\r\n"

    return Response(
        content=body.encode("utf-8"),
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": 'inline; filename="reach.ics"',
            # 订阅链接不应被中间缓存留存
            "Cache-Control": "no-store, private",
        },
    )
