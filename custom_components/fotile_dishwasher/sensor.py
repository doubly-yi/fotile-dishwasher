"""状态传感器。"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    PROP_CL_REMAIN,
    PROP_DETERGENT,
    PROP_ERROR,
    PROP_REMAIN,
    PROP_SOFTENER,
    PROP_STORE_TOTAL,
    PROP_TURBIDITY,
    PROP_WORK_MODE,
    PROP_WORK_STATE,
    WORK_MODE_MAP,
    WORK_STATE_MAP,
)
from .coordinator import FotileCoordinator


@dataclass
class SensorDef:
    key: str
    name: str
    icon: str
    value: Callable[[FotileCoordinator], Any]
    unit: str | None = None
    state_class: SensorStateClass | None = None


SENSORS: tuple[SensorDef, ...] = (
    SensorDef(
        "work_state",
        "工作状态",
        "mdi:state-machine",
        lambda c: WORK_STATE_MAP.get(int(c.prop(PROP_WORK_STATE, 0) or 0), "未知"),
    ),
    SensorDef(
        "work_mode",
        "工作模式",
        "mdi:dishwasher",
        lambda c: WORK_MODE_MAP.get(int(c.prop(PROP_WORK_MODE, 0) or 0), "未知"),
    ),
    SensorDef(
        "remain_time",
        "剩余时间",
        "mdi:timer-outline",
        lambda c: int(c.prop(PROP_REMAIN, 0) or 0),
        unit="min",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorDef(
        "cl_remain",
        "剩余时间(实时)",
        "mdi:timer-sand",
        lambda c: int(c.prop(PROP_CL_REMAIN, 0) or 0),
        unit="min",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorDef(
        "store_total",
        "存储时长",
        "mdi:calendar-clock",
        lambda c: int(c.prop(PROP_STORE_TOTAL, 0) or 0),
        unit="h",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorDef(
        "error",
        "故障代码",
        "mdi:alert-circle-outline",
        lambda c: int(c.prop(PROP_ERROR, 0) or 0),
    ),
    SensorDef(
        "detergent",
        "洗碗液余量",
        "mdi:water",
        lambda c: int(c.prop(PROP_DETERGENT, 0) or 0),
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorDef(
        "softener",
        "软水盐余量",
        "mdi:shaker-outline",
        lambda c: int(c.prop(PROP_SOFTENER, 0) or 0),
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorDef(
        "turbidity",
        "浊度",
        "mdi:water-opacity",
        lambda c: int(c.prop(PROP_TURBIDITY, 0) or 0),
        state_class=SensorStateClass.MEASUREMENT,
    ),
)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: FotileCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([FotileSensor(coordinator, entry, d) for d in SENSORS])


class FotileSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = False

    def __init__(self, coordinator: FotileCoordinator, entry, definition: SensorDef) -> None:
        super().__init__(coordinator)
        self.definition = definition
        self._attr_name = f"{entry.title} {definition.name}"
        self._attr_unique_id = f"{DOMAIN}_{coordinator.device_id}_{definition.key}"
        self._attr_icon = definition.icon
        self._attr_native_unit_of_measurement = definition.unit
        if definition.state_class:
            self._attr_state_class = definition.state_class

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.online

    @property
    def native_value(self):
        try:
            return self.definition.value(self.coordinator)
        except Exception:  # noqa: BLE001
            return None
