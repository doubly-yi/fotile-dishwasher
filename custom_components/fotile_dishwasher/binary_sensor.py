"""门状态与在线状态。"""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PROP_DOOR
from .coordinator import FotileCoordinator


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: FotileCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            FotileDoorSensor(coordinator, entry),
            FotileOnlineSensor(coordinator, entry),
        ]
    )


class FotileDoorSensor(CoordinatorEntity, BinarySensorEntity):
    _attr_has_entity_name = False
    _attr_device_class = BinarySensorDeviceClass.DOOR

    def __init__(self, coordinator: FotileCoordinator, entry) -> None:
        super().__init__(coordinator)
        self._attr_name = f"{entry.title} 门"
        self._attr_unique_id = f"{DOMAIN}_{coordinator.device_id}_door"

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.online

    @property
    def is_on(self) -> bool:
        # DoorLockSta: 1 = 门锁闭合，0 = 门开
        return int(self.coordinator.prop(PROP_DOOR, 1) or 0) == 0


class FotileOnlineSensor(CoordinatorEntity, BinarySensorEntity):
    _attr_has_entity_name = False
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: FotileCoordinator, entry) -> None:
        super().__init__(coordinator)
        self._attr_name = f"{entry.title} 在线"
        self._attr_unique_id = f"{DOMAIN}_{coordinator.device_id}_online"

    @property
    def is_on(self) -> bool:
        return self.coordinator.online
