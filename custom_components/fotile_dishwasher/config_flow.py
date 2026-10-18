"""方太洗碗机的配置流程。"""
from __future__ import annotations

import base64
import binascii
import json
import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import FotileApi, FotileAuthError
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_DEVICE_ID,
    CONF_HOME_ID,
    CONF_PHONE,
    CONF_PRODUCT_ID,
    CONF_PRODUCT_TYPE,
    CONF_REFRESH_TOKEN,
    CONF_SCAN_INTERVAL,
    CONF_USER_ID,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required("auth_code"): str,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            int, vol.Range(min=10, max=600)
        ),
    }
)


def parse_auth_code(raw: str) -> dict[str, str]:
    """把授权码还原成账号信息。

    支持两种形式：base64 编码的 JSON（tools/export_auth.py 生成的），
    或直接粘贴 JSON。
    """
    text = (raw or "").strip()
    if not text:
        raise ValueError("授权码为空")

    payload: dict[str, Any] | None = None

    if text.startswith("{"):
        payload = json.loads(text)
    else:
        compact = "".join(text.split())
        padded = compact + "=" * (-len(compact) % 4)
        for decoder in (base64.urlsafe_b64decode, base64.b64decode):
            try:
                payload = json.loads(decoder(padded).decode("utf-8"))
                break
            except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError):
                continue

    if not isinstance(payload, dict):
        raise ValueError("授权码格式不正确")

    # 兼容长字段名与短字段名
    mapping = {
        CONF_USER_ID: payload.get("u") or payload.get(CONF_USER_ID),
        CONF_PHONE: payload.get("p") or payload.get(CONF_PHONE),
        CONF_ACCESS_TOKEN: payload.get("a") or payload.get(CONF_ACCESS_TOKEN),
        CONF_REFRESH_TOKEN: payload.get("r") or payload.get(CONF_REFRESH_TOKEN),
    }
    missing = [k for k, v in mapping.items() if not v]
    if missing:
        raise ValueError(f"授权码缺少字段: {', '.join(missing)}")

    return {k: str(v) for k, v in mapping.items()}


def _collect_devices(payload: Any) -> list[dict[str, Any]]:
    """从不同结构的设备接口响应里提取设备列表。

    实测接口有两种形态：
      {"deviceList": [ {...}, ... ]}
      {"data": [ {"homeId": 1, "devices": [...]}, ... ]}
    """
    found: list[dict[str, Any]] = []

    def add(items: Any) -> None:
        if isinstance(items, list):
            found.extend(item for item in items if isinstance(item, dict))

    def add_homes(homes: Any) -> None:
        if not isinstance(homes, list):
            return
        for home in homes:
            if isinstance(home, dict):
                add(home.get("devices"))

    if isinstance(payload, list):
        add(payload)
        add_homes(payload)
        for item in payload:
            if isinstance(item, dict):
                add_homes(item.get("homes") or item.get("list"))
    elif isinstance(payload, dict):
        add(payload.get("deviceList"))
        data = payload.get("data")
        if isinstance(data, list):
            add(data)
            add_homes(data)
        elif isinstance(data, dict):
            add(data.get("deviceList"))
            add(data.get("devices"))
            add_homes(data.get("homes") or data.get("list"))
        add_homes(payload.get("homes") or payload.get("list"))

    # 去重（按设备 ID）
    unique: dict[str, dict[str, Any]] = {}
    for dev in found:
        key = str(dev.get("id") or dev.get("deviceId") or "")
        if key:
            unique.setdefault(key, dev)
    return list(unique.values())


class FotileConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """添加一台方太洗碗机。"""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                credentials = parse_auth_code(user_input["auth_code"])
            except ValueError:
                _LOGGER.debug("授权码解析失败", exc_info=True)
                errors["base"] = "invalid_auth_code"
            else:
                try:
                    device = await self._async_discover(credentials)
                except FotileAuthError:
                    _LOGGER.debug("凭据验证失败", exc_info=True)
                    errors["base"] = "auth"
                except Exception:  # noqa: BLE001
                    _LOGGER.exception("添加设备时发生异常")
                    errors["base"] = "unknown"
                else:
                    await self.async_set_unique_id(f"{DOMAIN}_{device[CONF_DEVICE_ID]}")
                    self._abort_if_unique_id_configured()
                    data = {
                        **credentials,
                        **device,
                        CONF_SCAN_INTERVAL: user_input.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    }
                    return self.async_create_entry(
                        title=device.get("name") or "方太洗碗机", data=data
                    )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )

    async def _async_discover(self, credentials: dict[str, str]) -> dict[str, Any]:
        """用授权信息列出设备，自动挑出洗碗机。"""
        session = async_get_clientsession(self.hass)
        api = FotileApi(
            session,
            credentials[CONF_USER_ID],
            credentials[CONF_PHONE],
            credentials[CONF_ACCESS_TOKEN],
            credentials[CONF_REFRESH_TOKEN],
        )
        payload = await api.get_all_devices()

        for dev in _collect_devices(payload):
            product_id = str(dev.get("product_id") or dev.get("productId") or "")
            if not product_id.startswith("1025"):
                continue
            home_id = (
                dev.get("familyId")
                or dev.get("homeId")
                or dev.get("home_id")
                or ""
            )
            return {
                CONF_HOME_ID: str(home_id),
                CONF_DEVICE_ID: str(dev.get("id") or dev.get("deviceId") or ""),
                CONF_PRODUCT_ID: product_id,
                CONF_PRODUCT_TYPE: str(
                    dev.get("type") or dev.get("productType") or ""
                ),
                "name": dev.get("name") or "方太洗碗机",
            }

        raise FotileAuthError("该账号下没有找到洗碗机设备")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return FotileOptionsFlow()


class FotileOptionsFlow(config_entries.OptionsFlow):
    """调整轮询间隔。"""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_SCAN_INTERVAL, default=current): vol.All(
                        int, vol.Range(min=10, max=600)
                    )
                }
            ),
        )
