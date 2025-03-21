import asyncio
import logging
from platform import system

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, CONF_USERNAME, CONF_PASSWORD, CONF_API_KEY, CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from pysveasolar.api import SveaSolarAPI
from pysveasolar.token_manager import TokenManager
from pysveasolar.token_managers.models import BadgesUpdatedMessage, KeepAliveMessage, VehicleDetailsUpdatedMessage

from .const import DOMAIN, CONF_REFRESH_TOKEN

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [
    Platform.SENSOR
]
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up this integration using UI."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})


    token_manager = SveaSolarTokenManager(hass, entry)
    try:
        api = SveaSolarAPI(session=async_get_clientsession(hass), token_manager=token_manager)
    except Exception as exception:
        raise ConfigEntryAuthFailed("Failed to setup API") from exception

    await api.async_login(
        entry.data.get(CONF_USERNAME),
        entry.data.get(CONF_PASSWORD)
    )

    coordinator = SveaSolarDataUpdateCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    entry.async_create_background_task(
        hass,
        coordinator.ws_connect(),
        "websocket_task",
    )

    hass.data[DOMAIN][entry.entry_id] = entry.data
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.add_update_listener(async_reload_entry)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    hass.data[DOMAIN].pop(entry.entry_id)
    return True

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when it changed."""
    await hass.config_entries.async_reload(entry.entry_id)

class SveaSolarDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: SveaSolarAPI):
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN
        )
        self._hass = hass
        self._entry = entry
        self._api = api

    async def _async_update_data(self):
        my_system = self._api.async_get_my_system()
        self._system_ids = self._extract_system_ids(my_system)
        return my_system

    async def ws_connect(self):
        async def battery_message_handler(msg):
            if isinstance(msg, BadgesUpdatedMessage):
                if msg.data.has_battery:
                    _LOGGER.info(f"Battery name: {msg.data.battery.battery_id}")
                    _LOGGER.info(f"Battery name: {msg.data.battery.name}")
                    _LOGGER.info(f"Battery status: {msg.data.battery.status}")
                    _LOGGER.info(f"Battery SoC: {msg.data.battery.state_of_charge}")

        async def ev_message_handler(msg):
            if isinstance(msg, VehicleDetailsUpdatedMessage):
                _LOGGER.info(f"EV id: {msg.data.id}")
                _LOGGER.info(f"EV name: {msg.data.name}")
                _LOGGER.info(f"EV charging status: {msg.data.vehicleStatus.chargingStatus}")
                _LOGGER.info(f"EV battery status: {msg.data.vehicleStatus.batteryLevel}")

            if isinstance(msg, KeepAliveMessage):
                print(f"KeepAlive: {msg}")

        await self._api.async_home_websocket(battery_message_handler)

        for ev_id in self._system_ids['evs']:
            await self._api.async_ev_websocket(ev_id, ev_message_handler)

    @staticmethod
    def _extract_system_ids(response) -> dict[str:str]:
        ev_ids = [ev['id'] for ev in response.get('electricVehicles', [])]
        battery_ids = [location['battery']['id'] for location in response.get('locations', []) if
                       location.get('battery')]
        location_ids = [location['id'] for location in response.get('locations', [])]

        return {
            'evs': ev_ids,
            'batteries': battery_ids,
            'locations': location_ids
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
            data={CONF_REFRESH_TOKEN: refresh_token, CONF_ACCESS_TOKEN: access_token},
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