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

from homeassistant.components.climate import (
    STATE_HEAT, STATE_COOL, STATE_IDLE, ClimateDevice, PLATFORM_SCHEMA,
    ATTR_TARGET_TEMP_HIGH, ATTR_TARGET_TEMP_LOW, ATTR_CURRENT_TEMPERATURE,
    ATTR_OPERATION_MODE, STATE_AUTO)
from homeassistant.const import (CONF_NAME, CONF_TIMEOUT, TEMP_FAHRENHEIT,
        TEMP_CELSIUS, STATE_OFF, STATE_ON)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.template import Template
from homeassistant.util.async import run_callback_threadsafe
from homeassistant.util.async import run_coroutine_threadsafe

CONF_BASE_URL = 'base_url'
CONF_PROXY_ID = 'proxy_id'

DEFAULT_NAME = 'Control4 Light'
DEFAULT_TIMEOUT = 10
STATE_VARIABLE_ID = '1104'
OPERATION_VARIABLE_ID = '1107'
CURRENT_TEMP_VARIABLE_ID = '1130'
UNIT_VARIABLE_ID = '1100'
TARGET_TEMP_HIGH_VARIABLE_ID = '1134'
TARGET_TEMP_LOW_VARIABLE_ID = '1132'

STATE_MAPPING = {
    "Off": STATE_OFF,
    "Cool": STATE_COOL,
    "Heat": STATE_HEAT,
    "Auto": STATE_AUTO
}

OPERATION_MAPPING = {
    "Off": STATE_IDLE,
    "Cool": STATE_COOL,
    "Heat": STATE_HEAT
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
    timeout = config.get(CONF_TIMEOUT)

    yield from async_add_devices(
        [C4ClimateDevice(hass, name, base_url, proxy_id, timeout)])

class C4ClimateDevice(ClimateDevice):

    def __init__(self, hass, name, base_url, proxy_id, timeout):
        self._state = STATE_OFF
        self._operation = STATE_IDLE
        self.hass = hass
        self._name = name
        self._base_url = base_url;
        self._proxy_id = proxy_id;
        self._timeout = timeout
        self._current_temp = 0
        self._target_temp_high = 0
        self._target_temp_low = 0
        self._unit = TEMP_FAHRENHEIT

    @property
    def name(self):
        return self._name

    @property
    def temperature_unit(self):
        return self._unit

    @property
    def precision(self):
        return 1

    @property
    def current_temperature(self):
        return self._current_temp

    @property
    def current_operation(self):
        return self._operation

    @property
    def target_temperature_high(self):
        return self._target_temp_high

    @property
    def target_temperature_low(self):
        return self._target_temp_low

    def __init__(self, hass, name, base_url, proxy_id, timeout):
        self._state = STATE_OFF
        self._operation = STATE_IDLE
        self.hass = hass
        self._name = name
        self._base_url = base_url;
        self._proxy_id = proxy_id;
        self._timeout = timeout
        self._current_temp = 0
        self._target_temp_high = 0
        self._target_temp_low = 0
        self._unit = TEMP_FAHRENHEIT

    @property
    def name(self):
        return self._name

    @property
    def temperature_unit(self):
        return self._unit

    @property
    def precision(self):
        return 1

    @property
    def current_temperature(self):
        return self._current_temp

    @property
    def current_operation(self):
        return self._operation

    @property
    def target_temperature_high(self):
        return self._target_temp_high

    @property
    def target_temperature_low(self):
        return self._target_temp_low

    def __init__(self, hass, name, base_url, proxy_id, timeout):
        self._state = STATE_OFF
        self._operation = STATE_IDLE
        self.hass = hass
        self._name = name
        self._base_url = base_url;
        self._proxy_id = proxy_id;
        self._timeout = timeout
        self._current_temp = 0
        self._target_temp_high = 0
        self._target_temp_low = 0
        self._unit = TEMP_FAHRENHEIT

    @property
    def name(self):
        return self._name

    @property
    def temperature_unit(self):
        return self._unit

    @property
    def precision(self):
        return 1

    @property
    def current_temperature(self):
        return self._current_temp

    @property
    def current_operation(self):
        """Return current operation ie. heat, cool, idle."""
        return self._operation

    @property
    def target_temperature_high(self):
        return self._target_temp_high

    @property
    def target_temperature_low(self):
        return self._target_temp_low

    def set_temperature(self, **kwargs):
        if 'target_temp_high' not in kwargs or 'target_temp_low' not in kwargs:
            return
        if int(kwargs['target_temp_low']) != self._target_temp_low:
            run_coroutine_threadsafe(self.update_state(TARGET_TEMP_LOW_VARIABLE_ID, int(kwargs['target_temp_low'])), self.hass.loop).result()
            self._target_temp_low = int(kwargs['target_temp_low'])
        else:
            run_coroutine_threadsafe(self.update_state(TARGET_TEMP_HIGH_VARIABLE_ID, int(kwargs['target_temp_high'])), self.hass.loop).result()
            self._target_temp_high = int(kwargs['target_temp_high'])

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

        websession = async_get_clientsession(self.hass)
        request = None
        try:
            with async_timeout.timeout(self._timeout, loop=self.hass.loop):
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
            with async_timeout.timeout(self._timeout, loop=self.hass.loop):
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
            self._state = STATE_MAPPING[json_text[STATE_VARIABLE_ID]]
            self._operation = OPERATION_MAPPING[json_text[OPERATION_VARIABLE_ID]]
            self._current_temp = int(json_text[CURRENT_TEMP_VARIABLE_ID])
            self._target_temp_high = int(json_text[TARGET_TEMP_HIGH_VARIABLE_ID])
            self._target_temp_low = int(json_text[TARGET_TEMP_LOW_VARIABLE_ID])
            self._unit = UNIT_MAPPING[json_text[UNIT_VARIABLE_ID]]
        except ValueError:
            _LOGGER.warning('Invalid value received')
