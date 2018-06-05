"""
Add support for the Xbox One consoles.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/xbox_one/
"""

import logging
import uuid
import voluptuous as vol
# import asyncio
import homeassistant.helpers.config_validation as cv
from homeassistant.const import (CONF_NAME, STATE_OFF, STATE_ON, CONF_IP_ADDRESS)
from homeassistant.components.media_player import (
    SUPPORT_TURN_ON, SUPPORT_TURN_OFF, MediaPlayerDevice, PLATFORM_SCHEMA,
    SUPPORT_VOLUME_STEP)

REQUIREMENTS = ['xbox-smartglass-core==1.0.7']

DOMAIN = 'xboxone'

_LOGGER = logging.getLogger(__name__)

SUPPORT_XBOX_ONE = SUPPORT_VOLUME_STEP | SUPPORT_TURN_ON | \
                    SUPPORT_TURN_OFF

DEFAULT_NAME = "Xbox One"
DEFAULT_TOKEN_FILE = 'tokens.json'
CONF_LIVE_ID = "live device id"
CONF_TOKEN_FILE = "xbox token file"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_IP_ADDRESS): cv.string,
    vol.Required(CONF_LIVE_ID): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_TOKEN_FILE, default=DEFAULT_TOKEN_FILE): cv.string
})


#@asyncio.coroutine
def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Xbox One platform"""
    from xbox.webapi.authentication.manager import AuthenticationManager
    from xbox.sg.enum import ConnectionState
    from xbox.sg.console import Console
    hass.loop.set_debug(True)
    ip_address = config.get(CONF_IP_ADDRESS)
    live_id = config.get(CONF_LIVE_ID)
    name = config.get(CONF_NAME)
    tokens_file_name = hass.config.path(config.get(CONF_TOKEN_FILE))

    try:
        auth_mgr = AuthenticationManager.from_file(tokens_file_name)
        auth_mgr.authenticate(do_refresh=False)  
        auth_mgr.dump(tokens_file_name)
    except Exception as e:
        _LOGGER.error(e)

    # userhash = auth_mgr.userinfo.userhash
    # token = auth_mgr.xsts_token.jwt

    # consoles = Console.discover(timeout=1, addr=ip_address)

    # if not len(consoles):
    initial_state = STATE_OFF
    add_devices([XboxOne(auth_mgr, live_id, ip_address, name, initial_state)])
    # else: 
    #     consoles = [c for c in consoles if c.liveid == live_id]
    #     initial_state = STATE_ON 
    #     for c in consoles:
    #         state = c.connect(userhash, token)
    #         if state != ConnectionState.Connected:
    #             _LOGGER.error("Connecting to %s failed" % c)                
    #         else:
    #             async_add_devices([XboxOne(auth_mgr, live_id, ip_address, name, initial_state, c)])

class XboxOne(MediaPlayerDevice):
    """Represent the Xbox One for Home Assistant."""

    def __init__(self, auth_mgr, live_id, ip_address, name, state, console=None):
        """Receive IP address and name to construct class."""
        self._auth_mgr = auth_mgr
        self._live_id = live_id
        self._ip_address = ip_address        
        self._name = name
        self._state = state
        self._console = console
        self.update()

    @property
    def name(self):
        """Return the display name of this Xbox."""
        return self._name

    @property
    def state(self):
        """Return _state variable, containing the appropriate constant."""
        return self._state

    @property
    def assumed_state(self):
        """Indicate that state is assumed."""
        return True

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        return SUPPORT_XBOX_ONE

    #@asyncio.coroutine
    def update(self):
        from xbox.sg.enum import ConnectionState
        from xbox.sg.console import Console
        userhash = self._auth_mgr.userinfo.userhash
        token = self._auth_mgr.xsts_token.jwt

        if self._console is None:
            consoles = Console.discover(timeout=1, addr=self._ip_address)
            if len(consoles):
                consoles = [c for c in consoles if c.liveid == self._live_id]
            if not len(consoles):                
                self._state = STATE_OFF
            else:
                for c in consoles:
                    state = c.connect(userhash, token)
                    if state != ConnectionState.Connected:
                        _LOGGER.error("Connecting to %s failed" % c)
                        self._state = STATE_OFF
                        continue
                    self._state = STATE_ON
                    self._console = c

    #@asyncio.coroutine
    def turn_off(self):
        """
        Instruct the Xbox to turn off
        """
        from xbox.sg.enum import ConnectionState
        from xbox.sg.console import Console
        userhash = self._auth_mgr.userinfo.userhash
        token = self._auth_mgr.xsts_token.jwt

        # _LOGGER.warn(f'userhash { userhash } and token { token }')
        #_LOGGER.warn(f'About to turn off { self._name } on ip { self._ip_address } with live id { self._live_id }!')
        
        if self._console is None:
            consoles = Console.discover(timeout=1, addr=self._ip_address)
            if len(consoles):
                consoles = [c for c in consoles if c.liveid == self._live_id]
            if not len(consoles):
                _LOGGER.error("No console found.")  
            else:
                for c in consoles:
                    state = c.connect(userhash, token)
                    if state != ConnectionState.Connected:
                        _LOGGER.error("Connecting to %s failed" % c)
                        continue
                    c.wait(1)
                    c.power_off()
                    self._state = STATE_OFF
        else:
            self._console.power_off()
            self._state = STATE_OFF

    #@asyncio.coroutine
    def turn_on(self):
        """Turn on the Xbox."""
        # _LOGGER.warn(f'About to turn on { self._name } on ip { self._ip_address } with live id { self._live_id }!')
        # from xbox.sg.console import Console
        # from xbox.sg.enum import ConnectionState
        from xbox.sg.console import Console

        Console.power_on(self._live_id, self._ip_address, tries=5)
        #self.async_update()
        # userhash = self._auth_mgr.userinfo.userhash
        # token = self._auth_mgr.xsts_token.jwt

        # consoles = Console.discover(timeout=1, addr=self._ip_address)
        # if not len(consoles):
        #     self._state = STATE_OFF
        # else: 
        #     consoles = [c for c in consoles if c.liveid == self._live_id]
        #     self._state = STATE_ON
        #     for c in consoles:
        #         state = c.connect(userhash, token)
        #         if state != ConnectionState.Connected:
        #             _LOGGER.error("Connecting to %s failed" % c)
        #             continue
        

    # def volume_up(self):
    #     """Increase volume by one."""
    #     self._consoles.volume_up()

    # def volume_down(self):
    #     """Decrease volume by one."""
    #     self._consoles.volume_down()
