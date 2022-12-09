"""
Utility functions to help users load configuration data from files
"""

import logging
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, Protocol, Union

import yaml

from neighborly.archetypes import (
    BaseBusinessArchetype,
    BaseCharacterArchetype,
    BaseResidenceArchetype,
)
from neighborly.core.ecs import GameObject, World
from neighborly.engine import ICharacterArchetype
from neighborly.simulation import Simulation

logger = logging.getLogger(__name__)


class ISectionLoader(Protocol):
    """Interface for a function that loads a specific subsection of the YAML data file"""

    def __call__(self, sim: Simulation, data: Any) -> None:
        raise NotImplementedError()


class YamlDataLoader:
    """Load Neighborly Component and Archetype definitions from an YAML"""

    __slots__ = "sim"

    _section_loaders: ClassVar[Dict[str, ISectionLoader]] = {}

    def __init__(self, sim: Simulation) -> None:
        self.sim: Simulation = sim

    def load(
        self,
        yaml_str: Optional[str] = None,
        filepath: Optional[Union[str, Path]] = None,
    ) -> None:
        """
        Load each section of that YAML datafile

        Parameters
        ----------
        yaml_str: Optional[str]
            YAML data inside a Python string
        filepath: Optional[Union[str, Path]]
            Path to YAML file with data to load
        """
        if yaml_str:
            raw_data: Dict[str, Any] = yaml.safe_load(yaml_str)
        elif filepath:
            with open(filepath, "r") as f:
                raw_data: Dict[str, Any] = yaml.safe_load(f)
        else:
            raise ValueError("No data string or file path given")

        for section, data in raw_data.items():
            if section in self._section_loaders:
                self._section_loaders[section](self.sim, data)
            else:
                logger.warning(f"skipping unsupported YAML section '{section}'.")

    @classmethod
    def add_section_loader(cls, section_name: str, loader_fn: ISectionLoader) -> None:
        """Add a function to load a section of YAML"""
        if section_name in cls._section_loaders:
            logger.warning(f"Overwriting existing loader for section: {section_name}")
        cls._section_loaders[section_name] = loader_fn

    @classmethod
    def section_loader(cls, section_name: str):
        """Decorator function for registering functions that load various sections of the YAML data"""

        def decorator(loader_fn: ISectionLoader) -> ISectionLoader:
            cls.add_section_loader(section_name, loader_fn)
            return loader_fn

        return decorator


@YamlDataLoader.section_loader("Characters")
def load_character_archetypes(sim: Simulation, data: List[Dict[str, Any]]) -> None:
    """Process data defining entity archetypes"""
    for archetype_data in data:
        sim.engine.character_archetypes.add(
            archetype_data["name"], BaseCharacterArchetype(**archetype_data)
        )


@YamlDataLoader.section_loader("Businesses")
def load_business_archetypes(sim: Simulation, data: List[Dict[str, Any]]) -> None:
    """Process data defining business archetypes"""
    for archetype_data in data:
        sim.engine.business_archetypes.add(
            archetype_data["name"], BaseBusinessArchetype(**archetype_data)
        )


@YamlDataLoader.section_loader("Residences")
def load_residence_data(sim: Simulation, data: List[Dict[str, Any]]) -> None:
    """Process data defining residence archetypes"""
    for archetype_data in data:
        sim.engine.residence_archetypes.add(
            archetype_data["name"], BaseResidenceArchetype(**archetype_data)
        )


class YamlDefinedCharacterArchetype(ICharacterArchetype):
    def __init__(
        self,
        name: str,
        base: ICharacterArchetype,
        options: Dict[str, Any],
        max_children_at_spawn: Optional[int] = None,
        chance_spawn_with_spouse: Optional[int] = None,
        spawn_frequency: Optional[int] = None,
    ) -> None:
        self._base: ICharacterArchetype = base
        self._max_children_at_spawn: int = (
            max_children_at_spawn
            if max_children_at_spawn
            else base.get_max_children_at_spawn()
        )
        self._chance_spawn_with_spouse: float = (
            chance_spawn_with_spouse
            if chance_spawn_with_spouse
            else base.get_chance_spawn_with_spouse()
        )
        self._spawn_frequency: int = (
            spawn_frequency if spawn_frequency else base.get_spawn_frequency()
        )
        self._options = options
        self.name = name

    def get_name(self) -> str:
        return self.name

    def get_max_children_at_spawn(self) -> int:
        return self._base.get_max_children_at_spawn()

    def get_chance_spawn_with_spouse(self) -> float:
        return self._base.get_chance_spawn_with_spouse()

    def get_spawn_frequency(self) -> int:
        return self._base.get_spawn_frequency()

    def create(self, world: World, **kwargs: Any) -> GameObject:
        return self._base.create(world, **{**self._options, **kwargs})
