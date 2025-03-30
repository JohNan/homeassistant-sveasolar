"""Sensor platform for Svea Solar."""

import logging
from dataclasses import dataclass
from datetime import datetime
from operator import attrgetter
from typing import Callable, Any, Mapping

from homeassistant.components.sensor import SensorEntityDescription, SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfLength, UnitOfEnergy, UnitOfTime, EntityCategory, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType
from pysveasolar.models import Battery, BatteryDetailsData, VehicleDetailsData, Location
from homeassistant.util import dt as dt_util

from custom_components.sveasolar import (
    SveaSolarConfigEntry,
    SveaSolarDataUpdateCoordinator,
    SveaSolarSystemType,
    SveaSolarFetchType,
)
from custom_components.sveasolar.entity import SveaSolarEntity

_LOGGER: logging.Logger = logging.getLogger(__package__)

TYPE_EV_CHARGING_STATUS = "ev_charging_status"
TYPE_EV_BATTERY_LEVEL = "ev_battery_level"
TYPE_EV_RANGE = "ev_range"
TYPE_EV_CHARGING_HOURS = "ev_charging_hours"
TYPE_EV_ENERGY = "ev_energy"

TYPE_BATTERY_STATUS = "battery_status"
TYPE_BATTERY_BATTERY_LEVEL = "battery_battery_level"
TYPE_BATTERY_CAPACITY = "battery_capacity"
TYPE_BATTERY_DISCHARGED_ENERGY = "battery_discharged_energy"
TYPE_BATTERY_CHARGED_ENERGY = "battery_charged_energy"
TYPE_BATTERY_DISCHARGE_POWER = "battery_discharge_power"

TYPE_LOCATION_SPOT_PRICE = "location_spot_price"
TYPE_LOCATION_RATING = "location_rating"
TYPE_LOCATION_STATUS = "location_status"
TYPE_LOCATION_GRID_POWER = "location_grid_power"
TYPE_LOCATION_SOLAR_POWER = "location_solar_power"
TYPE_LOCATION_BATTERY_POWER = "location_battery_power"
TYPE_LOCATION_USAGE_POWER = "location_usage_power"


@dataclass(frozen=True, kw_only=True)
class SveaSolarSensorEntityDescription(SensorEntityDescription):
    fetch_type: SveaSolarFetchType
    system_type: list[SveaSolarSystemType]
    value_fn: Callable[[VehicleDetailsData | Battery | Location | BatteryDetailsData], StateType | datetime]


