# Template Climate

[![My Home Assistant](https://img.shields.io/badge/Home%20Assistant-%2341BDF5.svg?style=flat&logo=home-assistant&label=My)](https://my.home-assistant.io/redirect/hacs_repository/?owner=EuleMitKeule&repository=template-climate&category=integration)

![GitHub License](https://img.shields.io/github/license/eulemitkeule/template-climate)
![GitHub Sponsors](https://img.shields.io/github/sponsors/eulemitkeule?logo=GitHub-Sponsors)

> [!NOTE]
> This integration is strongly inspired by [hass-template-climate](https://github.com/jcwillox/hass-template-climate).<br>
> Unfortunately that integration is missing some features, so I decided to create a new and improved one.

With Template Climate you can create climate entities in Home Assistant using templates and scripts.<br>
You can define any attribute you want and create custom behaviour for all services supported by the `climate` domain.<br>
This allows you to combine your existing climate entities into a single entity for improved usability and control or to create completely new climate entities from scratch.

## Installation

You can install this integration using the custom repository option in [HACS](https://hacs.xyz/).<br>

1. Add the repository URL to the list of custom repositories in HACS
2. Select and install the integration in HACS
3. Restart Home Assistant
4. Configure your entities

## Configuration

To create the entities you need to define them in your `configuration.yaml` file.<br>
For a full example of all available options see [examples](examples/configuration.yaml).

```yaml
climate:
  - platform: template_climate
    climates:
      my_climate:
        unique_id: my_climate
        friendly_name: My Climate
        device_class: hvac
        icon: mdi:thermostat
        state: "on"
```

### Templates

All main options and all elements of the `attributes` object can be defined using Jinja2 templates:

```yaml
# ...
state: >
  {% if states('climate.something") == "on" %}
    idle
  {% else %}
    off
  {% endif %}
```

#### Attributes

To define state attributes for your entity use the `attributes` option.<br>
You can use the variable `attribute` in your templates to get the current attributes name as a string.<br>
For a full list of attributes commonly used by climate entities see [examples](examples/configuration.yaml).

```yaml
climate:
  - platform: template_climate
    climates:
      my_climate:
        #...
        attributes:
            temperature: >
              # `attribute` contains the value "temperature"
              {{ state_attr("climate.something", attribute) }}
```

#### Variables

To reduce code duplication you can define a template using the `variables` option.
This is a dictionary of variables that can be used in all templates of the climate entity.<br>

```yaml
climate:
  - platform: template_climate
    climates:
      my_climate:
        #...
        variables:
          climate1: "climate.something"
        state: >
          {{ states(climate1) }}
```

### Scripts

Elements of the `service_scripts`, `preset_mode_scripts` or `hvac_mode_scripts` options are action sequences like in Home Assistant scripts.

```yaml
climate:
  - platform: template_climate
    climates:
      my_climate:
        #...
        service_scripts:
          turn_on:
            - service: climate.turn_on
              data_template:
                entity_id: climate.something
            - delay:
                seconds: 3
            - service: climate.set_temperature
              data_template:
                entity_id: climate.something
                temperature: 22
```

#### Service Scripts

Use the `service_scripts` option to define services that are supported by the `climate` domain.<br>
For a full list of services and their respective variables supported by climate entities see [examples](examples/configuration.yaml).

```yaml
climate:
  - platform: template_climate
    climates:
      my_climate:
        #...
        service_scripts:
          turn_on:
            - service: climate.turn_on
              data_template:
                entity_id: climate.something
```

#### HVAC Mode Scripts

Use the `hvac_mode_scripts` option to define HVAC modes for your climate entity.

```yaml
climate:
  - platform: template_climate
    climates:
      my_climate:
        #...
        hvac_mode_scripts:
          Cool:
            - service: climate.set_hvac_mode
              data_template:
                entity_id: climate.something
                hvac_mode: Cool
```

#### Preset Mode Scripts

Use the `preset_mode_scripts` option to define preset modes for your climate entity.

```yaml
climate:
  - platform: template_climate
    climates:
      my_climate:
        #...
        preset_mode_scripts:
          Eco:
            - service: climate.set_preset_mode
              data_template:
                entity_id: climate.something
                preset_mode: Eco
```

### Other

`fan_mode_scripts`, `swing_mode_scripts` and `swing_horizontal_mode_scripts` can be used to define scripts for the respective modes.<br>

### Base Climate

You can specify an entity using the `base_climate_entity_id` option to inherit all supported behaviour and attributes from, when the behaviour or attribute is not implemented by the template climate.
