"""Config flow for Sipeed NanoKVM integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import AbortFlow, FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.components import zeroconf

from nanokvm.client import NanoKVMClient, NanoKVMAuthenticationFailure, NanoKVMError
from nanokvm.models import GetInfoRsp

from cachetools import TTLCache

from .const import DEFAULT_USERNAME, DEFAULT_PASSWORD, DOMAIN

_LOGGER = logging.getLogger(__name__)

async def _async_get_nanokvm_device_info(
    hass: HomeAssistant, host: str
) -> tuple[GetInfoRsp, str] | None:
    """Attempt to connect to the device and retrieve its info without authentication."""
    url = f"http://{host}/api/"

    session = async_get_clientsession(hass)
    client = NanoKVMClient(url, session)

    try:
        # Attempt to authenticate with default credentials (admin/admin)
        await client.authenticate(DEFAULT_USERNAME, DEFAULT_PASSWORD)
        device_info = await client.get_info()
        
        # Use device_key as the unique identifier
        unique_id = device_info.device_key
        
        # Store in cache using URL and device_key for better lookup
        _LOGGER.debug(
            "Adding device %s to discovery cache with URL %s and device_key %s",
            device_info.mdns,
            url,
            unique_id
        )
        return device_info, unique_id
    except NanoKVMAuthenticationFailure:
        _LOGGER.debug(
            "Discovered NanoKVM device at %s requires user credentials.",
            url,
        )
        # If authentication fails, it's still a NanoKVM device, but we can't get device_info.
        # We'll let the flow continue to prompt for credentials.
        # To avoid repeated attempts for the same device, we can cache a "placeholder"
        # or simply return None and rely on the existing unique_id logic in async_step_zeroconf.
        # For now, returning None will cause async_step_zeroconf to use discovery_info.properties.get("id", name)
        # as the unique_id, which is acceptable.
        return None
    except (aiohttp.ClientError, NanoKVMError) as err:
        _LOGGER.debug("Failed to connect to %s during discovery: %s", url, err)
        return None

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    session = async_get_clientsession(hass)
    
    host = data[CONF_HOST]
    # Ensure the host has a scheme
    if not host.startswith(("http://", "https://")):
        host = f"http://{host}"
    
    # Ensure the host ends with /api/
    if not host.endswith("/api/"):
        host = f"{host}/api/" if host.endswith("/") else f"{host}/api/"

    client = NanoKVMClient(host, session)

    try:
        await client.authenticate(data[CONF_USERNAME], data[CONF_PASSWORD])
        device_info = await client.get_info()
        
        # For manual configuration, we use the device_key as the unique identifier
    except NanoKVMAuthenticationFailure as err:
        raise InvalidAuth from err
    except (aiohttp.ClientError, NanoKVMError) as err:
        raise CannotConnect from err

    # Return info that you want to store in the config entry.
    return {
        "title": f"NanoKVM ({device_info.mdns})", 
        "device_key": device_info.device_key,
        "unique_id": device_info.device_key
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sipeed NanoKVM."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_host: str | None = None
        self._discovered_name: str | None = None
        self._discovered_device_key: str | None = None
        self._discovered_unique_id: str | None = None
        self._default_auth_successful: bool = False # New flag
        
    @callback
    def _abort_if_unique_id_configured(self) -> None:
        """Abort if the unique ID is already configured."""
        if self.unique_id is None:
            return
        
        for entry in self._async_current_entries():
            if entry.unique_id == self.unique_id:
                _LOGGER.debug(
                    "Aborting flow because device with unique_id %s is already configured as %s",
                    self.unique_id,
                    entry.title
                )
                raise AbortFlow("already_configured")

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        
        # Define the schema for the form, with defaults from user_input if available
        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=user_input.get(CONF_HOST) if user_input else None): str,
                vol.Required(CONF_USERNAME, default=user_input.get(CONF_USERNAME, DEFAULT_USERNAME) if user_input else DEFAULT_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )
        
        if user_input is not None:
            # Ensure CONF_PASSWORD is always present, even if empty, to match schema for validation
            if CONF_PASSWORD not in user_input:
                user_input[CONF_PASSWORD] = ""
            
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Check if this device was discovered via zeroconf
                if user_input.get("discovered_via_zeroconf") and user_input.get("zeroconf_unique_id"):
                    # Use the zeroconf_unique_id as the unique_id
                    zeroconf_unique_id = user_input["zeroconf_unique_id"]
                    _LOGGER.debug(
                        "Using zeroconf_unique_id %s as unique_id for device discovered via zeroconf",
                        zeroconf_unique_id
                    )
                    await self.async_set_unique_id(zeroconf_unique_id)
                    
                    # Add the unique_id to the data
                    user_input["unique_id"] = zeroconf_unique_id
                else:
                    # Use device_key as the unique_id for manually configured devices
                    _LOGGER.debug(
                        "Using device_key %s as unique_id for manually configured device",
                        info["device_key"]
                    )
                    await self.async_set_unique_id(info["device_key"])
                    
                    # Add the unique_id to the data
                    user_input["unique_id"] = info["device_key"]
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )

    async def async_step_zeroconf(
        self, discovery_info: zeroconf.ZeroconfServiceInfo
    ) -> FlowResult:
        """Handle zeroconf discovery."""
        host = discovery_info.host
        name = discovery_info.name.split(".")[0]
        
        # Get the zeroconf unique ID from properties or use the name
        zeroconf_unique_id = discovery_info.properties.get("id", name)
        
        # Attempt to get device info with default credentials
        result = await _async_get_nanokvm_device_info(self.hass, host)

        # Store discovered info
        self._discovered_host = discovery_info.hostname
        
        if result:
            device_info, device_key = result
            # If we successfully got device_info, use its mDNS name and device_key
            self._discovered_name = device_info.mdns
            self._discovered_device_key = device_key
            self._discovered_unique_id = zeroconf_unique_id
            self._default_auth_successful = True # Default auth succeeded
            
            # Use zeroconf_unique_id as the unique_id for consistency
            _LOGGER.debug(
                "Using zeroconf_unique_id %s as unique_id for device %s",
                zeroconf_unique_id,
                self._discovered_name
            )
            
            # Check if a device with this unique_id is already configured
            await self.async_set_unique_id(zeroconf_unique_id)
            
            # Check if this device is already configured
            for entry in self._async_current_entries():
                if entry.unique_id == zeroconf_unique_id:
                    _LOGGER.debug(
                        "Device with unique_id %s is already configured as %s",
                        zeroconf_unique_id,
                        entry.title
                    )
                    return self.async_abort(reason="already_configured")
                
                # Also check if the unique_id is stored in the entry data
                if entry.data.get("unique_id") == zeroconf_unique_id:
                    _LOGGER.debug(
                        "Device with unique_id %s is already configured as %s (from entry data)",
                        zeroconf_unique_id,
                        entry.title
                    )
                    # Update the unique_id if it's different
                    if entry.unique_id != zeroconf_unique_id:
                        _LOGGER.debug(
                            "Updating unique_id from %s to %s for entry %s",
                            entry.unique_id,
                            zeroconf_unique_id,
                            entry.title
                        )
                        self.hass.config_entries.async_update_entry(
                            entry, unique_id=zeroconf_unique_id
                        )
                    return self.async_abort(reason="already_configured")
            
            # If we get here, the device is not configured yet
            self._abort_if_unique_id_configured()
        else:
            # If default credentials failed or other connection error,
            # use the name from zeroconf and fallback to zeroconf_unique_id for display/fallback unique_id
            self._discovered_name = name
            self._discovered_device_key = zeroconf_unique_id # Fallback unique_id for the entry
            self._discovered_unique_id = zeroconf_unique_id
            self._default_auth_successful = False # Default auth failed
            
            # Use zeroconf_unique_id as the unique_id
            _LOGGER.debug(
                "Using zeroconf_unique_id %s as unique_id for device %s",
                zeroconf_unique_id,
                self._discovered_name
            )
            await self.async_set_unique_id(zeroconf_unique_id)
            self._abort_if_unique_id_configured()
            
            _LOGGER.debug(
                "Could not get device info for %s, using zeroconf name '%s' for discovery",
                host,
                name,
            )

        # Set the title for the confirmation dialog
        self.context["title_placeholders"] = {"name": self._discovered_name}

        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initiated by zeroconf."""
        if user_input is not None:
            if self._default_auth_successful:
                # If default authentication succeeded, create entry directly
                # We need to reconstruct the data that validate_input expects
                data = {
                    CONF_HOST: self._discovered_host,
                    CONF_USERNAME: DEFAULT_USERNAME,
                    CONF_PASSWORD: DEFAULT_PASSWORD,
                    "unique_id": self._discovered_unique_id, # Store the unique_id in the entry data
                }
                try:
                    info = await validate_input(self.hass, data)
                except CannotConnect:
                    return self.async_abort(reason="cannot_connect")
                except InvalidAuth:
                    # This should not happen if _default_auth_successful is True
                    _LOGGER.error("Unexpected authentication failure after successful default auth")
                    return self.async_abort(reason="unknown")
                except Exception:
                    _LOGGER.exception("Unexpected exception during direct entry creation")
                    return self.async_abort(reason="unknown")
                
                # The unique_id is already set in async_step_zeroconf
                return self.async_create_entry(
                    title=info["title"], 
                    data=data
                )
            else:
                # If default authentication failed, proceed to user step to ask for credentials
                # Pass the zeroconf_unique_id to ensure it's used as the unique_id
                return await self.async_step_user(
                    {
                        CONF_HOST: self._discovered_host,
                        CONF_USERNAME: DEFAULT_USERNAME,
                        # Do NOT pre-fill password, let the user enter it
                        "discovered_via_zeroconf": True,
                        "zeroconf_unique_id": self._discovered_unique_id,
                    }
                )

        return self.async_show_form(
            step_id="zeroconf_confirm",
            description_placeholders={"name": self._discovered_name},
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
