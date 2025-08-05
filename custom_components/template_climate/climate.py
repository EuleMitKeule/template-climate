"""Template Climate Component for Home Assistant."""

from collections.abc import Callable, Sequence
import logging
from typing import Any, cast

import voluptuous as vol

from homeassistant.components.climate import (
    DOMAIN as CLIMATE_DOMAIN,
    PLATFORM_SCHEMA as CLIMATE_PLATFORM_SCHEMA,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.components.template.template_entity import (
    TEMPLATE_ENTITY_ATTRIBUTES_SCHEMA,
    TEMPLATE_ENTITY_COMMON_SCHEMA,
    TemplateEntity,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import TemplateError
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.script import Script, Template
from homeassistant.helpers.trigger_template_entity import CONF_UNIQUE_ID
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import (
    CONF_BASE_CLIMATE_ENTITY_ID,
    CONF_CLIMATES,
    CONF_FAN_MODE_SCRIPTS,
    CONF_HVAC_MODE_SCRIPTS,
    CONF_PRESET_MODE_SCRIPTS,
    CONF_SERVICE_SCRIPTS,
    CONF_SET_HUMIDITY_SCRIPT,
    CONF_SET_TEMPERATURE_SCRIPT,
    CONF_STATE,
    CONF_SWING_HORIZONTAL_MODE_SCRIPTS,
    CONF_SWING_MODE_SCRIPTS,
    CONF_TEMPERATURE_UNIT,
    CONF_TOGGLE_SCRIPT,
    CONF_TURN_OFF_SCRIPT,
    CONF_TURN_ON_SCRIPT,
)

_LOGGER = logging.getLogger(__name__)

CLIMATE_SCHEMA = (
    vol.Schema(
        {
            vol.Required(CONF_TEMPERATURE_UNIT): cv.string,
            vol.Optional(CONF_STATE): cv.string,
            vol.Optional(CONF_BASE_CLIMATE_ENTITY_ID): cv.entity_id,
            vol.Optional(CONF_SERVICE_SCRIPTS, default={}): {
                cv.string: cv.SCRIPT_SCHEMA
            },
            vol.Optional(CONF_HVAC_MODE_SCRIPTS, default={}): {
                cv.string: cv.SCRIPT_SCHEMA
            },
            vol.Optional(CONF_PRESET_MODE_SCRIPTS, default={}): {
                cv.string: cv.SCRIPT_SCHEMA
            },
            vol.Optional(CONF_FAN_MODE_SCRIPTS, default={}): {
                cv.string: cv.SCRIPT_SCHEMA
            },
            vol.Optional(CONF_SWING_MODE_SCRIPTS, default={}): {
                cv.string: cv.SCRIPT_SCHEMA
            },
            vol.Optional(CONF_SWING_HORIZONTAL_MODE_SCRIPTS, default={}): {
                cv.string: cv.SCRIPT_SCHEMA
            },
        }
    )
    .extend(TEMPLATE_ENTITY_COMMON_SCHEMA.schema)
    .extend(TEMPLATE_ENTITY_ATTRIBUTES_SCHEMA.schema)
)

PLATFORM_SCHEMA = CLIMATE_PLATFORM_SCHEMA.extend(
    {vol.Required(CONF_CLIMATES): cv.schema_with_slug_keys(CLIMATE_SCHEMA)}
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the template climates."""
    climate_configs: dict[str, ConfigType] = config[CONF_CLIMATES]
    climates: list[TemplateClimate] = []

    for climate_name, climate_config in climate_configs.items():
        climates.append(TemplateClimate(hass, climate_config, climate_name))

    async_add_entities(climates)


class TemplateClimate(TemplateEntity, ClimateEntity):
    """Representation of a Template climate."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigType,
        name: str,
    ) -> None:
        """Initialize the Template climate."""
        unique_id: str | None = config.get(CONF_UNIQUE_ID, name)

        TemplateEntity.__init__(self, hass, config, unique_id)

        self._attr_should_poll = False
        self._attr_temperature_unit = config[CONF_TEMPERATURE_UNIT]

        self._base_climate_entity_id = config.get(CONF_BASE_CLIMATE_ENTITY_ID)
        self._state_template: Template | None = Template(config.get(CONF_STATE), hass)
        self._state: str | None = None
        self._service_scripts = {
            service: Script(hass, service_script, name, CLIMATE_DOMAIN)
            for service, service_script in cast(
                dict[str, Sequence[dict[str, Any]]], config.get(CONF_SERVICE_SCRIPTS)
            ).items()
        }
        self._hvac_mode_scripts = {
            hvac_mode: Script(hass, hvac_mode_script, name, CLIMATE_DOMAIN)
            for hvac_mode, hvac_mode_script in cast(
                dict[str, Sequence[dict[str, Any]]], config.get(CONF_HVAC_MODE_SCRIPTS)
            ).items()
        }
        self._preset_mode_scripts = {
            preset_mode: Script(hass, preset_mode_script, name, CLIMATE_DOMAIN)
            for preset_mode, preset_mode_script in cast(
                dict[str, Sequence[dict[str, Any]]],
                config.get(CONF_PRESET_MODE_SCRIPTS),
            ).items()
        }
        self._fan_mode_scripts = {
            fan_mode: Script(hass, fan_mode_script, name, CLIMATE_DOMAIN)
            for fan_mode, fan_mode_script in cast(
                dict[str, Sequence[dict[str, Any]]], config.get(CONF_FAN_MODE_SCRIPTS)
            ).items()
        }
        self._swing_mode_scripts = {
            swing_mode: Script(hass, swing_mode_script, name, CLIMATE_DOMAIN)
            for swing_mode, swing_mode_script in cast(
                dict[str, Sequence[dict[str, Any]]], config.get(CONF_SWING_MODE_SCRIPTS)
            ).items()
        }
        self._swing_horizontal_mode_scripts = {
            swing_horizontal_mode: Script(
                hass, swing_horizontal_mode_script, name, CLIMATE_DOMAIN
            )
            for swing_horizontal_mode, swing_horizontal_mode_script in cast(
                dict[str, Sequence[dict[str, Any]]],
                config.get(CONF_SWING_HORIZONTAL_MODE_SCRIPTS),
            ).items()
        }

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        self.add_template_attribute(
            "_state", self._state_template, None, self._update_state
        )
        await super().async_added_to_hass()

    @property
    def _base_climate_entity(self) -> ClimateEntity | None:
        if self._base_climate_entity_id:
            component: EntityComponent[ClimateEntity] = self.hass.data[CLIMATE_DOMAIN]
            if entity := component.get_entity(self._base_climate_entity_id):
                return entity
        return None

    @callback
    def _update_state(self, result: str | TemplateError) -> None:
        super()._update_state(result)

        if isinstance(result, TemplateError):
            _LOGGER.error("Could not render state template: %s", result)
            self._state = None
            return

        try:
            state = str(result)
            self._state = state
        except ValueError:
            _LOGGER.error("Received invalid state: %s", result)
            self._state = None

    def add_template_attribute(
        self,
        attribute: str,
        template: Template,
        validator: Callable[[Any], Any] | None = None,
        on_update: Callable[[Any], None] | None = None,
        none_on_template_error: bool = False,
    ) -> None:
        """Create a template tracker for the attribute."""
        template = Template(
            "{% set attribute = '" + attribute + "' %}" + template.template, self.hass
        )

        super().add_template_attribute(
            attribute,
            template,
            validator,
            on_update,
            none_on_template_error,
        )

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Flag climate features that are supported."""
        support = ClimateEntityFeature(0)

        if self._base_climate_entity:
            support |= self._base_climate_entity.supported_features

        if CONF_TURN_ON_SCRIPT in self._service_scripts:
            support |= ClimateEntityFeature.TURN_ON
        if CONF_TURN_OFF_SCRIPT in self._service_scripts:
            support |= ClimateEntityFeature.TURN_OFF
        if CONF_SET_TEMPERATURE_SCRIPT in self._service_scripts:
            support |= ClimateEntityFeature.TARGET_TEMPERATURE
        if CONF_SET_HUMIDITY_SCRIPT in self._service_scripts:
            support |= ClimateEntityFeature.TARGET_HUMIDITY
        if self._fan_mode_scripts:
            support |= ClimateEntityFeature.FAN_MODE
        if self._preset_mode_scripts:
            support |= ClimateEntityFeature.PRESET_MODE
        if self._swing_mode_scripts:
            support |= ClimateEntityFeature.SWING_MODE
        if self._swing_horizontal_mode_scripts:
            support |= ClimateEntityFeature.SWING_HORIZONTAL_MODE

        return support

    @property
    def state(self) -> str | None:
        """State of the climate."""
        if self._state_template:
            return self._state

        if self._base_climate_entity:
            return self._base_climate_entity.state

        return None

    @property
    def hvac_modes(self) -> list | list[str] | None:
        """List of available hvac modes."""
        if self._hvac_mode_scripts:
            return list(self._hvac_mode_scripts.keys())

        if self._base_climate_entity:
            return self._base_climate_entity.hvac_modes

        return []

    @property
    def preset_modes(self) -> list[str] | None:
        """List of available preset modes."""
        if self._preset_mode_scripts:
            return list(self._preset_mode_scripts.keys())

        if self._base_climate_entity:
            return self._base_climate_entity.preset_modes

        return None

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        if CONF_SET_TEMPERATURE_SCRIPT in self._service_scripts:
            await self._service_scripts[CONF_SET_TEMPERATURE_SCRIPT].async_run(
                kwargs, context=self._context
            )

        if self._base_climate_entity:
            await self._base_climate_entity.async_set_temperature(**kwargs)

    async def async_set_humidity(self, humidity: int) -> None:
        """Set new target humidity."""
        if CONF_SET_HUMIDITY_SCRIPT in self._service_scripts:
            await self._service_scripts[CONF_SET_HUMIDITY_SCRIPT].async_run(
                {"humidity": humidity}, context=self._context
            )
        if self._base_climate_entity:
            await self._base_climate_entity.async_set_humidity(humidity)

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        if fan_mode in self._fan_mode_scripts:
            await self._fan_mode_scripts[fan_mode].async_run(context=self._context)
        if self._base_climate_entity:
            await self._base_climate_entity.async_set_fan_mode(fan_mode)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        if hvac_mode in self._hvac_mode_scripts:
            await self._hvac_mode_scripts[hvac_mode].async_run(context=self._context)
        if self._base_climate_entity:
            await self._base_climate_entity.async_set_hvac_mode(hvac_mode)

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Set new target swing operation."""
        if swing_mode in self._swing_mode_scripts:
            await self._swing_mode_scripts[swing_mode].async_run(context=self._context)
        if self._base_climate_entity:
            await self._base_climate_entity.async_set_swing_mode(swing_mode)

    async def async_set_swing_horizontal_mode(self, swing_horizontal_mode: str) -> None:
        """Set new target horizontal swing operation."""
        if swing_horizontal_mode in self._swing_horizontal_mode_scripts:
            await self._swing_horizontal_mode_scripts[swing_horizontal_mode].async_run(
                context=self._context
            )
        if self._base_climate_entity:
            await self._base_climate_entity.async_set_swing_horizontal_mode(
                swing_horizontal_mode
            )

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        if preset_mode in self._preset_mode_scripts:
            await self._preset_mode_scripts[preset_mode].async_run(
                context=self._context
            )
        if self._base_climate_entity:
            await self._base_climate_entity.async_set_preset_mode(preset_mode)

    async def async_turn_on(self) -> None:
        """Turn the entity on."""
        if CONF_TURN_ON_SCRIPT in self._service_scripts:
            await self._service_scripts[CONF_TURN_ON_SCRIPT].async_run(
                context=self._context
            )
        if self._base_climate_entity:
            await self._base_climate_entity.async_turn_on()

    async def async_turn_off(self) -> None:
        """Turn the entity off."""
        if CONF_TURN_OFF_SCRIPT in self._service_scripts:
            await self._service_scripts[CONF_TURN_OFF_SCRIPT].async_run(
                context=self._context
            )
        if self._base_climate_entity:
            await self._base_climate_entity.async_turn_off()

    async def async_toggle(self) -> None:
        """Toggle the entity."""
        if CONF_TOGGLE_SCRIPT in self._service_scripts:
            await self._service_scripts[CONF_TOGGLE_SCRIPT].async_run(
                context=self._context
            )
        if self._base_climate_entity:
            await self._base_climate_entity.async_toggle()
