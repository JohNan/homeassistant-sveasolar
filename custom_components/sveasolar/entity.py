""" Base entity for Svea Solar"""
from idlelib.calltip import get_entity
from operator import attrgetter

from homeassistant.components.sensor import ENTITY_ID_FORMAT
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from pyric.utils.hardware import manufacturer
from pysveasolar.battery import Battery as BatteryPoll
from pysveasolar.models import Battery as BatteryLive, VehicleDetailsData


from custom_components.sveasolar import SveaSolarDataUpdateCoordinator, SveaSolarSystemType, DOMAIN, SveaSolarFetchType


class SveaSolarEntity(CoordinatorEntity[SveaSolarDataUpdateCoordinator]):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
            self,
            coordinator: SveaSolarDataUpdateCoordinator,
            system_id: str,
            system_name: str,
            system_type: SveaSolarSystemType,
            fetch_type: SveaSolarFetchType,
            description: EntityDescription
    ):
        super().__init__(coordinator)
        self._fetch_type = fetch_type
        self._system_type = system_type
        self._system_id = system_id
        self._coordinator = coordinator
        self._system_name = system_name
        self._attr_unique_id = f"{system_id}_{description.key}"
        self.entity_id = ENTITY_ID_FORMAT.format(f"{DOMAIN}_{system_name}_{description.key}")
        self.entity_description = description

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return the device info."""
        if self.get_entity is not None and hasattr(self.get_entity, "brand"):
            return DeviceInfo(
                identifiers={(DOMAIN, self._system_id)},
                name=self._system_name,
                manufacturer=attrgetter("brand")(self.get_entity)
            )

        return DeviceInfo(
            identifiers={(DOMAIN, self._system_id)},
            name=self._system_name
        )

    @property
    def get_entity(self) -> BatteryLive | VehicleDetailsData | BatteryPoll | None:
        if self._system_type not in self._coordinator.data[self._fetch_type]:
            return None

        return self._coordinator.data[self._fetch_type][self._system_type].get(self._system_id, None)
