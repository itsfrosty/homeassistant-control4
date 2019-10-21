"""
Support for Control4 Thermostat. You need to use control4-2way-web-driver
along with this
"""
import asyncio
import logging

import aiohttp
import async_timeout
import voluptuous as vol
import urllib.parse as urlparse
from urllib.parse import urlencode
import json

from homeassistant.components.climate import ClimateDevice, PLATFORM_SCHEMA
from homeassistant.components.climate.const import (
    HVAC_MODE_OFF, HVAC_MODE_COOL, HVAC_MODE_HEAT, HVAC_MODE_AUTO,
    CURRENT_HVAC_IDLE, CURRENT_HVAC_COOL, CURRENT_HVAC_HEAT,
    ATTR_TARGET_TEMP_HIGH, ATTR_TARGET_TEMP_LOW, ATTR_CURRENT_TEMPERATURE,
    SUPPORT_TARGET_TEMPERATURE)
from homeassistant.const import (CONF_NAME, CONF_TIMEOUT, TEMP_FAHRENHEIT, TEMP_CELSIUS)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.template import Template

TIMEOUT = 10

SUPPORT_FLAGS = (SUPPORT_TARGET_TEMPERATURE)

CONF_BASE_URL = 'base_url'
CONF_PROXY_ID = 'proxy_id'

DEFAULT_NAME = 'Control5 Light'
DEFAULT_TIMEOUT = 10
STATE_VARIABLE_ID = '1107'
OPERATION_VARIABLE_ID = '1104'
CURRENT_TEMP_VARIABLE_ID = '1130'
UNIT_VARIABLE_ID = '1100'
TARGET_TEMP_HIGH_VARIABLE_ID = '1134'
TARGET_TEMP_LOW_VARIABLE_ID = '1132'

OPERATION_MAPPING = {
    "Off": HVAC_MODE_OFF,
    "Cool": HVAC_MODE_COOL,
    "Heat": HVAC_MODE_HEAT,
    "Auto": HVAC_MODE_AUTO
}

STATE_MAPPING = {
    "Off": CURRENT_HVAC_IDLE,
    "Cool": CURRENT_HVAC_COOL,
    "Heat": CURRENT_HVAC_HEAT
}

UNIT_MAPPING = {
    "FAHRENHEIT": TEMP_FAHRENHEIT,
    "CELSIUS": TEMP_CELSIUS
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_BASE_URL): cv.url,
    vol.Required(CONF_PROXY_ID): cv.positive_int,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): cv.positive_int,
})

_LOGGER = logging.getLogger(__name__)


# pylint: disable=unused-argument,
@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    name = config.get(CONF_NAME)
    base_url = config.get(CONF_BASE_URL)
    proxy_id = config.get(CONF_PROXY_ID)
    async_add_devices([C4ClimateDevice(hass, name, base_url, proxy_id)])

