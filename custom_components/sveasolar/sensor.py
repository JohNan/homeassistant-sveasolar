"""Sensor platform for Svea Solar."""
import logging
from dataclasses import dataclass
from datetime import datetime
from operator import attrgetter
from typing import Callable

from homeassistant.components.sensor import SensorEntityDescription, SensorDeviceClass, SensorEntity
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType
from pysveasolar.models import VehicleDetailsData, Battery

from custom_components.sveasolar import SveaSolarConfigEntry, SveaSolarDataUpdateCoordinator, SveaSolarSystemType
from custom_components.sveasolar.entity import SveaSolarEntity

_LOGGER: logging.Logger = logging.getLogger(__package__)

TYPE_EV_CHARGING_STATUS = "ev_charging_status"
TYPE_EV_BATTERY_LEVEL = "ev_battery_level"

TYPE_BATTERY_STATUS = "battery_status"
TYPE_BATTERY_BATTERY_LEVEL = "battery_battery_level"


@dataclass(frozen=True, kw_only=True)
class SveaSolarSensorEntityDescription(SensorEntityDescription):
    system_type: list[SveaSolarSystemType]
    value_fn: Callable[[VehicleDetailsData | Battery], StateType | datetime]


SENSOR_DESCRIPTIONS = (
    SveaSolarSensorEntityDescription(
        key=TYPE_BATTERY_STATUS,
        name="Status",
        translation_key="status",
        device_class=SensorDeviceClass.ENUM,
        system_type=[SveaSolarSystemType.BATTERY],
        value_fn=attrgetter("status")
    ),
    SveaSolarSensorEntityDescription(
        key=TYPE_EV_CHARGING_STATUS,
        name="Charging Status",
        device_class=SensorDeviceClass.ENUM,
        system_type=[SveaSolarSystemType.EV],
        value_fn=attrgetter("vehicleStatus.chargingStatus")
    ),
    SveaSolarSensorEntityDescription(
        key=TYPE_EV_BATTERY_LEVEL,
        name="Battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        system_type=[SveaSolarSystemType.EV],
        value_fn=attrgetter("vehicleStatus.batteryLevel")
    ),
    SveaSolarSensorEntityDescription(
        key=TYPE_BATTERY_BATTERY_LEVEL,
        name="SoC",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        system_type=[SveaSolarSystemType.BATTERY],
        value_fn=attrgetter("state_of_charge")
    ),
)


async def async_setup_entry(
        hass: HomeAssistant,
        entry: SveaSolarConfigEntry,
        async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Setup sensor platform."""
    coordinator = entry.runtime_data

    temp = [SveaSolarSensor(coordinator, system_id, system_type, system_name, description)
        for system_type, inner_list in coordinator.system_ids.items() for inner_dict in inner_list for system_id, system_name in inner_dict.items()
        for description in SENSOR_DESCRIPTIONS
        if system_type in description.system_type]

    async_add_entities(
        SveaSolarSensor(coordinator, system_id, system_type, system_name, description)
        for system_type, inner_list in coordinator.system_ids.items() for inner_dict in inner_list for system_id, system_name in inner_dict.items()
        for description in SENSOR_DESCRIPTIONS
        if system_type in description.system_type
    )


class SveaSolarSensor(SveaSolarEntity, SensorEntity):
    """Define an Ambient sensor."""

    def __init__(
            self,
            coordinator: SveaSolarDataUpdateCoordinator,
            system_id: str,
            system_type: SveaSolarSystemType,
            system_name: str,
            description: SveaSolarSensorEntityDescription
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, system_id, system_name, system_type, description)
        self.entity_description = description

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.get_entity is None:
            return None

        value = self.entity_description.value_fn(self.get_entity)
        # value = attrgetter(self.entity_description.key)(self.get_entity)
        _LOGGER.info(f"Got value: {value} for key {self.entity_description.key}")
        return value
