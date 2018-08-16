"""
Support for Brunt Blind Engine covers.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/cover.brunt
"""

import logging

import voluptuous as vol

from homeassistant.const import (
    CONF_PASSWORD, CONF_USERNAME)
from homeassistant.components.cover import (
    ATTR_POSITION, CoverDevice,
    PLATFORM_SCHEMA, SUPPORT_CLOSE,
    SUPPORT_OPEN, SUPPORT_SET_POSITION
)
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = ['brunt==0.1.2']

_LOGGER = logging.getLogger(__name__)

ATTRIBUTION = 'Based on an unofficial Brunt SDK.'

COVER_FEATURES = SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_SET_POSITION
DEVICE_CLASS = 'window'

STATE_PARTIALLY_OPEN = 'partially open'
ATTR_REQUEST_POSITION = 'request_position'
DEFAULT_NAME = 'brunt blind engine'
NOTIFICATION_ID = 'brunt_notification'
NOTIFICATION_TITLE = 'Brunt Cover Setup'

CLOSED_POSITION = 0
OPEN_POSITION = 100

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the brunt platform."""
    # pylint: disable=no-name-in-module
    from brunt import BruntAPI
    username = config[CONF_USERNAME]
    password = config[CONF_PASSWORD]

    bapi = BruntAPI(username=username, password=password)
    try:
        things = bapi.getThings()['things']
        if not things:
            _LOGGER.error("No things present in account.")
        else:
            add_devices([BruntDevice(
                bapi, thing['NAME'],
                thing['thingUri']) for thing in things], True)
    except (TypeError, KeyError, NameError, ValueError) as ex:
        _LOGGER.error("%s", ex)
        hass.components.persistent_notification.create(
            'Error: {}<br />'
            'You will need to restart hass after fixing.'
            ''.format(ex),
            title=NOTIFICATION_TITLE,
            notification_id=NOTIFICATION_ID)


class BruntDevice(CoverDevice):
    """
    Representation of a Brunt cover device.

    Contains the common logic for all Brunt devices.
    """

    def __init__(self, bapi, name, thing_uri):
        """Init the Brunt device."""
        self._bapi = bapi
        self._name = name
        self._thing_uri = thing_uri

        self._state = {}
        self._available = None

    @property
    def name(self):
        """Return the name of the device as reported by tellcore."""
        return self._name

    @property
    def available(self):
        """Could the device be accessed during the last update call."""
        return self._available

    @property
    def current_cover_position(self):
        """
        Return current position of cover.

        None is unknown, 0 is closed, 100 is fully open.
        """
        pos = self._state.get('currentPosition', None)
        return int(pos) if pos else None

    @property
    def request_cover_position(self):
        """
        Return request position of cover.

        The request position is the position of the last request
        to Brunt, at times there is a diff of 1 to current
        None is unknown, 0 is closed, 100 is fully open.
        """
        pos = self._state.get('requestPosition', None)
        return int(pos) if pos else None

    @property
    def move_state(self):
        """
        Return current position of cover.

        None is unknown, 0 when stopped, 1 when opening, 2 when closing
        """
        mov = self._state.get('moveState', None)
        return int(mov) if mov else None

    @property
    def is_opening(self):
        """Return if the cover is opening or not."""
        return True if self.move_state == 1 else False

    @property
    def is_closing(self):
        """Return if the cover is closing or not."""
        return True if self.move_state == 2 else False

    @property
    def device_state_attributes(self):
        """Return the detailed device state attributes."""
        return {
            ATTR_REQUEST_POSITION: self.request_cover_position
        }

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return DEVICE_CLASS

    @property
    def supported_features(self):
        """Flag supported features."""
        return COVER_FEATURES

    @property
    def is_closed(self):
        """Return true if cover is closed, else False."""
        return self.current_cover_position == CLOSED_POSITION

    def update(self):
        """Poll the current state of the device."""
        try:
            self._state = self._bapi.getState(
                thingUri=self._thing_uri).get('thing')
            self._available = True
        except (TypeError, KeyError, NameError, ValueError) as ex:
            _LOGGER.error("%s", ex)
            self._available = False

    def open_cover(self, **kwargs):
        """Set the cover to the open position."""
        self._bapi.changeRequestPosition(
            OPEN_POSITION, thingUri=self._thing_uri)

    def close_cover(self, **kwargs):
        """Set the cover to the closed position."""
        self._bapi.changeRequestPosition(
            CLOSED_POSITION, thingUri=self._thing_uri)

    def set_cover_position(self, **kwargs):
        """Set the cover to a specific position."""
        self._bapi.changeRequestPosition(
            kwargs[ATTR_POSITION], thingUri=self._thing_uri)