class C4ClimateDevice(ClimateDevice):

    def __init__(self, hass, name, base_url, proxy_id):
        self._state = CURRENT_HVAC_IDLE
        self._operation = HVAC_MODE_OFF
        self.hass = hass
        self._name = name
        self._base_url = base_url;
        self._proxy_id = proxy_id;
        self._current_temp = 72
        self._target_temp_high = 78
        self._target_temp_low = 68
        self._unit = TEMP_FAHRENHEIT
        self._target_temperature = 72
        self._min_temp = 65
        self._max_temp = 78

    @property
    def name(self):
        return self._name

    @property
    def temperature_unit(self):
        return self._unit

    @property
    def min_temp(self):
        return self._min_temp

    @property
    def max_temp(self):
        return self._max_temp

    @property
    def supported_features(self):
        return SUPPORT_FLAGS

    @property
    def precision(self):
        return 1

    @property
    def current_temperature(self):
        return self._current_temp

    @property
    def hvac_mode(self):
        """Return current operation ie. heat, cool, idle."""
        return self._operation

    @property
    def target_temperature_high(self):
        return self._target_temp_high

    @property
    def target_temperature_low(self):
        return self._target_temp_low

    @property
    def target_temperature(self):
        return self._target_temperature

    def set_temperature(self, **kwargs):
        self._target_temperature = int(kwargs['temperature'])
        if self._operation == HVAC_MODE_COOL:
            self._target_temp_high = int(kwargs['temperature'])
            asyncio.run_coroutine_threadsafe(self.update_state(TARGET_TEMP_HIGH_VARIABLE_ID, int(kwargs['temperature'])), self.hass.loop).result()
        else:
            self._target_temp_low = int(kwargs['temperature'])
            asyncio.run_coroutine_threadsafe(self.update_state(TARGET_TEMP_LOW_VARIABLE_ID, int(kwargs['temperature'])), self.hass.loop).result()

    def get_url(self, url, params):
        url_parts = list(urlparse.urlparse(url))
        query = dict(urlparse.parse_qsl(url_parts[4]))
        query.update(params)
        url_parts[4] = urlencode(query)

        return urlparse.urlunparse(url_parts)

    @asyncio.coroutine
    def update_state(self, variable_id, value):
        params = {
            'command': 'set',
            'proxyID': self._proxy_id,
            'variableID': variable_id,
            'newValue': value
        }

        request = None
        try:
            websession = async_get_clientsession(self.hass)
            with async_timeout.timeout(TIMEOUT, loop=self.hass.loop):
                request = yield from websession.get(self.get_url(self._base_url, params))
        except (asyncio.TimeoutError, aiohttp.errors.ClientError):
            _LOGGER.error("Error while turn on %s", self._base_url)
            return
        finally:
            if request is not None:
                yield from request.release()

        if request.status != 200:
            _LOGGER.error("Can't turn on %s. Is resource/endpoint offline?",
                          self._base_url)
    
    @asyncio.coroutine
    def async_set_hvac_mode(self, hvac_mode):
      url_str = 'http://192.168.86.152:8080/'
      if self._proxy_id == 36:
        url_str = url_str + 'ThreeMode'
      else:
        url_str = url_str + 'TwoMode'

      if hvac_mode == HVAC_MODE_HEAT:
        self._current_operation = HVAC_MODE_HEAT
        self._enabled = True
        url_str = url_str + 'Heat'
      elif hvac_mode == HVAC_MODE_COOL:
        self._current_operation = HVAC_MODE_COOL
        self._enabled = True
        url_str = url_str + 'Cool'
      elif hvac_mode == HVAC_MODE_AUTO:
        self._current_operation = HVAC_MODE_AUTO
        self._enabled = True
        url_str = url_str + 'Auto'
      elif hvac_mode == HVAC_MODE_OFF:
        self._current_operation = HVAC_MODE_OFF
        self._enabled = False
        url_str = url_str + 'Off'

       
      websession = async_get_clientsession(self.hass)
      request = None
      with async_timeout.timeout(TIMEOUT, loop=self.hass.loop):
        request = yield from websession.get(url_str)
      return

    @property
    def hvac_modes(self):
      return [HVAC_MODE_OFF, HVAC_MODE_HEAT, HVAC_MODE_COOL, HVAC_MODE_AUTO];

    @asyncio.coroutine
    def async_update(self):
        """Get the latest data from API and update the state."""
        params = {
            'command': 'get',
            'proxyID': self._proxy_id,
            'variableID': ','.join([STATE_VARIABLE_ID, OPERATION_VARIABLE_ID,
                CURRENT_TEMP_VARIABLE_ID, UNIT_VARIABLE_ID, TARGET_TEMP_HIGH_VARIABLE_ID,
                TARGET_TEMP_LOW_VARIABLE_ID])
        }
        url = self.get_url(self._base_url, params)
        websession = async_get_clientsession(self.hass)
        request = None

        try:
            with async_timeout.timeout(TIMEOUT, loop=self.hass.loop):
                request = yield from websession.get(url)
                text = yield from request.text()
        except (asyncio.TimeoutError, aiohttp.errors.ClientError):
            _LOGGER.exception("Error while fetch data.")
            return
        finally:
            if request is not None:
                yield from request.release()
        json_text = json.loads(text)
        try:
            self._state = STATE_MAPPING[json_text[STATE_VARIABLE_ID] if json_text[STATE_VARIABLE_ID] else "Off"]
            self._operation = OPERATION_MAPPING[json_text[OPERATION_VARIABLE_ID]]
            self._current_temp = int(json_text[CURRENT_TEMP_VARIABLE_ID])
            self._target_temp_high = int(json_text[TARGET_TEMP_HIGH_VARIABLE_ID])
            self._target_temp_low = int(json_text[TARGET_TEMP_LOW_VARIABLE_ID])
            self._unit = UNIT_MAPPING[json_text[UNIT_VARIABLE_ID]]
            if self._operation == HVAC_MODE_COOL:
                self._target_temperature = self._target_temp_high
            else:
                self._target_temperature = self._target_temp_low
        except ValueError:
            _LOGGER.warning('Invalid value received')
