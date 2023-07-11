"""Neighborly Character Components

The module contains definitions of components used to compose Character entities.
It also contains definitions for common statuses and relationship statuses.

"""
from __future__ import annotations

import dataclasses
import enum
from typing import (
    Any,
    ClassVar,
    Dict,
    FrozenSet,
    Iterator,
    List,
    Optional,
    Tuple,
    Type,
    Union,
)

import numpy as np
from numpy import typing as npt

from neighborly.core.ecs import Component, GameObject, ISerializable
from neighborly.core.relationship import IRelationshipStatus
from neighborly.core.status import IStatus

from neighborly.components.trait import IInheritable, ITrait


class GameCharacter(Component, ISerializable):
    """Tags a GameObject as a character and tracks their name."""

    __slots__ = "first_name", "last_name"

    first_name: str
    """The character's first name."""

    last_name: str
    """The character's last name or family name."""

    def __init__(
        self,
        first_name: str,
        last_name: str,
    ) -> None:
        """
        Parameters
        ----------
        first_name
            The character's first name.
        last_name
            The character's last name or family name.
        """
        super().__init__()
        self.first_name = first_name
        self.last_name = last_name

    @property
    def full_name(self) -> str:
        """The combined full name of the character."""
        return f"{self.first_name} {self.last_name}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "first_name": self.first_name,
            "last_name": self.last_name,
        }

    def __repr__(self) -> str:
        return "{}(name={})".format(
            self.__class__.__name__,
            self.full_name,
        )

    def __str__(self) -> str:
        return self.full_name


class Departed(IStatus):
    """Tags a character as departed from the simulation."""

    is_persistent = True


class CanAge(ITrait):
    """Tags a GameObject as being able to change life stages as time passes."""

    @classmethod
    def get_conflicts(cls) -> FrozenSet[Type[ITrait]]:
        """Get component types that this component's type conflicts with."""
        return frozenset({})


class CanGetPregnant(ITrait):
    """Tags a character as capable of getting pregnant and giving birth."""

    @classmethod
    def get_conflicts(cls) -> FrozenSet[Type[ITrait]]:
        """Get component types that this component's type conflicts with."""
        return frozenset({})


class CanGetOthersPregnant(ITrait):
    """Tags a character as capable of getting other characters pregnant."""

    @classmethod
    def get_conflicts(cls) -> FrozenSet[Type[ITrait]]:
        """Get component types that this component's type conflicts with."""
        return frozenset({})


class Deceased(IStatus):
    """Tags a character as deceased."""

    is_persistent = True


class Retired(IStatus):
    """Tags a character as retired."""

    is_persistent = True


class Virtue(enum.IntEnum):
    """An enumeration of virtue types."""

    ADVENTURE = 0
    AMBITION = enum.auto()
    EXCITEMENT = enum.auto()
    COMMERCE = enum.auto()
    CONFIDENCE = enum.auto()
    CURIOSITY = enum.auto()
    FAMILY = enum.auto()
    FRIENDSHIP = enum.auto()
    WEALTH = enum.auto()
    HEALTH = enum.auto()
    INDEPENDENCE = enum.auto()
    KNOWLEDGE = enum.auto()
    LEISURE_TIME = enum.auto()
    LOYALTY = enum.auto()
    LUST = enum.auto()
    MATERIAL_THINGS = enum.auto()
    NATURE = enum.auto()
    PEACE = enum.auto()
    POWER = enum.auto()
    RELIABILITY = enum.auto()
    ROMANCE = enum.auto()
    SINGLE_MINDEDNESS = enum.auto()
    SOCIALIZING = enum.auto()
    SELF_CONTROL = enum.auto()
    TRADITION = enum.auto()
    TRANQUILITY = enum.auto()


