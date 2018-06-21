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
import time

from homeassistant.helpers import discovery
from homeassistant.exceptions import HomeAssistantError
from homeassistant.core import callback
from homeassistant.const import (
    CONF_NAME, CONF_USERNAME, CONF_PASSWORD) #, CONF_DEVICE)
from homeassistant.components.cover import (
    CoverDevice, SUPPORT_OPEN, SUPPORT_CLOSE, SUPPORT_SET_POSITION,
    ATTR_POSITION, PLATFORM_SCHEMA, SERVICE_OPEN_COVER, SERVICE_CLOSE_COVER, SERVICE_SET_COVER_POSITION,
    SERVICE_STOP_COVER, STATE_OPEN, STATE_CLOSED)
from homeassistant.helpers.entity import Entity
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = ['brunt==0.1.2']

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'brunt'

COVER_FEATURES = SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_SET_POSITION

ATTR_COVER_STATE = 'cover_state'
DEFAULT_NAME = 'brunt blind engine'
NOTIFICATION_ID = 'brunt_notification'
NOTIFICATION_TITLE = 'Brunt Cover Setup'

CLOSED_POSITION = 0
OPEN_POSITION = 100
# CONF_CLOSED_POSITION = 'closed_value'
# CONF_OPEN_POSITION = 'opened_value'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({     
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string
        # vol.Required(CONF_DEVICE): cv.string,
        # vol.Optional(CONF_CLOSED_POSITION,
        #          default=DEFAULT_CLOSED_POSITION): int,
        # vol.Optional(CONF_OPEN_POSITION,
        #          default=DEFAULT_OPEN_POSITION): int
})

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the brunt component."""
    from brunt import BruntAPI
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)
    name = config.get(CONF_NAME)
    # device = config.get(CONF_DEVICE)
    # name = config.get(CONF_NAME)

    # closed_position = config.get(CONF_CLOSED_POSITION)
    # open_position = config.get(CONF_OPEN_POSITION)

    bapi = BruntAPI()
    bapi.login(username, password)
    try:
        things = bapi.getThings()['things']
        if len(things) == 0:
            raise HomeAssistantError

        add_devices(BruntDevice(
                hass, bapi, thing['NAME'], thing['thingUri']) for thing in things)
    except (TypeError, KeyError, NameError, ValueError) as ex:
        _LOGGER.error("%s", ex)
        hass.components.persistent_notification.create(
            'Error: {}<br />'
            'You will need to restart hass after fixing.'
            ''.format(ex),
            title=NOTIFICATION_TITLE,
            notification_id=NOTIFICATION_ID)


class BruntDevice(CoverDevice):
    """Representation of a Brunt cover device.

    Contains the common logic for all Brunt devices.
    """

    # def __init__(self, hass, username, password, name, device, closed_position, open_position):
    def __init__(self, hass, bapi, name, thingUri):
        """Init the Brunt device."""
        from brunt import BruntAPI
        # self._username = username
        # self._password = password
        self._name = name
        self._thingUri = thingUri
        # self._device = device

        # self._closed_position = closed_position
        # self._open_position = open_position
        self._bapi = bapi

        # res = self._bapi.getThings()['things']
        # if len(res) == 0:
        #     raise HomeAssistantError
        self._position = None
        self._movestate = None
        self._available = None
        self.update()

    @property
    def name(self):
        """Return the name of the device as reported by tellcore."""
        return self._name

    @property
    def available(self):
        """Could the device be accessed during the last update call."""
        return self._available

    @property
    def device_state_attributes(self):
        """Return the device state attributes."""
        data = {}

        if self._movestate == 1:
            data[ATTR_COVER_STATE] = 'OPENING'
        elif self._movestate == 2:
            data[ATTR_COVER_STATE] = 'CLOSING'
        elif self.is_closed():
            data[ATTR_COVER_STATE] = 'CLOSED'
        elif int(self._position) == OPEN_POSITION:
            data[ATTR_COVER_STATE] = 'OPENED'
        else:            
            data[ATTR_COVER_STATE] = 'PARTIALLY OPENED'

        return data

    @property
    def is_on(self):
        """Return true if the device is on."""
        return True

    @property
    def state(self):
        """Return the state of the cover."""
        return STATE_CLOSED if self.is_closed() else STATE_OPEN

    @property
    def current_cover_position(self):
        """Return current position of cover.
        None is unknown, 0 is closed, 100 is fully open.
        """
        return self._position

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return 'window'
    
    @property
    def supported_features(self):
        """Flag supported features."""
        return COVER_FEATURES

    def update(self):
        """Poll the current state of the device."""
        try:
            self._position = int(self._bapi.getState(thingUri=self._thingUri)['thing']['currentPosition'])
            self._movestate = int(self._bapi.getState(thingUri=self._thingUri)['thing']['moveState'])
            self._available = True
        except (TypeError, KeyError, NameError, ValueError) as ex:
            _LOGGER.error("%s", ex)
            self._available = False

    def is_closed(self):
        return self._position == CLOSED_POSITION

    def open_cover(self, **kwargs):
        # try:
        self._bapi.changePosition(OPEN_POSITION, thingUri=self._thingUri)
        time.sleep(2)
        self.update()
        # except:
        #     return False

    def close_cover(self, **kwargs):
        # try:
        self._bapi.changePosition(CLOSED_POSITION, thingUri=self._thingUri)
        time.sleep(2)
        self.update()
        # except:
        #     return False

    def set_cover_position(self, **kwargs):
        if ATTR_POSITION in kwargs:
            # try:
            self._bapi.changePosition(int(kwargs[ATTR_POSITION]), thingUri=self._thingUri)
            time.sleep(2)
            self.update()
            # except:
                # return False
    