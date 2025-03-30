import logging
from datetime import timedelta
from enum import Enum

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, CONF_USERNAME, CONF_PASSWORD, CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from pysveasolar.api import SveaSolarAPI
from pysveasolar.models import BadgesUpdatedMessage, VehicleDetailsUpdatedMessage, VehicleDetailsData, Battery, Location
from pysveasolar.token_manager import TokenManager

from .const import DOMAIN, CONF_REFRESH_TOKEN

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR]

type SveaSolarConfigEntry = ConfigEntry[SveaSolarDataUpdateCoordinator]


class SveaSolarSystemType(str, Enum):
    BATTERY = "battery"
    LOCATION = "location"
    EV = "ev"


class SveaSolarFetchType(str, Enum):
    POLL = "poll"
    WEBSOCKET = "websocket"


async def async_setup_entry(hass: HomeAssistant, entry: SveaSolarConfigEntry):
    """Set up this integration using UI."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})

    if CONF_PASSWORD and CONF_USERNAME not in entry.data:
        raise ConfigEntryAuthFailed

    token_manager = SveaSolarTokenManager(hass, entry)
    try:
        api = SveaSolarAPI(session=async_get_clientsession(hass), token_manager=token_manager)
    except Exception as exception:
        raise ConfigEntryAuthFailed("Failed to setup API") from exception

    await api.async_login(entry.data.get(CONF_USERNAME), entry.data.get(CONF_PASSWORD))

    coordinator = SveaSolarDataUpdateCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    entry.async_create_background_task(
        hass,
        coordinator.ws_battery_connect(),
        "home_websocket_task",
    )

    for system in coordinator.system_ids[SveaSolarSystemType.EV]:
        entry.async_create_background_task(
            hass,
            coordinator.ws_ev_connect(next(iter(system))),
            "ev_websocket_task",
        )

    hass.data[DOMAIN][entry.entry_id] = entry.data
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.add_update_listener(async_reload_entry)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SveaSolarConfigEntry):
    await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    hass.data[DOMAIN].pop(entry.entry_id)
    return True


async def async_reload_entry(hass: HomeAssistant, entry: SveaSolarConfigEntry) -> None:
    """Reload the config entry when it changed."""
    await hass.config_entries.async_reload(entry.entry_id)


class SveaSolarDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: SveaSolarAPI):
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=timedelta(seconds=90))
        self._battery_websocket: dict[str, Battery] = {}
        self._battery_poll: dict[str, Battery] = {}
        self._ev_websocket: dict[str, VehicleDetailsData] = {}
        self._location_poll: dict[str, Location] = {}

        self._hass = hass
        self._entry = entry
        self._api = api
        self.system_ids: dict[SveaSolarSystemType, list] = {}

    async def _async_update_data(self):
        my_system = await self._api.async_get_my_system()
        self.system_ids = self._extract_system_ids(my_system)

        if len(self.system_ids[SveaSolarSystemType.BATTERY]) > 0:
            battery = await self._api.async_get_battery(next(iter(self.system_ids[SveaSolarSystemType.BATTERY][0])))
            self._battery_poll[battery.id] = battery

        my_data = await self._api.async_get_my_data()
        for location in my_data:
            self._location_poll[location.id] = location

        return self._data_update()

    async def ws_battery_connect(self):
        def on_connected():
            _LOGGER.debug("Connected to SveaSolar Home WS")

        def on_data(msg: BadgesUpdatedMessage):
            if msg.data.has_battery:
                battery: Battery = msg.data.battery
                _LOGGER.info(f"Battery id: {battery.battery_id}")
                _LOGGER.info(f"Battery name: {battery.name}")
                _LOGGER.info(f"Battery status: {battery.status}")
                _LOGGER.info(f"Battery SoC: {battery.state_of_charge}")

                self._battery_websocket[battery.battery_id] = battery

                self.async_set_updated_data(self._data_update())
                self.async_update_listeners()

        await self._api.async_home_websocket(data_callback=on_data, connected_callback=on_connected)

    async def ws_ev_connect(self, ev_id: str):
        def on_connected():
            _LOGGER.debug("Connected to SveaSolar EV WS")

        def on_data(msg: VehicleDetailsUpdatedMessage):
            ev: VehicleDetailsData = msg.data
            _LOGGER.info(f"EV id: {ev.id}")
            _LOGGER.info(f"EV name: {ev.name}")
            _LOGGER.info(f"EV charging status: {ev.vehicleStatus.chargingStatus}")
            _LOGGER.info(f"EV battery status: {ev.vehicleStatus.batteryLevel}")

            self._ev_websocket[ev.id] = ev
            self.async_set_updated_data(self._data_update())
            self.async_update_listeners()

        await self._api.async_ev_websocket(ev_id, data_callback=on_data, connected_callback=on_connected)

    def _data_update(self):
        data = {
            SveaSolarFetchType.POLL: {
                SveaSolarSystemType.BATTERY: self._battery_poll,
                SveaSolarSystemType.LOCATION: self._location_poll,
            },
            SveaSolarFetchType.WEBSOCKET: {
                SveaSolarSystemType.BATTERY: self._battery_websocket,
                SveaSolarSystemType.EV: self._ev_websocket,
            },
        }
        return data

    @staticmethod
    def _extract_system_ids(response) -> dict[SveaSolarSystemType, list]:
        evs = [{ev["id"]: ev["name"]} for ev in response.get("electricVehicles", [])]
        batteries = [
            {location["battery"]["id"]: location["battery"]["name"]}
            for location in response.get("locations", [])
            if location.get("battery")
        ]
        locations = [{location["id"]: location["name"]} for location in response.get("locations", [])]

        return {
            SveaSolarSystemType.EV: evs,
            SveaSolarSystemType.BATTERY: batteries,
            SveaSolarSystemType.LOCATION: locations,
        }


class SveaSolarTokenManager(TokenManager):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self._hass = hass
        self._entry = entry
        refresh_token = entry.data.get(CONF_REFRESH_TOKEN)
        access_token = entry.data.get(CONF_ACCESS_TOKEN)
        super().__init__(access_token, refresh_token)

    def update(self, access_token: str, refresh_token: str):
        super().update(access_token, refresh_token)
        _LOGGER.debug("Tokens updated")
        _LOGGER.debug(f"Access token: {self._mask_access_token(access_token)}")
        _LOGGER.debug(f"Refresh token: {self._mask_access_token(refresh_token)}")

        self._hass.config_entries.async_update_entry(
            self._entry,
            data={
                CONF_REFRESH_TOKEN: refresh_token,
                CONF_ACCESS_TOKEN: access_token,
                CONF_USERNAME: self._entry.data.get(CONF_USERNAME),
                CONF_PASSWORD: self._entry.data.get(CONF_PASSWORD),
            },
        )

    @staticmethod
    def _mask_access_token(token: str):
        if token is None:
            return "*"
        if len(token) == 1:
            return "*"
        elif len(token) < 4:
            return token[:2] + "*" * (len(token) - 2)
        elif len(token) < 10:
            return token[:2] + "*****" + token[-2:]
        else:
            return token[:5] + "*****" + token[-5:]
