"""华为 Push Kit 推送通道（用于 HarmonyOS 客户端）。

**为什么需要它**：Android 端原有的 FCM 通道在没有 Google 服务的设备上完全不可用，
而 HarmonyOS NEXT 根本不存在 GMS。鸿蒙端的云端提醒必须走华为 Push Kit。

实现与 ``push.py`` 保持一致的风格：只用 ``httpx``，不引入任何华为 SDK，
凭证缺失时静默 no-op，绝不影响主流程。

配置：
  HMS_CLIENT_ID      —— AppGallery Connect 项目的 Client ID（即 App ID）
  HMS_CLIENT_SECRET  —— 对应的 Client Secret
两者缺一即视为未配置。

协议参考 Push Kit REST API v3（HarmonyOS 消息体形态）：
  POST https://push-api.cloud.huawei.com/v3/{clientId}/messages:send
"""

from __future__ import annotations

import json
import logging
import time
from typing import Optional

import httpx

from .config import settings

logger = logging.getLogger("reach.push.hms")

# access_token 缓存。华为返回的有效期通常为 3600s，这里提前 300s 过期以规避时钟漂移。
_token_cache: dict[str, float | str] = {"value": "", "expires_at": 0.0}
_TOKEN_SAFETY_MARGIN = 300


def configured() -> bool:
    return settings.hms_configured


async def _access_token(client: httpx.AsyncClient) -> Optional[str]:
    """用 client_credentials 换取 access_token，带进程内缓存。

    缓存是必要的：每分钟一次的提醒调度如果每次都换 token，
    很快会撞上华为的 OAuth 频控。
    """
    now = time.time()
    cached = str(_token_cache.get("value") or "")
    if cached and float(_token_cache.get("expires_at") or 0) > now:
        return cached

    try:
        r = await client.post(
            settings.hms_oauth_url,
            data={
                "grant_type": "client_credentials",
                "client_id": settings.hms_client_id,
                "client_secret": settings.hms_client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        r.raise_for_status()
        body = r.json()
    except Exception:  # noqa: BLE001
        logger.exception("获取华为 Push access_token 失败")
        return None

    token = body.get("access_token")
    if not token:
        logger.warning("华为 OAuth 返回中没有 access_token：%s", str(body)[:200])
        return None

    ttl = int(body.get("expires_in") or 3600)
    _token_cache["value"] = token
    _token_cache["expires_at"] = now + max(60, ttl - _TOKEN_SAFETY_MARGIN)
    return token


async def send(
    tokens: list[str],
    title: str,
    body: str,
    data: Optional[dict] = None,
) -> int:
    """向一批鸿蒙设备 token 推送通知。返回成功的设备数。

    Push Kit 支持单请求多 token，但**一个失效 token 会让整批返回非 0 码**，
    无法分辨是哪台设备的问题。这里改为逐 token 发送：请求数换取
    「精确知道哪台设备成功」，对个人自托管场景（设备数个位数）完全可接受。
    """
    if not tokens:
        return 0
    if not configured():
        logger.warning("华为 Push 未配置（HMS_CLIENT_ID / HMS_CLIENT_SECRET），跳过鸿蒙推送")
        return 0

    url = settings.hms_push_url.format(app_id=settings.hms_client_id)
    payload_data = json.dumps(
        {k: str(v) for k, v in (data or {}).items()}, ensure_ascii=False
    )

    sent = 0
    async with httpx.AsyncClient(timeout=settings.upstream_timeout_seconds) as client:
        access = await _access_token(client)
        if not access:
            return 0

        headers = {
            "Authorization": f"Bearer {access}",
            "Content-Type": "application/json; charset=UTF-8",
        }
        for token in tokens:
            message = {
                "payload": {
                    "notification": {
                        # IM 类别在鸿蒙上具备较高的到达优先级，适合到期提醒
                        "category": "IM",
                        "title": title,
                        "body": body,
                        "clickAction": {
                            # actionType=0：点击拉起应用指定 Ability
                            "actionType": 0,
                            "action": settings.hms_target_ability,
                        },
                    },
                    "extraData": payload_data,
                },
                "target": {"token": [token]},
                "pushOptions": {"testMessage": False},
            }
            try:
                r = await client.post(url, headers=headers, json=message)
                ok = False
                if r.status_code == 200:
                    try:
                        # Push Kit 用响应体里的 code 表达业务结果，
                        # HTTP 200 并不代表推送成功，必须看 code == "80000000"
                        ok = str(r.json().get("code")) == "80000000"
                    except ValueError:
                        ok = False
                if ok:
                    sent += 1
                else:
                    logger.warning(
                        "华为 Push 发送失败 status=%s body=%s",
                        r.status_code,
                        r.text[:200],
                    )
            except Exception:  # noqa: BLE001
                logger.exception("华为 Push 发送异常")
    return sent