class Virtues(Component, ISerializable):
    """
    Values are what an entity believes in. They are used
    for decision-making and relationship compatibility among
    other things.


    Individual values are integers on the range [-50,50], inclusive.

    This model of entity values is borrowed from Dwarf Fortress'
    model of entity beliefs/values outlined at the following link
    https://dwarffortresswiki.org/index.php/DF2014:Personality_trait>.
    """

    VIRTUE_MAX: ClassVar[int] = 50
    """The maximum value an virtue can have."""

    VIRTUE_MIN: ClassVar[int] = -50
    """The minimum value a virtue can have."""

    STRONG_AGREE: ClassVar[int] = 35
    """The threshold for strong agreement with a virtue."""

    AGREE: ClassVar[int] = 25
    """The threshold for mild agreement with a virtue."""

    WEAK_AGREE: ClassVar[int] = 15
    """The threshold for weak agreement with a virtue."""

    WEAK_DISAGREE: ClassVar[int] = -15
    """The threshold for weak disagreement with a virtue."""

    DISAGREE: ClassVar[int] = -25
    """The threshold for mild disagreement with a virtue."""

    STRONG_DISAGREE: ClassVar[int] = -35
    """The threshold for strong disagreement with a virtue."""

    __slots__ = "_virtues"

    _virtues: npt.NDArray[np.int32]
    """An array representing the values of virtues."""

    def __init__(self, overrides: Optional[Dict[str, int]] = None) -> None:
        """
        Parameters
        ----------
        overrides
            Optionally override any virtue with a new value.
        """
        super().__init__()
        self._virtues = np.zeros(len(Virtue), dtype=np.int32)  # type: ignore

        if overrides:
            for trait, value in overrides.items():
                self[Virtue[trait]] = value

    def compatibility(self, other: Virtues) -> int:
        """Calculates the similarity between two Virtue components.

        Parameters
        ----------
        other
            The other set of virtues to compare to

        Returns
        -------
        int
            Similarity score on the range [-100, 100]


        Notes
        -----
        This method uses a combination of cosine similarity and similarity in magnitude to calculate the overall
        similarity of two sets of virtues.
        """
        # Cosine similarity is a value between -1 and 1
        norm_product: float = float(
            np.linalg.norm(self._virtues) * np.linalg.norm(other._virtues)  # type: ignore
        )

        if norm_product == 0:
            cosine_similarity = 0.0
        else:
            cosine_similarity = float(np.dot(self._virtues, other._virtues) / norm_product)  # type: ignore

        # Distance similarity is a value between -1 and 1
        max_distance = 509.9019513592785  # This the maximum difference in the magnitudes of the virtue vectors
        distance = float(np.linalg.norm(self._virtues - other._virtues))  # type: ignore
        distance_similarity = 2.0 * (1.0 - (distance / max_distance)) - 1.0

        similarity: int = round(100 * ((cosine_similarity + distance_similarity) / 2.0))

        return similarity

    def get_high_values(self, n: int = 3) -> List[Virtue]:
        """Return the virtues with n-highest values.

        Returns
        -------
        List[Virtue]
            A list of virtues.
        """
        sorted_index_array = np.argsort(self._virtues)[-n:]  # type: ignore

        value_names = list(Virtue)

        return [value_names[i] for i in sorted_index_array]

    def get_low_values(self, n: int = 3) -> List[Virtue]:
        """Return the virtues with the n-lowest values.

        Returns
        -------
        List[Virtue]
            A list of virtues.
        """
        sorted_index_array = np.argsort(self._virtues)[:n]  # type: ignore

        value_names = list(Virtue)

        return [value_names[i] for i in sorted_index_array]

    def __getitem__(self, item: Virtue) -> int:
        return int(self._virtues[item])

    def __setitem__(self, item: Virtue, value: int) -> None:
        self._virtues[item] = max(Virtues.VIRTUE_MIN, min(Virtues.VIRTUE_MAX, value))

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return "{}({})".format(
            self.__class__.__name__,
            {
                virtue.name: int(self._virtues[i])
                for i, virtue in enumerate(list(Virtue))
            },
        )

    def __iter__(self) -> Iterator[Tuple[Virtue, int]]:
        virtue_dict = {
            virtue: int(self._virtues[i]) for i, virtue in enumerate(list(Virtue))
        }

        return virtue_dict.items().__iter__()

    def to_dict(self) -> Dict[str, Any]:
        return {
            virtue.name: int(self._virtues[i]) for i, virtue in enumerate(list(Virtue))
        }


class Pregnant(IStatus):
    """Tags a character as pregnant and tracks relevant information."""

    __slots__ = "_partner"

    _partner: GameObject
    """The GameObject ID of the character that impregnated this character."""

    def __init__(self, year_created: int, partner: GameObject) -> None:
        """
        Parameters
        ----------
        partner
            The character that got this one pregnant.
        """
        super().__init__(year_created)
        self._partner = partner

    @property
    def partner(self) -> GameObject:
        return self._partner

    def __str__(self) -> str:
        return f"{type(self).__name__}(partner={self.partner.name})"

    def __repr__(self) -> str:
        return f"{type(self).__name__}(partner={self.partner.name})"

    def to_dict(self) -> Dict[str, Any]:
        return {
            **super().to_dict(),
            "partner": self.partner.uid,
        }


