"""数据协调器：轮询设备影子 + 维护 MQTT 实时通道。"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import FotileApi, FotileAuthError, FotileMqtt
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_DEVICE_ID,
    CONF_HOME_ID,
    CONF_PHONE,
    CONF_PRODUCT_ID,
    CONF_REFRESH_TOKEN,
    CONF_SCAN_INTERVAL,
    CONF_USER_ID,
    DEFAULT_PRODUCT_ID,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class FotileCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """管理单个洗碗机的状态。"""

    def __init__(self, hass: HomeAssistant, entry) -> None:
        self.entry = entry
        data = entry.data
        self.device_id = int(data[CONF_DEVICE_ID])
        self.product_id = str(data.get(CONF_PRODUCT_ID, DEFAULT_PRODUCT_ID))
        self.home_id = str(data.get(CONF_HOME_ID, ""))
        self.product_type = str(data.get("product_type", ""))

        interval = int(
            entry.options.get(
                CONF_SCAN_INTERVAL,
                data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            )
        )
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self.device_id}",
            update_interval=timedelta(seconds=interval),
        )

        self.api = FotileApi(
            async_get_clientsession(hass),
            data[CONF_USER_ID],
            data[CONF_PHONE],
            data[CONF_ACCESS_TOKEN],
            data[CONF_REFRESH_TOKEN],
            token_callback=self._on_token_refresh,
        )

        self.mqtt: FotileMqtt | None = None
        self.mqtt_task: asyncio.Task | None = None
        self.properties: dict[str, Any] = {}
        self.online: bool = False
        self.available = True

    # ------------------------------------------------------------------ 令牌
    def _on_token_refresh(self, access: str, refresh: str, expire_in: int) -> None:
        """把轮换后的令牌写回 config entry，保证重启后仍可用。"""
        new_data = dict(self.entry.data)
        new_data[CONF_ACCESS_TOKEN] = access
        new_data[CONF_REFRESH_TOKEN] = refresh
        self.hass.config_entries.async_update_entry(self.entry, data=new_data)

    # ------------------------------------------------------------------ 轮询
    async def _async_update_data(self) -> dict[str, Any]:
        try:
            shadow = await self.api.get_shadow(self.product_id, self.device_id)
        except FotileAuthError as err:
            raise UpdateFailed(str(err)) from err

        self.online = bool(shadow.get("online"))
        props = ((shadow.get("shadowData") or {}).get("propertyPairs")) or {}
        self.properties = props
        return {
            "online": self.online,
            "properties": props,
            "timestamp": (shadow.get("shadowData") or {}).get("timeStamp"),
        }

    # ------------------------------------------------------------------ MQTT
    async def async_start_mqtt(self) -> None:
        if self.mqtt_task:
            return
        self.mqtt_task = asyncio.create_task(self._mqtt_loop())

    async def async_stop_mqtt(self) -> None:
        if self.mqtt_task:
            self.mqtt_task.cancel()
            self.mqtt_task = None
        if self.mqtt:
            await self.mqtt.disconnect()
            self.mqtt = None

    async def _mqtt_loop(self) -> None:
        while True:
            try:
                if self.mqtt and self.mqtt.connected:
                    # 连接存活期间持续检查，掉线就立刻重连
                    for _ in range(20):
                        await asyncio.sleep(3)
                        if not self.mqtt or not self.mqtt.connected:
                            break
                    if self.mqtt and self.mqtt.connected:
                        continue
                    _LOGGER.debug("MQTT 已断开，准备重连")

                broker = await self.api.get_broker()
                host = broker["ip"]
                port = int(broker.get("port", 1883))
                client_id = broker.get("clientId") or f"Fotile_APP_{self.api.user_id}"
                self.mqtt = FotileMqtt(
                    client_id, self.api.user_id, self.api.access_token, self._on_mqtt_message
                )
                await self.mqtt.connect(host, port)
                await self.mqtt.subscribe(f"sync/{self.product_id}/{self.device_id}")
                await self.mqtt.subscribe(f"reply/{self.product_id}/{self.device_id}")
                _LOGGER.debug("MQTT 已连接 %s:%s", host, port)
            except asyncio.CancelledError:
                raise
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning("MQTT 连接失败，10 秒后重试: %s", err)
                await asyncio.sleep(10)

    def _on_mqtt_message(self, topic: str, payload: str) -> None:
        text = payload.strip()
        # 设备回传形如 9e{"PowerSwitchAll":1,...}，去掉前缀长度标记
        brace = text.find("{")
        if brace > 0:
            text = text[brace:]
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return
        if not isinstance(data, dict):
            return
        self.properties.update(data)
        self.online = True
        self.async_set_updated_data(
            {
                "online": True,
                "properties": dict(self.properties),
                "timestamp": None,
            }
        )

    # ------------------------------------------------------------------ 控制
    async def async_send(self, command: dict[str, Any]) -> None:
        if not self.mqtt or not self.mqtt.connected:
            await self._ensure_mqtt()
        if not self.mqtt or not self.mqtt.connected:
            raise FotileAuthError("MQTT 通道不可用")
        await self.mqtt.publish(f"control/{self.product_id}/{self.device_id}", command)
        self.properties.update(command)
        self.async_set_updated_data(
            {"online": True, "properties": dict(self.properties), "timestamp": None}
        )

    async def _ensure_mqtt(self) -> None:
        if self.mqtt and self.mqtt.connected:
            return
        broker = await self.api.get_broker()
        self.mqtt = FotileMqtt(
            broker.get("clientId") or f"Fotile_APP_{self.api.user_id}",
            self.api.user_id,
            self.api.access_token,
            self._on_mqtt_message,
        )
        await self.mqtt.connect(broker["ip"], int(broker.get("port", 1883)))
        await self.mqtt.subscribe(f"sync/{self.product_id}/{self.device_id}")
        await self.mqtt.subscribe(f"reply/{self.product_id}/{self.device_id}")

    # ------------------------------------------------------------------ 便捷
    def prop(self, key: str, default: Any = None) -> Any:
        return self.properties.get(key, default)
