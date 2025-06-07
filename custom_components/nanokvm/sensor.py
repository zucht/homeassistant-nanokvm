"""Sensor platform for Sipeed NanoKVM."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfInformation, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategoryry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    ICON_HID,
    ICON_IMAGE,
    ICON_KVM,
    ICON_OLED,
)
from . import NanoKVMDataUpdateCoordinator, NanoKVMEntity


@dataclass
class NanoKVMSensorEntityDescription(SensorEntityDescription):
    """Describes NanoKVM sensor entity."""

    value_fn: Callable[[NanoKVMDataUpdateCoordinator], Any] = None
    available_fn: Callable[[NanoKVMDataUpdateCoordinator], bool] = lambda _: True


SENSORS: tuple[NanoKVMSensorEntityDescription, ...] = (
    NanoKVMSensorEntityDescription(
        key="hid_mode",
        name="HID Mode",
        icon=ICON_HID,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda coordinator: coordinator.hid_mode.mode.value,
    ),
    NanoKVMSensorEntityDescription(
        key="oled_sleep",
        name="OLED Sleep Timeout",
        icon=ICON_OLED,
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coordinator: coordinator.oled_info.sleep,
        available_fn=lambda coordinator: coordinator.oled_info.exist,
    ),
    NanoKVMSensorEntityDescription(
        key="hardware_version",
        name="Hardware Version",
        icon=ICON_KVM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda coordinator: coordinator.hardware_info.version.value,
    ),
    NanoKVMSensorEntityDescription(
        key="application_version",
        name="Application Version",
        icon=ICON_KVM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda coordinator: coordinator.device_info.application,
    ),
    NanoKVMSensorEntityDescription(
        key="mounted_image",
        name="Mounted Image",
        icon=ICON_IMAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda coordinator: coordinator.mounted_image.file,
        available_fn=lambda coordinator: coordinator.mounted_image.file != "",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up NanoKVM sensor based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        NanoKVMSensor(
            coordinator=coordinator,
            description=description,
        )
        for description in SENSORS
        if description.available_fn(coordinator)
    )


class NanoKVMSensor(NanoKVMEntity, SensorEntity):
    """Defines a NanoKVM sensor."""

    entity_description: NanoKVMSensorEntityDescription

    def __init__(
        self,
        coordinator: NanoKVMDataUpdateCoordinator,
        description: NanoKVMSensorEntityDescription,
    ) -> None:
        """Initialize NanoKVM sensor."""
        super().__init__(
            coordinator=coordinator,
            name=f"{description.name}",
            unique_id_suffix=f"sensor_{description.key}",
        )
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.coordinator)