class Family(IRelationshipStatus):
    """Tags the relationship owner as a member of the target's family."""

    pass


class ParentOf(IRelationshipStatus):
    """Tags the relationship owner as the parent of the target."""

    pass


class ChildOf(IRelationshipStatus):
    """Tags the relationship owner as the child of the target."""

    pass


class SiblingOf(IRelationshipStatus):
    """Tags the relationship owner as a sibling of the target."""

    pass


class Married(IRelationshipStatus):
    """Tags two characters as being married"""

    pass


class Dating(IRelationshipStatus):
    """Tags two characters as dating"""

    pass


@dataclasses.dataclass()
class MarriageConfig(Component):
    """A component that tracks configuration settings for marriage."""

    spouse_prefabs: List[str] = dataclasses.field(default_factory=list)
    """The names the prefabs of potential spouses when spawning a character."""

    chance_spawn_with_spouse: float = 0.5
    """The probability of this character spawning with a spouse."""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chance_spawn_with_spouse": self.chance_spawn_with_spouse,
            "spouse_prefabs": self.spouse_prefabs,
        }


@dataclasses.dataclass()
class AgingConfig(Component):
    """A component that tracks configuration settings for aging."""

    adolescent_age: int
    """The age the character is considered an adolescent."""

    young_adult_age: int
    """The age the character is considered a young-adult."""

    adult_age: int
    """The age the character is considered an adult."""

    senior_age: int
    """The age the character is considered to be a senior."""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "adolescent_age": self.adolescent_age,
            "young_adult_age": self.young_adult_age,
            "adult_age": self.adult_age,
            "senior_age": self.senior_age,
        }


@dataclasses.dataclass()
class ReproductionConfig(Component):
    """A component that track configuration settings about reproduction."""

    max_children_at_spawn: int = 3
    """The maximum number of children this character can spawn with."""

    child_prefabs: List[str] = dataclasses.field(default_factory=list)
    """The names of prefabs that can spawn as children."""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_children_at_spawn": self.max_children_at_spawn,
            "child_prefabs": self.child_prefabs,
        }


class GenderType(enum.Enum):
    """An enumeration tracking gender expression."""

    Male = enum.auto()
    Female = enum.auto()
    NonBinary = enum.auto()
    NotSpecified = enum.auto()


class Gender(Component, ISerializable):
    """A component that tracks a character's gender expression."""

    __slots__ = "gender"

    gender: GenderType
    """The character's current gender."""

    def __init__(self, gender: Union[str, GenderType] = "NotSpecified") -> None:
        """
        Parameters
        ----------
        gender
            The character's current gender.
        """
        super().__init__()
        self.gender = gender if isinstance(gender, GenderType) else GenderType[gender]

    def __str__(self) -> str:
        return f"{type(self).__name__}({self.gender.name})"

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.gender.name})"

    def to_dict(self) -> Dict[str, Any]:
        return {"gender": self.gender.name}


class LifeStageType(enum.IntEnum):
    """An enumeration of all the various life stages aging characters pass through."""

    Child = 0
    Adolescent = enum.auto()
    YoungAdult = enum.auto()
    Adult = enum.auto()
    Senior = enum.auto()


class LifeStage(Component, ISerializable):
    """A component that tracks the current life stage of a character."""

    __slots__ = "life_stage"

    life_stage: LifeStageType
    """The character's current life stage."""

    def __init__(self, life_stage: Union[str, LifeStageType] = "YoungAdult") -> None:
        """
        Parameters
        ----------
        life_stage
            The character's current life stage.
        """
        super().__init__()
        self.life_stage = (
            life_stage
            if isinstance(life_stage, LifeStageType)
            else LifeStageType[life_stage]
        )

    def __str__(self) -> str:
        return f"{type(self).__name__}({self.life_stage.name})"

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.life_stage.name})"

    def to_dict(self) -> Dict[str, Any]:
        return {"life_stage": self.life_stage.name}


class Immortal(IInheritable, ITrait):
    @classmethod
    def get_conflicts(cls) -> FrozenSet[Type[ITrait]]:
        """Get component types that this component's type conflicts with."""
        return frozenset({})

    @classmethod
    def inheritance_probability(cls) -> Tuple[float, float]:
        return 0, 1.0
