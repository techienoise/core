from __future__ import print_function
import datetime
import pickle
import os.path
import voluptuous as vol

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from homeassistant.const import (
    CONF_API_KEY,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_MODE,
    CONF_NAME,
    PRESSURE_HPA,
    PRESSURE_INHG,
    STATE_UNKNOWN,
    TEMP_CELSIUS,
)
import homeassistant.helpers.config_validation as cv
from homeassistant.util import Throttle
# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

#######################################################################################################
## Home Assistant 
#######################################################################################################
from datetime import timedelta
import logging

from homeassistant.helpers.config_validation import (  # noqa: F401
    PLATFORM_SCHEMA,
    PLATFORM_SCHEMA_BASE,
)

from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_component import EntityComponent

_LOGGER = logging.getLogger(__name__)

DOMAIN = "gevents"

ENTITY_ID_FORMAT = DOMAIN + ".{}"

SCAN_INTERVAL = timedelta(seconds=30)

#Project Default Name 
DEFAULT_NAME = "googlecalenderevents"

async def async_setup(hass, config):
    """Set up the gevents component."""
    component = hass.data[DOMAIN] = EntityComponent(
        _LOGGER, DOMAIN, hass, SCAN_INTERVAL
    )
    await component.async_setup(config)
    return True

async def async_setup_entry(hass, entry):
    """Set up a config entry."""
    return await hass.data[DOMAIN].async_setup_entry(entry)


async def async_unload_entry(hass, entry):
    """Unload a config entry."""
    return await hass.data[DOMAIN].async_unload_entry(entry)
 
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        #Validation     Values      Format 
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    }
)

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the GoogleEvents platform."""
    name = config.get(CONF_NAME)
    mode = config.get(CONF_MODE)
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    try:
        service = build('calendar', 'v3', credentials=creds)
    except APICallError:
        _LOGGER.error("Error while connecting to Google Calender API")
        return False

    data = EventsData(service)

    add_entities(
        [GoogleEvents(name, data)],
        True,
    )

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=10)
class EventsData:
    """Get the latest data from Google Calender."""

    def __init__(self, service):
        """Initialize the data object."""
        self.data = None
        self.service = service

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Get the latest data from Google Calender."""
        # Call the Calendar API
        now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
        print('Getting the upcoming 10 events')
        events_result = service.events().list(calendarId='primary', timeMin=now,
                                            maxResults=100, singleEvents=True,
                                            orderBy='startTime').execute()
        events = events_result.get('items', [])
        self.data = events

class GoogleEvents(Entity):
    """Representation of a Google Events."""

    def __init__(self, name, api):
        """Initialize a Google Events."""
        self._api = api
        self._name = name
        self._state = "Available"
        self._var_icon = "mdi:timelapse"

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._name}"

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return self._var_icon

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    def update(self):
        """Get the latest data from the Google Wifi API."""
        self._api.update()
        self._state = self._api.data["summary"]