"""Sensor platform for Svea Solar."""
from dataclasses import dataclass

from homeassistant.components.sensor import SensorEntityDescription, SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from custom_components.sveasolar import SveaSolarConfigEntry, SveaSolarDataUpdateCoordinator, SveaSolarSystemType
from custom_components.sveasolar.entity import SveaSolarEntity

TYPE_STATUS = "status"


@dataclass(frozen=True, kw_only=True)
class SveaSolarSensorEntityDescription(SensorEntityDescription):
    system_type: list[SveaSolarSystemType]

SENSOR_DESCRIPTIONS = (
    SveaSolarSensorEntityDescription(
        key=TYPE_STATUS,
        name="Status",
        translation_key="status",
        device_class=SensorDeviceClass.ENUM,
        system_type=[SveaSolarSystemType.BATTERY, SveaSolarSystemType.EV]
    ),
)

async def async_setup_entry(
        hass: HomeAssistant,
        entry: SveaSolarConfigEntry,
        async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Setup sensor platform."""
    coordinator = entry.runtime_data

    async_add_entities(
        SveaSolarSensor(coordinator, system_id, system_type, description)
        for system_type, ids in coordinator.system_ids.items() for system_id in ids
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
        description: EntityDescription
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, system_id, system_type, description)

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.get_entity is None:
            return None

        return getattr(self.get_entity, self.entity_description.key)