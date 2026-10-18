"""电源开关。"""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PROP_POWER
from .coordinator import FotileCoordinator


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: FotileCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([FotilePowerSwitch(coordinator, entry)])


class FotilePowerSwitch(CoordinatorEntity, SwitchEntity):
    _attr_has_entity_name = False
    _attr_icon = "mdi:power"

    def __init__(self, coordinator: FotileCoordinator, entry) -> None:
        super().__init__(coordinator)
        self._attr_name = f"{entry.title} 电源"
        self._attr_unique_id = f"{DOMAIN}_{coordinator.device_id}_power"

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.online

    @property
    def is_on(self) -> bool:
        return int(self.coordinator.prop(PROP_POWER, 0) or 0) == 1

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_send({PROP_POWER: 1})

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_send({PROP_POWER: 0})
