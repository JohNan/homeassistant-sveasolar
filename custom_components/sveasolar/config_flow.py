import logging
from typing import Any, Mapping

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD, CONF_ACCESS_TOKEN
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pysveasolar.api import SveaSolarAPI
from pysveasolar.token_manager import TokenManager

from .const import DOMAIN, CONF_REFRESH_TOKEN, CONFIG_FLOW_TITLE

_LOGGER: logging.Logger = logging.getLogger(__package__)


class SveaSolarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    entry: ConfigEntry

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize."""
        self._errors = {}
        self._token_manager = SveaSolarConfigFlowTokenManager()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        self._errors = {}
        _LOGGER.debug(user_input)
        if user_input is not None:
            try:
                await self._test_credentials(user_input[CONF_USERNAME], user_input[CONF_PASSWORD])

                # Copy the maybe possibly credentials
                user_input[CONF_ACCESS_TOKEN] = self._token_manager.access_token
                user_input[CONF_REFRESH_TOKEN] = self._token_manager.refresh_token
            except Exception as exp:  # pylint: disable=broad-except
                _LOGGER.error("Validating credentials failed - %s", exp)
                self._errors["base"] = "auth"
                return await self._show_config_form(user_input)

            return self.async_create_entry(title=CONFIG_FLOW_TITLE, data={**user_input})

        return await self._show_config_form(user_input)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """Handle configuration by re-auth."""
        if entry := self.hass.config_entries.async_get_entry(self.context["entry_id"]):
            self.entry = entry
        return await self.async_step_reauth_validate()

    async def async_step_reauth_validate(self, user_input=None) -> ConfigFlowResult:
        """Handle reauth and validation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await self._test_credentials(user_input[CONF_USERNAME], user_input[CONF_PASSWORD])

                # Copy the maybe possibly credentials
                user_input[CONF_ACCESS_TOKEN] = self._token_manager.access_token
                user_input[CONF_REFRESH_TOKEN] = self._token_manager.refresh_token
            except Exception as exp:  # pylint: disable=broad-except
                _LOGGER.error("Validating credentials failed - %s", exp)

            return self.async_update_reload_and_abort(
                self.entry,
                data={**user_input},
            )

        return self.async_show_form(
            step_id="reauth_validate",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME, default=self.entry.data.get(CONF_USERNAME, "")): str,
                    vol.Required(CONF_PASSWORD, default=self.entry.data.get(CONF_PASSWORD, "")): str,
                }
            ),
            errors=errors,
        )

    async def _show_config_form(self, user_input):  # pylint: disable=unused-argument
        """Show the configuration form to set credentials."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=self._errors,
        )

    async def _test_credentials(self, username: str, password: str):
        """Return true if credentials is valid."""

        client = SveaSolarAPI(session=async_get_clientsession(self.hass), token_manager=self._token_manager)
        await client.async_login(username, password)


class SveaSolarConfigFlowTokenManager(TokenManager):
    """TokenManager implementation for config flow"""

    def __init__(self):
        pass

    def update(self, access_token: str, refresh_token: str):
        super().update(access_token, refresh_token)
