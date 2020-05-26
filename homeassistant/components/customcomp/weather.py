"""Support for the OpenWeatherMap (OWM) service."""
from datetime import timedelta
import logging

from pyowm import OWM
from pyowm.exceptions.api_call_error import APICallError
import voluptuous as vol

from homeassistant.components.weather import (
    ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_PRECIPITATION,
    ATTR_FORECAST_TEMP,
    ATTR_FORECAST_TEMP_LOW,
    ATTR_FORECAST_TIME,
    ATTR_FORECAST_WIND_BEARING,
    ATTR_FORECAST_WIND_SPEED,
    PLATFORM_SCHEMA,
    WeatherEntity,
)
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
from homeassistant.util.pressure import convert as convert_pressure

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "customcomp"

MIN_TIME_BETWEEN_FORECAST_UPDATES = timedelta(minutes=30)
MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=10)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_API_KEY): cv.string,
        vol.Optional(CONF_LATITUDE): cv.latitude,
        vol.Optional(CONF_LONGITUDE): cv.longitude,
        vol.Optional(CONF_MODE, default="hourly"): vol.In(FORECAST_MODE),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the OpenWeatherMap weather platform."""

    longitude = config.get(CONF_LONGITUDE, round(hass.config.longitude, 5))
    latitude = config.get(CONF_LATITUDE, round(hass.config.latitude, 5))
    name = config.get(CONF_NAME)
    mode = config.get(CONF_MODE)

    try:
        owm = OWM(config.get(CONF_API_KEY))
    except APICallError:
        _LOGGER.error("Error while connecting to OpenWeatherMap")
        return False

    data = WeatherData(owm, latitude, longitude, mode)

    add_entities(
        [OpenWeatherMapWeather(name, data, hass.config.units.temperature_unit, mode)],
        True,
    )


class OpenWeatherMapWeather(WeatherEntity):
    """Implementation of an OpenWeatherMap sensor."""

    def __init__(self, name, owm, temperature_unit, mode):
        """Initialize the sensor."""
        self._name = name

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

class WeatherData:
    """Get the latest data from OpenWeatherMap."""

    def __init__(self, owm, latitude, longitude, mode):
        """Initialize the data object."""
        self._mode = mode
        self.owm = owm
        self.latitude = latitude
        self.longitude = longitude
        self.data = None
        self.forecast_data = None

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Get the latest data from OpenWeatherMap."""
        obs = self.owm.weather_at_coords(self.latitude, self.longitude)
        if obs is None:
            _LOGGER.warning("Failed to fetch data from OWM")
            return

        self.data = obs.get_weather()

    @Throttle(MIN_TIME_BETWEEN_FORECAST_UPDATES)
    def update_forecast(self):
        """Get the latest forecast from OpenWeatherMap."""
        try:
            if self._mode == "daily":
                fcd = self.owm.daily_forecast_at_coords(
                    self.latitude, self.longitude, 15
                )
            else:
                fcd = self.owm.three_hours_forecast_at_coords(
                    self.latitude, self.longitude
                )
        except APICallError:
            _LOGGER.error("Exception when calling OWM web API to update forecast")
            return

        if fcd is None:
            _LOGGER.warning("Failed to fetch forecast data from OWM")
            return

        self.forecast_data = fcd.get_forecast()
