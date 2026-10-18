"""一键启动 / 停止按钮。"""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PROP_POWER, PROP_WORK_MODE
from .coordinator import FotileCoordinator


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: FotileCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            FotileStartButton(coordinator, entry),
            FotileStopButton(coordinator, entry),
        ]
    )


class FotileStartButton(CoordinatorEntity, ButtonEntity):
    _attr_has_entity_name = False
    _attr_icon = "mdi:play-circle"

    def __init__(self, coordinator: FotileCoordinator, entry) -> None:
        super().__init__(coordinator)
        self._attr_name = f"{entry.title} 开始洗涤"
        self._attr_unique_id = f"{DOMAIN}_{coordinator.device_id}_start"

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.online

    async def async_press(self) -> None:
        mode = int(getattr(self.coordinator, "selected_mode", 0) or 0)
        await self.coordinator.async_send(
            {
                PROP_WORK_MODE: mode,
                "WorkState": 1,
                PROP_POWER: 1,
            }
        )


class FotileStopButton(CoordinatorEntity, ButtonEntity):
    _attr_has_entity_name = False
    _attr_icon = "mdi:stop-circle"

    def __init__(self, coordinator: FotileCoordinator, entry) -> None:
        super().__init__(coordinator)
        self._attr_name = f"{entry.title} 停止/关机"
        self._attr_unique_id = f"{DOMAIN}_{coordinator.device_id}_stop"

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.online

    async def async_press(self) -> None:
        await self.coordinator.async_send({PROP_POWER: 0})
