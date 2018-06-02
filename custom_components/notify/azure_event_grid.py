"""
Azure Event Grid platform for notify component.

For more details about this platform, please refer to the documentation at
TBD

Created by Eduard van Valkenburg
"""

import logging
from datetime import datetime
import uuid
import voluptuous as vol
import pytz

from homeassistant.const import CONF_HOST
from homeassistant.exceptions import HomeAssistantError
from homeassistant.components.notify import (ATTR_DATA, ATTR_TITLE,
    ATTR_TITLE_DEFAULT, PLATFORM_SCHEMA, BaseNotificationService)
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = ['azure.eventgrid==0.1.0', 'msrest==0.4.29']

_LOGGER = logging.getLogger(__name__)

CONF_TOPIC_KEY = 'topic key'
CONF_DATA_VERSION = 'data_version'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_DATA_VERSION, '1'): cv.string,
    vol.Inclusive(CONF_TOPIC_KEY, 'authentication'): cv.string
})

def get_service(hass, config, discovery_info=None):
    from azure.eventgrid import EventGridClient
    from msrest.authentication import TopicCredentials

    credentials = TopicCredentials(config[CONF_TOPIC_KEY])
    event_grid_client = EventGridClient(credentials)

    return AzureEventGrid(config[CONF_HOST], event_grid_client)

class AzureEventGrid(BaseNotificationService):
    """Implement the notification service for the azure event grid."""

    def __init__(self, endpoint, event_grid_client):
        """Initialize the service."""
        self.endpoint = endpoint
        self.client = event_grid_client

    def send_message(self, message="", **kwargs):
        #In order to match the Notify of the HA platform to the schema of Events in the Event Grid platform, this match was decided upon:
        # HA: Title maps to EG: Subject 
        # HA: Message maps to EG: Event Type
        # HA: Data maps to EG: Data
        # The rationale is that subject in EG is the thing that the event is about and since that defaults to Home Assistant this is true even then
        # The event typ is that happened with that Subject, a free text field and sometimes enough to further deal with the event (think sunset as Event Type aka message)
        # The data is the payload of the event, which is freely filled depending on need.
        # The other reason for this is the way in which Event Grid Subscriptions can be filtered, that can be done on Event Type or on a patterns match in the subject
        # this allows you to for instance route all events related to ha.lights.* to a specific endpoint regardless of the light that triggered

        data = kwargs.get(ATTR_DATA)
        title = data.get(ATTR_TITLE, ATTR_TITLE_DEFAULT)
        data_version = data.get(CONF_DATA_VERSION)

        #create the payload, with subject, message, data and type coming in from the notify platform
        payload = {
            'id' : str(uuid.uuid4()),
            'subject': title,
            'data': data,
            'event_type': message,
            'event_time': datetime.utcnow().replace(tzinfo=pytz.UTC),
            'data_version': data_version
        }

        #Send the event to event grid
        try:
            self.client.publish_events(
                self.endpoint,
                events=[payload]
            )
        except HomeAssistantError as err:
            _LOGGER.error("Unable to send event to Event Grid: %s", err)
