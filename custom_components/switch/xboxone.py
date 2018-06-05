"""
Support Xbox One Power On and Off

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/switch.xboxone/
"""
import logging
import uuid
import sys, socket, select, time, json
import subprocess
import voluptuous as vol

from homeassistant.components.switch import (SwitchDevice, PLATFORM_SCHEMA)
from homeassistant.const import CONF_IP_ADDRESS, CONF_NAME,  STATE_OFF, STATE_ON
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

CONF_LIVE_ID = "live device id"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_NAME): cv.string,
    vol.Inclusive(CONF_IP_ADDRESS, 'ip_address'): cv.string,
    vol.Inclusive(CONF_LIVE_ID, 'xbox_live'): cv.string
})

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up xbox."""
    ip_address = config.get(CONF_IP_ADDRESS)
    live_id = config.get(CONF_LIVE_ID)
    name = config.get(CONF_NAME)
    add_devices([XboxOne(hass, live_id, ip_address, name, STATE_OFF)])

class XboxOne(SwitchDevice):
    """Representation of a Xbox One device, allowing on and off commands."""

    def __init__(self, hass, live_id, ip, name, state):
        """Initialize the switch."""
        self.hass = hass
        self._live_id = live_id
        self._ip = ip
        self._name = name
        self._state = state
        self.discover()

    @property
    def name(self):
        """Return the display name of this Xbox."""
        return self._name

    @property
    def state(self):
        """Return _state variable, containing the appropriate constant."""
        return self._state

    def update(self, **kwargs):
        self.discover()

    def discover(self):
        command = f"xbox-discover --address { self._ip }" 
        response = str(subprocess.check_output(command, shell=True))
        if len(response) > 55:
            self._state = STATE_ON
        else:
            self._state = STATE_OFF

    def turn_on(self, **kwargs):
        command = f"xbox-poweron { self._live_id } --address { self._ip }" 
        (subprocess.call(command, shell=True) == 0)  

    def turn_off(self, **kwargs):
        command = f"xbox-poweroff --liveid { self._live_id }" 
        (subprocess.call(command, shell=True) == 0)  
    