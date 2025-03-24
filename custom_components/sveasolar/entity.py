""" Base entity for Svea Solar"""

from homeassistant.helpers.entity import Entity, EntityDescription
from pysveasolar.token_managers.models import Battery, VehicleDetailsData

from custom_components.sveasolar import SveaSolarDataUpdateCoordinator, SveaSolarSystemType


class SveaSolarEntity(Entity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
            self,
            coordinator: SveaSolarDataUpdateCoordinator,
            system_id: str,
            system_type: SveaSolarSystemType,
            description: EntityDescription,
    ):
        self._system_type = system_type
        self._system_id = system_id
        self._coordinator = coordinator
        self._attr_unique_id = f"{system_id}_{description.key}"
        self.entity_description = description

    @property
    def get_entity(self) -> Battery | VehicleDetailsData | None:
        if self._system_type not in self._coordinator.data:
            return None

        return self._coordinator.data[self._system_type].get(self._system_id, None)
