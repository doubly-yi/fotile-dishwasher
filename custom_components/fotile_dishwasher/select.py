"""洗涤模式选择（本地选择 + 一键启动）。"""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PROP_WORK_MODE, SELECTABLE_MODES, WORK_MODE_MAP
from .coordinator import FotileCoordinator

_OPTIONS = [WORK_MODE_MAP[m] for m in SELECTABLE_MODES]
_NAME_TO_ID = {WORK_MODE_MAP[m]: m for m in SELECTABLE_MODES}


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: FotileCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([FotileWorkModeSelect(coordinator, entry)])


class FotileWorkModeSelect(CoordinatorEntity, SelectEntity):
    _attr_has_entity_name = False
    _attr_icon = "mdi:dishwasher"

    def __init__(self, coordinator: FotileCoordinator, entry) -> None:
        super().__init__(coordinator)
        self._attr_name = f"{entry.title} 洗涤模式"
        self._attr_unique_id = f"{DOMAIN}_{coordinator.device_id}_work_mode_select"
        self._attr_options = _OPTIONS
        self._selected = _OPTIONS[0]

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.online

    @property
    def current_option(self) -> str:
        mode = int(self.coordinator.prop(PROP_WORK_MODE, 0) or 0)
        if mode in SELECTABLE_MODES and int(self.coordinator.prop("PowerSwitchAll", 0) or 0) == 1:
            return WORK_MODE_MAP.get(mode, self._selected)
        return self._selected

    async def async_select_option(self, option: str) -> None:
        if option not in _NAME_TO_ID:
            return
        self._selected = option
        self.coordinator.selected_mode = _NAME_TO_ID[option]
        self.async_write_ha_state()

    @property
    def selected_mode_id(self) -> int:
        return _NAME_TO_ID.get(self._selected, 0)
