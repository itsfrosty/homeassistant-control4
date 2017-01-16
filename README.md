# homeassistant-control4

This plugin for home assistant allows you to control your control4 devices using
Home Assistant. This plugin is very early state and right now only supports
lights/dimmers and thermostat.

How To:
--------
- Install Web2Way driver in Control4 - https://github.com/itsfrosty/control4-2way-web-driver
- Copy the custom_components into your ~/.homeassistant/ folder
- Find the proxy_id for each of your devices and include them
in your homeassistant configuration.yaml.

Known Issues:
--------------
- Changing thermostat mode is not working. Only temperature control

Sample Home Assistant Config:
-----------------------------

For lights:
~~~~
light:
  - platform: control4
    base_url: 'http://192.168.1.142:9000/'
    proxy_id: 25
    name: Bedroom
    scan_interval: 10
~~~~

For thermostat:
~~~~
climate:
  - platform: control4
    base_url: 'http://192.168.1.142:9000/'
    proxy_id: 36
    name: Top Floor
    scan_interval: 10
~~~~

