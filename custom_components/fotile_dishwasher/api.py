"""方太云 API 客户端：令牌管理、HTTP 与 MQTT。"""
from __future__ import annotations

import asyncio
import json
import logging
import struct
import time
from collections.abc import Callable
from typing import Any

import aiohttp

from .const import (
    BASE_URL,
    DEFAULT_APPVER,
    DEFAULT_MODEL,
    DEFAULT_SOFTWARE,
    DEFAULT_SOURCE,
    DEVICES_URL,
    REFRESH_URL,
    ROUTE_URL,
    SHADOW_URL,
    TOKEN_REFRESH_MARGIN,
)

_LOGGER = logging.getLogger(__name__)


class FotileAuthError(Exception):
    """令牌失效且无法刷新。"""


class FotileApi:
    """方太云 HTTP 客户端。"""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        user_id: str,
        phone: str,
        access_token: str,
        refresh_token: str,
        token_callback: Callable[[str, str, int], None] | None = None,
    ) -> None:
        self._session = session
        self.user_id = str(user_id)
        self.phone = str(phone)
        self.access_token = access_token
        self.refresh_token = refresh_token
        self._expires_at = time.time() + 86400
        self._token_callback = token_callback
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------ 令牌
    def _set_tokens(self, access: str, refresh: str, expire_in: int) -> None:
        self.access_token = access
        self.refresh_token = refresh
        self._expires_at = time.time() + int(expire_in or 86400)
        if self._token_callback:
            self._token_callback(access, refresh, int(expire_in or 86400))

    @property
    def seconds_left(self) -> float:
        return self._expires_at - time.time()

    async def ensure_token(self) -> None:
        """令牌快过期时主动刷新。"""
        if self.seconds_left > TOKEN_REFRESH_MARGIN:
            return
        await self.refresh_tokens()

    async def refresh_tokens(self) -> None:
        """调用 refresh2 轮换令牌（refresh_token 为一次性）。"""
        async with self._lock:
            payload = {
                "refreshToken": self.refresh_token,
                "accessToken": self.access_token,
                "phone": self.phone,
            }
            try:
                async with self._session.post(
                    REFRESH_URL,
                    json=payload,
                    headers=self._base_headers(),
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    data = await resp.json(content_type=None)
            except Exception as err:  # noqa: BLE001
                raise FotileAuthError(f"刷新令牌请求失败: {err}") from err

            if not isinstance(data, dict) or not data.get("access_token"):
                raise FotileAuthError(f"刷新令牌失败: {data}")

            self._set_tokens(
                data["access_token"],
                data.get("refresh_token", self.refresh_token),
                data.get("expire_in", 86400),
            )
            _LOGGER.debug("令牌已刷新，有效期 %s 秒", data.get("expire_in"))

    # ------------------------------------------------------------------ HTTP
    def _base_headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json; charset=utf-8",
            "Accept-Encoding": "gzip",
            "X-Source": DEFAULT_SOURCE,
            "X-ModelName": DEFAULT_MODEL,
            "X-SoftwareVersion": DEFAULT_SOFTWARE,
            "X-AppVer": DEFAULT_APPVER,
            "User-Agent": "Dart/3.6 (dart:io)",
        }

    def _auth_headers(self) -> dict[str, str]:
        headers = self._base_headers()
        headers["Access-Token"] = self.access_token
        headers["X-User"] = self.user_id
        return headers

    async def _request(self, method: str, url: str, payload: Any = None) -> Any:
        await self.ensure_token()
        for attempt in (1, 2):
            try:
                async with self._session.request(
                    method,
                    url,
                    json=payload,
                    headers=self._auth_headers(),
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    data = await resp.json(content_type=None)
            except Exception as err:  # noqa: BLE001
                raise FotileAuthError(f"请求 {url} 失败: {err}") from err

            if isinstance(data, dict) and data.get("error"):
                code = (data.get("error") or {}).get("code")
                if code in (4031002, 4031021) and attempt == 1:
                    await self.refresh_tokens()
                    continue
                raise FotileAuthError(f"接口错误: {data['error']}")
            return data
        raise FotileAuthError("请求重试后仍失败")

    async def get_devices(self, home_id: str | int) -> dict:
        return await self._request("GET", DEVICES_URL.format(home_id=home_id))

    async def get_all_devices(self) -> Any:
        """一次性列出所有家庭及设备（用于配置时自动发现）。"""
        return await self._request("GET", f"{BASE_URL}/v3/all/homes/devices")

    async def get_shadow(self, product_id: str, device_id: int) -> dict:
        data = await self._request(
            "POST",
            SHADOW_URL,
            {"devices": [{"productId": product_id, "deviceId": int(device_id)}]},
        )
        shadows = ((data or {}).get("data") or {}).get("deviceShadows") or []
        if not shadows:
            raise FotileAuthError("设备影子为空")
        return shadows[0]

    async def get_broker(self) -> dict:
        data = await self._request(
            "POST",
            ROUTE_URL,
            {
                "bussinessType": 1,
                "userId": self.user_id,
                "requestType": 1,
                "clientType": 1,
            },
        )
        if isinstance(data, list) and data:
            return data[0]
        raise FotileAuthError(f"MQTT 路由异常: {data}")


# ---------------------------------------------------------------------- MQTT


def _enc_str(text: str) -> bytes:
    raw = text.encode()
    return struct.pack(">H", len(raw)) + raw


def _packet(ptype: int, flags: int, payload: bytes) -> bytes:
    header = bytes([(ptype << 4) | flags])
    length = len(payload)
    out = bytearray(header)
    while True:
        digit = length % 128
        length //= 128
        if length:
            out.append(digit | 0x80)
        else:
            out.append(digit)
            break
    return bytes(out) + payload


class FotileMqtt:
    """极简 MQTT 3.1.1 客户端，仅支持方太设备频道所需功能。"""

    def __init__(
        self,
        client_id: str,
        username: str,
        password: str,
        on_message: Callable[[str, str], None],
    ) -> None:
        self.client_id = client_id
        self.username = username
        self.password = password
        self.on_message = on_message
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._task: asyncio.Task | None = None
        self._keepalive: asyncio.Task | None = None
        self.connected = False
        self._packet_id = 1

    async def connect(self, host: str, port: int = 1883) -> None:
        self._reader, self._writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=20
        )
        payload = (
            _enc_str(self.client_id) + _enc_str(self.username) + _enc_str(self.password)
        )
        variable = struct.pack(">H", 4) + b"MQTT" + bytes([4, 0xC2]) + struct.pack(">H", 60)
        self._writer.write(_packet(1, 0, variable + payload))
        await self._writer.drain()

        ptype, body = await asyncio.wait_for(self._read_packet(), timeout=15)
        if ptype >> 4 != 2 or len(body) < 2 or body[1] != 0:
            raise FotileAuthError(f"MQTT 连接被拒绝: {body}")
        self.connected = True
        self._task = asyncio.create_task(self._reader_loop())
        self._keepalive = asyncio.create_task(self._ping_loop())

    async def subscribe(self, topic: str, qos: int = 1) -> None:
        if not self._writer:
            return
        pid = self._next_id()
        body = struct.pack(">H", pid) + _enc_str(topic) + bytes([qos])
        self._writer.write(_packet(8, 2, body))
        await self._writer.drain()

    async def publish(self, topic: str, payload: str | dict) -> None:
        if not self._writer or not self.connected:
            raise FotileAuthError("MQTT 未连接")
        text = payload if isinstance(payload, str) else json.dumps(payload, separators=(",", ":"))
        self._writer.write(_packet(3, 0, _enc_str(topic) + text.encode()))
        await self._writer.drain()

    def _next_id(self) -> int:
        self._packet_id = self._packet_id % 65535 + 1
        return self._packet_id

    async def _read_packet(self) -> tuple[int, bytes]:
        assert self._reader is not None
        head = await self._reader.readexactly(1)
        multiplier = 1
        length = 0
        while True:
            digit = (await self._reader.readexactly(1))[0]
            length += (digit & 0x7F) * multiplier
            if not digit & 0x80:
                break
            multiplier *= 128
        body = await self._reader.readexactly(length) if length else b""
        return head[0], body

    async def _reader_loop(self) -> None:
        while self.connected:
            try:
                ptype, body = await self._read_packet()
            except Exception:  # noqa: BLE001
                self.connected = False
                break
            if ptype >> 4 == 3 and len(body) >= 2:
                topic_len = struct.unpack(">H", body[0:2])[0]
                topic = body[2 : 2 + topic_len].decode("utf-8", "replace")
                data = body[2 + topic_len :].decode("utf-8", "replace")
                try:
                    self.on_message(topic, data)
                except Exception:  # noqa: BLE001
                    _LOGGER.exception("处理 MQTT 消息失败")

    async def _ping_loop(self) -> None:
        while self.connected and self._writer:
            await asyncio.sleep(30)
            if not self.connected or not self._writer:
                break
            try:
                self._writer.write(_packet(12, 0, b""))
                await self._writer.drain()
            except Exception:  # noqa: BLE001
                self.connected = False
                break

    async def disconnect(self) -> None:
        self.connected = False
        for task in (self._task, self._keepalive):
            if task:
                task.cancel()
        if self._writer:
            try:
                self._writer.write(_packet(14, 0, b""))
                await self._writer.drain()
            except Exception:  # noqa: BLE001
                pass
            try:
                self._writer.close()
            except Exception:  # noqa: BLE001
                pass
        self._reader = None
        self._writer = None
