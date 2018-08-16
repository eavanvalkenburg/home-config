"""
Support for monitoring an Azure Event Grid subscription.
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.azure_event_grid/
"""
import logging
import asyncio

from custom_components.azure_event_grid import DOMAIN, FIELD_TYPES, ATTR_DATA_VERSION, ATTR_EVENT_TYPE, ATTR_PAYLOAD, ATTR_PAYLOAD_TEMPLATE, ATTR_SUBJECT
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity
from homeassistant.components.http import HomeAssistantView
from homeassistant.const import CONF_HOST, CONF_MONITORED_VARIABLES, CONF_PAYLOAD, CONF_NAME, HTTP_BAD_REQUEST, HTTP_UNAUTHORIZED, EVENT_STATE_CHANGED 

DEPENDENCIES = ['azure_event_grid']

LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_devices,
                               discovery_info=None):
    """Set up the AEG sensors."""
    if discovery_info is None:
        return
    # config = hass.data[DOMAIN]
    LOGGER.debug(config)
    LOGGER.debug(discovery_info)
    topics = config.data[DOMAIN]
    sensors = {}
    LOGGER.debug(topics)
    for topic in topics.items():
        mon_var = topic.topic[CONF_MONITORED_VARIABLES]
        for mon_var in topic.topic[CONF_MONITORED_VARIABLES]:
            sensors.update({'topic': topic, 'mon_var': mon_var})
    async_add_devices([AzureEventGridSensor(**sensors)])
    return True

class AzureEventGridSensor(Entity, HomeAssistantView):
    # url = EVENT_GRID_HTTP_ENDPOINT
    # name = EVENT_GRID_HTTP_NAME
    LOGGER.debug(f"Sensor: Create event grid sensor")

    def __init__(self, topic, mon_var):
        LOGGER.debug(f"Sensor: Setting up topic: {topic}")
        self._name = topic.name
        self._mon_var = mon_var
        self._state = None
        self._state_attributes = None

    @property
    def name(self):
        return f'{self._name}_{self._mon_var}'

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def device_state_attributes(self):
        """Return all known attributes of the sensor."""
        return self._state_attributes

    def should_poll(self):
        """Don't poll. Will be updated by dispatcher signal."""
        return False

    @asyncio.coroutine
    def post(self, request):
        # from azure.eventgrid.models import SubscriptionValidationResponse
        SubscriptionValidationEvent = "Microsoft.EventGrid.SubscriptionValidationEvent"
        LOGGER.debug(f"Sensor: Start event grid viewer call {request}")

        try:
            data = yield from request.json()
            LOGGER.debug(f"Sensor: Processing EventGrid data {data}")
        except ValueError:
            LOGGER.error(f"Sensor: Received event grid data: {request}")
            return self.json_message('Invalid JSON', HTTP_BAD_REQUEST)

        for event in data:
            LOGGER.debug(f"Sensor: Processing EventGrid message {event}")
            event_type = event.get('eventType', "")
            if event_type == SubscriptionValidationEvent:
                #[{'id': '58f9787a-xxxx-xxxx-xxxx-4fbb31c69398', 'topic': '/subscriptions/f2da982c-fc6f-xxxx-ad1e-46a186f9fa84/resourceGroups/eventgridtest/providers/Microsoft.EventGrid/topics/keestesttopic', 'subject': '', 'data': {'validationCode': '09E2E428-xxxx-xxxx-xxxx-BCD800D109A3', 'validationUrl': 'https://rp-westeurope.eventgrid.azure.net/eventsubscriptions/test/validate?id=09E2E428-xxxx-xxxx-xxxx-BCD800D109A3&t=2018-06-10T12:23:49.7126308Z&apiVersion=2018-05-01-preview&token=xxxx%2fXT1Uy8ndIfaro1mo%3d'}, 'eventType': 'Microsoft.EventGrid.SubscriptionValidationEvent', 'eventTime': '2018-06-10T12:23:49.7126308Z', 'metadataVersion': '1', 'dataVersion': '2'}]
                return self.json({
                    'ValidationResponse': event['data']['validationCode']
                })
            else:
                # {'data': "{ 'message': 'test' }", 
                # 'eventTime': '2018-07-01T15:24:10.6291209999999999Z', 
                # 'eventType': 'doUpdate', 
                # 'id': '5e0e8f49-c958-4bb9-9746-f56f8ce3c7f5', 
                # 'subject': 'homeassistant.update', 
                # 'dataVersion': '', 
                # 'metadataVersion': '1', 
                # 'topic': '/subscriptions/8f962503-0c00-4280-a157-8c20b3a9d990/resourceGroups/edvanhome/providers/Microsoft.EventGrid/topics/hass'}
                LOGGER.debug("else statement")
                # self.hass.bus.fire(EVENT_STATE_CHANGED, event_data=event['eventType'])
                # Todo do simething with this message
                # hass.
                self._state = event.get(self._mon_var, self._state)
                self._state_attributes = event

        # raise LOGGER.error('Unknown request on EventGrid api')