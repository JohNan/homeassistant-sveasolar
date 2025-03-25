""" Base entity for Svea Solar"""
from homeassistant.components.sensor import ENTITY_ID_FORMAT
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from pysveasolar.models import Battery, VehicleDetailsData

from custom_components.sveasolar import SveaSolarDataUpdateCoordinator, SveaSolarSystemType, DOMAIN


class SveaSolarEntity(CoordinatorEntity[SveaSolarDataUpdateCoordinator]):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
            self,
            coordinator: SveaSolarDataUpdateCoordinator,
            system_id: str,
            system_name: str,
            system_type: SveaSolarSystemType,
            description: EntityDescription
    ):
        super().__init__(coordinator)
        self._system_type = system_type
        self._system_id = system_id
        self._coordinator = coordinator
        self._attr_unique_id = f"{system_id}_{description.key}"
        self.entity_id = ENTITY_ID_FORMAT.format(f"{DOMAIN}_{system_name}_{description.key}")
        self.entity_description = description
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, system_id)},
            name=system_name,
        )

    @property
    def get_entity(self) -> Battery | VehicleDetailsData | None:
        if self._system_type not in self._coordinator.data:
            return None

        return self._coordinator.data[self._system_type].get(self._system_id, None)