SENSOR_DESCRIPTIONS = (
    SveaSolarSensorEntityDescription(
        key=TYPE_BATTERY_STATUS,
        name="Status",
        translation_key="status",
        device_class=SensorDeviceClass.ENUM,
        system_type=[SveaSolarSystemType.BATTERY],
        fetch_type=SveaSolarFetchType.WEBSOCKET,
        value_fn=attrgetter("status"),
    ),
    SveaSolarSensorEntityDescription(
        key=TYPE_BATTERY_BATTERY_LEVEL,
        name="SoC",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        system_type=[SveaSolarSystemType.BATTERY],
        fetch_type=SveaSolarFetchType.WEBSOCKET,
        value_fn=attrgetter("state_of_charge"),
    ),
    SveaSolarSensorEntityDescription(
        key=TYPE_BATTERY_DISCHARGED_ENERGY,
        name="Today discharged energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        system_type=[SveaSolarSystemType.BATTERY],
        fetch_type=SveaSolarFetchType.POLL,
        value_fn=attrgetter("dischargedEnergy"),
    ),
    SveaSolarSensorEntityDescription(
        key=TYPE_BATTERY_CHARGED_ENERGY,
        name="Today charged energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        system_type=[SveaSolarSystemType.BATTERY],
        fetch_type=SveaSolarFetchType.POLL,
        value_fn=attrgetter("chargedEnergy"),
    ),
    SveaSolarSensorEntityDescription(
        key=TYPE_BATTERY_DISCHARGE_POWER,
        name="Discharge Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        system_type=[SveaSolarSystemType.BATTERY],
        fetch_type=SveaSolarFetchType.POLL,
        suggested_display_precision=3,
        value_fn=attrgetter("dischargePower"),
    ),
    SveaSolarSensorEntityDescription(
        key=TYPE_BATTERY_CAPACITY,
        name="Capacity",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        system_type=[SveaSolarSystemType.BATTERY],
        fetch_type=SveaSolarFetchType.POLL,
        value_fn=attrgetter("capacity"),
    ),
    SveaSolarSensorEntityDescription(
        key=TYPE_EV_CHARGING_STATUS,
        name="Charging Status",
        device_class=SensorDeviceClass.ENUM,
        system_type=[SveaSolarSystemType.EV],
        fetch_type=SveaSolarFetchType.WEBSOCKET,
        value_fn=attrgetter("vehicleStatus.chargingStatus"),
    ),
    SveaSolarSensorEntityDescription(
        key=TYPE_EV_BATTERY_LEVEL,
        name="Battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        system_type=[SveaSolarSystemType.EV],
        fetch_type=SveaSolarFetchType.WEBSOCKET,
        value_fn=attrgetter("vehicleStatus.batteryLevel"),
    ),
    SveaSolarSensorEntityDescription(
        key=TYPE_EV_RANGE,
        name="Range",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        system_type=[SveaSolarSystemType.EV],
        fetch_type=SveaSolarFetchType.WEBSOCKET,
        value_fn=attrgetter("vehicleStatus.range"),
    ),
    SveaSolarSensorEntityDescription(
        key=TYPE_EV_ENERGY,
        name="Total energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        system_type=[SveaSolarSystemType.EV],
        fetch_type=SveaSolarFetchType.WEBSOCKET,
        value_fn=attrgetter("summary.energyInKwh"),
    ),
    SveaSolarSensorEntityDescription(
        key=TYPE_EV_CHARGING_HOURS,
        name="Total charging time",
        native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:battery-clock",
        system_type=[SveaSolarSystemType.EV],
        fetch_type=SveaSolarFetchType.WEBSOCKET,
        value_fn=attrgetter("summary.chargingTimeInHours"),
    ),
    SveaSolarSensorEntityDescription(
        key=TYPE_LOCATION_SPOT_PRICE,
        name="Energy Price",
        native_unit_of_measurement="SEK/kWh",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:cash",
        system_type=[SveaSolarSystemType.LOCATION],
        fetch_type=SveaSolarFetchType.POLL,
        suggested_display_precision=2,
        value_fn=lambda location: 0 if location.spotPrice is None else location.spotPrice.value / 100,
    ),
    SveaSolarSensorEntityDescription(
        key=TYPE_LOCATION_RATING,
        name="Rating",
        device_class=SensorDeviceClass.ENUM,
        system_type=[SveaSolarSystemType.LOCATION],
        fetch_type=SveaSolarFetchType.POLL,
        value_fn=lambda location: "N/A" if location.spotPrice is None else location.spotPrice.rating,
    ),
    SveaSolarSensorEntityDescription(
        key=TYPE_LOCATION_STATUS,
        name="Status",
        device_class=SensorDeviceClass.ENUM,
        system_type=[SveaSolarSystemType.LOCATION],
        fetch_type=SveaSolarFetchType.POLL,
        value_fn=attrgetter("statusRightNow.status"),
    ),
    SveaSolarSensorEntityDescription(
        key=TYPE_LOCATION_SOLAR_POWER,
        name="Solar",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        system_type=[SveaSolarSystemType.LOCATION],
        fetch_type=SveaSolarFetchType.POLL,
        value_fn=lambda location: next(
            (source.value for source in location.statusRightNow.sources if source.type == "Solar"), None
        ),
    ),
    SveaSolarSensorEntityDescription(
        key=TYPE_LOCATION_BATTERY_POWER,
        name="Battery",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        system_type=[SveaSolarSystemType.LOCATION],
        fetch_type=SveaSolarFetchType.POLL,
        value_fn=lambda location: next(
            (source.value for source in location.statusRightNow.sources if source.type == "Battery"), None
        ),
    ),
    SveaSolarSensorEntityDescription(
        key=TYPE_LOCATION_USAGE_POWER,
        name="Usage",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        system_type=[SveaSolarSystemType.LOCATION],
        fetch_type=SveaSolarFetchType.POLL,
        value_fn=lambda location: next(
            (source.value for source in location.statusRightNow.destinations if source.type == "Usage"), None
        ),
    ),
    SveaSolarSensorEntityDescription(
        key=TYPE_LOCATION_GRID_POWER,
        name="Grid",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        system_type=[SveaSolarSystemType.LOCATION],
        fetch_type=SveaSolarFetchType.POLL,
        value_fn=lambda location: next(
            (source.value for source in location.statusRightNow.destinations if source.type == "Grid"), None
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: SveaSolarConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Setup sensor platform."""
    coordinator = entry.runtime_data

    async_add_entities(
        SveaSolarSensor(coordinator, system_id, system_type, system_name, description.fetch_type, description)
        for system_type, inner_list in coordinator.system_ids.items()
        for inner_dict in inner_list
        for system_id, system_name in inner_dict.items()
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
        fetch_type: SveaSolarFetchType,
        description: SveaSolarSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, system_id, system_name, system_type, fetch_type, description)
        self.entity_description = description

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        entity = self.get_entity()
        if self.entity_description.key is TYPE_LOCATION_SPOT_PRICE and isinstance(entity, Location):
            if entity.spotPrice.tomorrow is not None:
                tomorrow = ", ".join(str(round(data.value, 2)) for data in entity.spotPrice.tomorrow.data)
                tomorrow_raw = [
                    {
                        "time": dt_util.parse_datetime(data.time).replace(tzinfo=dt_util.get_default_time_zone()),
                        "price": round(data.value, 2),
                        "rating": data.rating,
                    }
                    for data in entity.spotPrice.tomorrow.data
                ]
                tomorrow_valid = True
            else:
                tomorrow = None
                tomorrow_raw = None
                tomorrow_valid = False
            return {
                "last_update": dt_util.parse_datetime(entity.spotPrice.time).isoformat(),
                "today": ", ".join(str(round(data.value, 2)) for data in entity.spotPrice.today.data),
                "today_raw": [
                    {
                        "time": dt_util.parse_datetime(data.time).replace(tzinfo=dt_util.get_default_time_zone()),
                        "price": round(data.value, 2),
                        "rating": data.rating,
                    }
                    for data in entity.spotPrice.today.data
                ],
                "tomorrow": tomorrow,
                "tomorrow_raw": tomorrow_raw,
                "tomorrow_valid": tomorrow_valid,
            }

        return {}

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.get_entity() is None:
            return None

        value = self.entity_description.value_fn(self.get_entity())
        if self.entity_description.key is TYPE_BATTERY_BATTERY_LEVEL and value.isnumeric() is False:
            return attrgetter("stateOfCharge")(self.get_entity(alternative_fetch=True))

        return value
