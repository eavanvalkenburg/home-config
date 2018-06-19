"""
Brunt Blind Component.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/
"""
import asyncio
import logging
import threading
import requests
import voluptuous as vol
import json
from brunt.brunt import BruntAPI

from homeassistant.helpers import discovery
from homeassistant.exceptions import HomeAssistantError
from homeassistant.core import callback
from homeassistant.const import (
    CONF_NAME, CONF_USERNAME, CONF_PASSWORD, CONF_DEVICE)
from homeassistant.components.cover import (
    CoverDevice, SUPPORT_OPEN, SUPPORT_CLOSE, SUPPORT_SET_POSITION,
    ATTR_POSITION, PLATFORM_SCHEMA, SERVICE_OPEN_COVER, SERVICE_CLOSE_COVER, SERVICE_SET_COVER_POSITION,
    SERVICE_STOP_COVER, STATE_OPEN, STATE_CLOSED)
from homeassistant.helpers.entity import Entity
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = ['brunt==0.0.3']

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'brunt'

OPEN_CLOSE_FEATURES = SUPPORT_OPEN | SUPPORT_CLOSE 

DEFAULT_CLOSED_POSITION = 0
DEFAULT_OPEN_POSITION = 100
DEFAULT_OPEN = 'OPEN'
DEFAULT_CLOSE = 'CLOSE'
DEFAULT_PARTIAL = 'PARTIALLY OPEN'
CONF_CLOSED_POSITION = 'closed_value'
CONF_OPEN_POSITION = 'opened_value'
CONF_OPEN = 'open'
CONF_CLOSE = 'close'
CONF_PARTIAL = 'partially_open'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({     
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_DEVICE): cv.string,
        vol.Optional(CONF_CLOSED_POSITION,
                 default=DEFAULT_CLOSED_POSITION): int,
        vol.Optional(CONF_OPEN_POSITION,
                 default=DEFAULT_OPEN_POSITION): int,
        vol.Optional(CONF_OPEN,
                 default=DEFAULT_OPEN): cv.string,
        vol.Optional(CONF_CLOSE,
                 default=DEFAULT_CLOSE): cv.string,
        vol.Optional(CONF_PARTIAL,
                 default=DEFAULT_PARTIAL): cv.string
})

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the brunt component."""
    from brunt.brunt import BruntAPI
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)
    device = config.get(CONF_DEVICE)
    name = config.get(CONF_NAME)

    closed_position = config.get(CONF_CLOSED_POSITION)
    open_position = config.get(CONF_OPEN_POSITION)
    opened = config.get(CONF_OPEN)
    close = config.get(CONF_CLOSE)
    partial = config.get(CONF_PARTIAL)

    add_devices([BruntDevice(hass, username, password, name, device, closed_position, open_position, opened, close, partial)])


class BruntDevice(CoverDevice):
    """Representation of a Brunt cover device.

    Contains the common logic for all Brunt devices.
    """

    def __init__(self, hass, username, password, name, device, closed_position, open_position, opened, close, partial):
        """Init the Brunt device."""
        from brunt.brunt import BruntAPI
        self._username = username
        self._password = password
        self._name = name
        self._device = device

        self._closed_position = closed_position
        self._open_position = open_position
        self._open = opened
        self._close = close
        self._partial = partial

        self._bapi = BruntAPI()
        self._bapi.login(self._username, self._password)
        res = self._bapi.getThings()
        if len(res) == 0:
            raise HomeAssistantError
        self._position = None
        self._state = None
        self._update()

    @property
    def name(self):
        """Return the name of the device as reported by tellcore."""
        return self._name

    @property
    def is_on(self):
        """Return true if the device is on."""
        return self._state

    def _update(self):
        """Poll the current state of the device."""
        state = self._bapi.getState(self._device)
        self._position = state['currentPosition']
        if self._position == self._closed_position:
            self._state = self._open
        elif self._position == self._closed_position:
            self._state = self._close
        else:
            self._state = self._partial

    @property
    def state(self):
        """Return the state of the cover."""
        return STATE_CLOSED if self._state == self._close else STATE_OPEN

    def open_cover(self, **kwargs):
        self._bapi.changePosition(self._device, self._open_position)

    def close_cover(self, **kwargs):
        self._bapi.changePosition(self._device, self._closed_position)

    def stop_cover(self, **kwargs):
        self.update()
        self._bapi.changePosition(self._device, self._position)

    def set_cover_position(self, **kwargs):
        if ATTR_POSITION in kwargs:
            position = kwargs[ATTR_POSITION]
            self._bapi.changePosition(self._device, position)
    
    @property
    def current_cover_position(self):
        """Return current position of cover.
        None is unknown, 0 is closed, 100 is fully open.
        """
        return self._position

    def is_closed(self):
        return self._position == self._closed_position

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return 'window'
    
    @property
    def supported_features(self):
        """Flag supported features."""
        supported_features = 0
        supported_features = OPEN_CLOSE_FEATURES
        supported_features |= SUPPORT_SET_POSITION

        return supported_features