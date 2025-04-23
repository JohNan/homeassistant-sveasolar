import asyncio
import logging
from datetime import timedelta
from enum import Enum

from aiohttp import ClientError
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, CONF_USERNAME, CONF_PASSWORD, CONF_ACCESS_TOKEN, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant, Event
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pysveasolar.api import SveaSolarAPI
from pysveasolar.errors import WebsocketError, AuthenticationError
from pysveasolar.models import (
    BadgesUpdatedMessage,
    VehicleDetailsUpdatedMessage,
    VehicleDetailsData,
    Battery,
    Location,
    BatteryDetailsData,
)
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

    coordinator.async_websockets_connect()

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
    await entry.runtime_data.async_websocket_disconnect()
    await hass.config_entries.async_reload(entry.entry_id)


class SveaSolarDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: SveaSolarAPI):
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=timedelta(seconds=90))
        self._battery_websocket: dict[str, Battery] = {}
        self._battery_poll: dict[str, BatteryDetailsData] = {}
        self._ev_websocket: dict[str, VehicleDetailsData] = {}
        self._location_poll: dict[str, Location] = {}

        self._hass = hass
        self._entry = entry
        self._api = api
        self.system_ids: dict[SveaSolarSystemType, list] = {}
        self._home_websocket_reconnect_task: asyncio.Task | None = None
        self._ev_websocket_reconnect_tasks: dict[str, asyncio.Task | None] = {}

    async def _async_setup(self):
        my_system = await self._api.async_get_my_system()
        self.system_ids = self._extract_system_ids(my_system)

    def async_websockets_connect(self) -> None:
        self._home_websocket_reconnect_task = asyncio.create_task(self._async_start_home_websocket_loop())

        for system in self.system_ids[SveaSolarSystemType.EV]:
            system = next(iter(system))
            self._ev_websocket_reconnect_tasks[system] = asyncio.create_task(
                self._async_start_ev_websocket_loop(system)
            )

        async def async_websocket_disconnect_listener(_: Event) -> None:
            await self.async_websocket_disconnect()

        self._entry.async_on_unload(
            self._hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, async_websocket_disconnect_listener)
        )

        self._entry.async_on_unload(self.async_websocket_disconnect)

    async def async_websocket_disconnect(self):
        """Define an event handler to disconnect from the websocket."""
        await self._async_cancel_home_websocket_loop()
        for disconnect_system in self.system_ids[SveaSolarSystemType.EV]:
            disconnect_system = next(iter(disconnect_system))
            await self._async_cancel_ev_websocket_loop(disconnect_system)

    async def _async_start_home_websocket_loop(self) -> None:
        """Start a websocket reconnection loop."""
        try:
            await self.ws_battery_connect()
        except asyncio.CancelledError:
            _LOGGER.debug("Request to cancel websocket loop received")
            raise
        except WebsocketError as err:
            _LOGGER.error("Failed to connect to websocket: %s", err)
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Unknown exception while connecting to websocket: %s", err)

        _LOGGER.debug("Reconnecting to websocket")
        await self._async_cancel_home_websocket_loop()
        self._home_websocket_reconnect_task = self._hass.async_create_task(self._async_start_home_websocket_loop())

    async def _async_start_ev_websocket_loop(self, system: str) -> None:
        """Start a websocket reconnection loop."""
        try:
            await self.ws_ev_connect(system)
        except asyncio.CancelledError:
            _LOGGER.debug("Request to cancel websocket loop received")
            raise
        except WebsocketError as err:
            _LOGGER.error("Failed to connect to websocket: %s", err)
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Unknown exception while connecting to websocket: %s", err)

        _LOGGER.debug("Reconnecting to websocket")
        await self._async_cancel_ev_websocket_loop(system)
        self._websocket_reconnect_task = self._hass.async_create_task(self._async_start_home_websocket_loop())

    async def _async_cancel_home_websocket_loop(self) -> None:
        """Stop any existing websocket reconnection loop."""
        if self._home_websocket_reconnect_task:
            self._home_websocket_reconnect_task.cancel()
            try:
                await self._home_websocket_reconnect_task
            except asyncio.CancelledError:
                _LOGGER.debug("Websocket reconnection task successfully canceled")
                self._home_websocket_reconnect_task = None

            await self._api.async_home_websocket_disconnect()

    async def _async_cancel_ev_websocket_loop(self, system: str) -> None:
        """Stop any existing websocket reconnection loop."""
        if system in self._ev_websocket_reconnect_tasks.keys():
            task = self._ev_websocket_reconnect_tasks[system]
            if not task:
                return

            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                _LOGGER.debug("Websocket reconnection task successfully canceled")
                self._ev_websocket_reconnect_tasks[system] = None

            await self._api.async_ev_websocket_disconnect(system)

    async def _async_update_data(self):
        try:
            if len(self.system_ids[SveaSolarSystemType.BATTERY]) > 0:
                battery = await self._api.async_get_battery(next(iter(self.system_ids[SveaSolarSystemType.BATTERY][0])))
                self._battery_poll[battery.id] = battery

            my_data = await self._api.async_get_my_data()
            for location in my_data:
                self._location_poll[location.id] = location

            return self._data_update()
        except AuthenticationError as err:
            _LOGGER.warning(f"Failed to refresh token, trying to login again: {err}")
            await self.async_websocket_disconnect()
            await self._async_login()
            self.async_websockets_connect()
            return await self._async_update_data()
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")

    async def _async_login(self):
        try:
            await self._api.async_login(
                username=self._entry.data.get(CONF_USERNAME), password=self._entry.data.get(CONF_PASSWORD)
            )
        except ClientError as err:
            _LOGGER.warning(f"Failed to login. Raising Re-Auth: {err}")
            raise ConfigEntryAuthFailed from err
        except Exception as err:
            _LOGGER.warning(f"Failed to login due to exception: {err}")
            raise UpdateFailed from err

    async def ws_battery_connect(self):
        def on_keep_alive(msg):
            _LOGGER.debug("Keep Alive from SveaSolar Home WS")

        def on_connected():
            _LOGGER.debug("Connected to SveaSolar Home WS")

        def on_data(msg: BadgesUpdatedMessage):
            if msg.data.has_battery:
                battery: Battery = msg.data.battery
                _LOGGER.debug(f"Battery id: {battery.battery_id}")
                _LOGGER.debug(f"Battery name: {battery.name}")
                _LOGGER.debug(f"Battery status: {battery.status}")
                _LOGGER.debug(f"Battery SoC: {battery.state_of_charge}")

                self._battery_websocket[battery.battery_id] = battery

                self.async_set_updated_data(self._data_update())
                self.async_update_listeners()

        await self._api.async_home_websocket(
            data_callback=on_data, connected_callback=on_connected, keep_alive_callback=on_keep_alive
        )

    async def ws_ev_connect(self, ev_id: str):
        def on_connected():
            _LOGGER.debug("Connected to SveaSolar EV WS")

        def on_data(msg: VehicleDetailsUpdatedMessage):
            ev: VehicleDetailsData = msg.data
            _LOGGER.debug(f"EV id: {ev.id}")
            _LOGGER.debug(f"EV name: {ev.name}")
            _LOGGER.debug(f"EV charging status: {ev.vehicleStatus.chargingStatus}")
            _LOGGER.debug(f"EV battery status: {ev.vehicleStatus.batteryLevel}")

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
    def __init__(self, hass: HomeAssistant, entry: SveaSolarConfigEntry):
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
