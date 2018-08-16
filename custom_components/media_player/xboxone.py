"""
Add support for the Xbox One consoles.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/xbox_one/
"""

import logging
import uuid
import voluptuous as vol
from datetime import timedelta
import asyncio

import homeassistant.helpers.config_validation as cv
from homeassistant.const import (CONF_NAME, STATE_OFF, STATE_ON, CONF_IP_ADDRESS)
from homeassistant.components.media_player import (
    SUPPORT_TURN_ON, SUPPORT_TURN_OFF, MediaPlayerDevice, PLATFORM_SCHEMA,
    SUPPORT_VOLUME_STEP, SUPPORT_PLAY)
# from homeassistant.util import Throttle

REQUIREMENTS = ['xbox-smartglass-core==1.0.8']

DOMAIN = 'xboxone'

_LOGGER = logging.getLogger(__name__)

SUPPORT_XBOX_ONE = SUPPORT_VOLUME_STEP | SUPPORT_TURN_ON | \
                    SUPPORT_TURN_OFF | SUPPORT_PLAY

# MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=1)
DEFAULT_NAME = "Xbox One"
DEFAULT_TOKEN_FILE = 'xbox-tokens.json'
CONF_LIVE_ID = "live_device_id"
CONF_TOKEN_FILE = "xbox_token_file"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_IP_ADDRESS): cv.string,
    vol.Required(CONF_LIVE_ID): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_TOKEN_FILE, default=DEFAULT_TOKEN_FILE): cv.string
})

@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up the Xbox One platform"""
    from xbox.webapi.authentication.manager import AuthenticationManager
    from xbox.sg.enum import ConnectionState
    from xbox.sg.console import Console
    hass.loop.set_debug(True)
    ip_address = config.get(CONF_IP_ADDRESS)
    live_id = config.get(CONF_LIVE_ID)
    name = config.get(CONF_NAME)
    tokens_file_name = hass.config.path(config.get(CONF_TOKEN_FILE))
    _LOGGER.debug('Trying to authenticate')
    try:
        auth_mgr = AuthenticationManager.from_file(tokens_file_name)
        auth_mgr.authenticate(do_refresh=False)  
        auth_mgr.dump(tokens_file_name)
    except Exception as e:
        _LOGGER.error(e)

    _LOGGER.debug('Authenticated, starting discovery.')
    consoles = Console.discover(timeout=1, addr=ip_address)

    if not consoles:
        _LOGGER.debug('No consoles found, could be turned off')
        async_add_devices([XboxOne(auth_mgr, live_id, ip_address, name)])
    else:
        async_add_devices([XboxOne(auth_mgr, live_id, ip_address, name, console) for console in consoles if console.liveid == live_id])


class XboxOne(MediaPlayerDevice):
    """Represent the Xbox One for Home Assistant."""

    def __init__(self, auth_mgr, live_id, ip_address, name, console=None):
        """Receive IP address and name to construct class."""
        _LOGGER.debug(f'Setting up {name}')
        self._auth_mgr = auth_mgr
        self._console = console
        self._state = None
        self._live_id = live_id
        self._ip_address = ip_address
        self._name = name

    @property
    def name(self):
        """Return the display name of this Xbox."""
        return self._name

    @property
    def connected(self):
        """return true if the console is connected"""
        return self._console.connected if self._console else False

    @property
    def state(self):
        """Return _state variable, containing the appropriate constant."""
        return STATE_ON if self._console else STATE_OFF

    @property
    def device_state_attributes(self):
        return { CONF_IP_ADDRESS: self._ip_address }

    @property
    def assumed_state(self):
        """Indicate that state is assumed."""
        return True

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        return SUPPORT_XBOX_ONE

    # @Throttle(MIN_TIME_BETWEEN_UPDATES)
    @asyncio.coroutine
    def async_update(self):
        from xbox.sg.console import Console
        from xbox.sg.manager import MediaManager
        userhash = self._auth_mgr.userinfo.userhash
        token = self._auth_mgr.xsts_token.jwt
        _LOGGER.debug(f'Start update')

        if self._console:
            _LOGGER.debug(f'Console is present: {self._console.to_dict()} and {self._console.connected}')
            if not self.connected:
                self._console.add_manager(MediaManager)
                self._console.connect(userhash=userhash, xsts_token=token)
            if self.connected:
                active_media = self._console.media.active_media
                title_id = self._console.media.title_id
                aum_id = self._console.media.aum_id
                asset_id = self._console.media.asset_id
                media_type = self._console.media.media_type
                sound_level = self._console.media.sound_level
                playback_status = self._console.media.playback_status
                position = self._console.media.position
                media_start = self._console.media.media_start
                metadata = self._console.media.metadata
                _LOGGER.debug(f'The active_media is {active_media}.')
                _LOGGER.debug(f'The title_id is {title_id}.')
                _LOGGER.debug(f'The aum_id is {aum_id}.')
                _LOGGER.debug(f'The asset_id is {asset_id}.')
                _LOGGER.debug(f'The media_type is {media_type}.')
                _LOGGER.debug(f'The sound_level is {active_media}.')
                _LOGGER.debug(f'The playback_status is {playback_status}.')
                _LOGGER.debug(f'The position is {position}.')
                _LOGGER.debug(f'The media_start is {media_start}.')
                _LOGGER.debug(f'The metadata is {metadata}.')
        else:
            consoles = Console.discover(timeout=1, addr=self._ip_address)
            if consoles:
                filtered_cons = [c for c in consoles if c.liveid == self._live_id]
                if filtered_cons:
                    _LOGGER.debug('Console discovered during update.')
                    self._console = filtered_cons[0]
        _LOGGER.debug(f'End update')

    # @asyncio.coroutine
    def turn_off(self):
        """Instruct the Xbox to turn off."""
        _LOGGER.debug(f'About to turn off { self._name } on ip { self._ip_address } with live id { self._live_id }!')
        self._console.power_off()
        self._console = None

    # @asyncio.coroutine
    def turn_on(self):
        """Turn on the Xbox."""
        from xbox.sg.console import Console
        _LOGGER.debug(f'About to turn on { self._name } on ip { self._ip_address } with live id { self._live_id }!')
        Console.power_on(self._live_id, addr=self._ip_address, tries=10)

    def media_play(self):
        from xbox.sg.enum import MediaControlCommand
        if self.connected:
            self._console.media_command(0x54321, MediaControlCommand.Play, 0)

    # def volume_up(self):
    #     """Increase volume by one."""
    #     self._consoles.volume_up()

    # def volume_down(self):
    #     """Decrease volume by one."""
    #     self._consoles.volume_down()
