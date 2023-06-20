from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import (
    Any,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Type,
)

from ordered_set import OrderedSet

from neighborly.core.ecs import Component, Event, GameObject, World, ISerializable
from neighborly.core.roles import Role, RoleList
from neighborly.core.time import SimDateTime


class LifeEvent(Event, ABC):
    """An event of significant importance in a GameObject's life"""

    _next_event_id: int = 0

    __slots__ = "_roles", "_timestamp", "_uid"

    def __init__(
        self,
        timestamp: SimDateTime,
        roles: Iterable[Role],
    ) -> None:
        """
        Parameters
        ----------
        timestamp
            Timestamp for when this event
        roles
            The names of roles mapped to GameObjects
        """
        self._uid: int = LifeEvent._next_event_id
        LifeEvent._next_event_id += 1
        self._timestamp: SimDateTime = timestamp.copy()
        self._roles: RoleList = RoleList(roles)

    def get_id(self) -> int:
        return self._uid

    def get_timestamp(self) -> SimDateTime:
        return self._timestamp

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this LifeEvent to a dictionary"""
        return {
            "type": self.get_type(),
            "timestamp": str(self._timestamp),
            "roles": [role.to_dict() for role in self._roles],
        }

    def iter_roles(self) -> Iterator[Role]:
        return self._roles.__iter__()

    def __getitem__(self, role_name: str) -> GameObject:
        return self._roles[role_name]

    def __repr__(self) -> str:
        return "{}(timestamp={}, roles=[{}])".format(
            self.get_type(), str(self.get_timestamp()), self._roles
        )

    def __str__(self) -> str:
        return "{} [@ {}] {}".format(
            self.get_type(),
            str(self.get_timestamp()),
            ", ".join([str(role) for role in self._roles]),
        )

    def __eq__(self, __o: object) -> bool:
        if isinstance(__o, LifeEvent):
            return self._uid == __o._uid
        raise TypeError(f"Expected type Event, but was {type(__o)}")

    def __le__(self, other: LifeEvent) -> bool:
        return self._uid <= other._uid

    def __lt__(self, other: LifeEvent) -> bool:
        return self._uid < other._uid

    def __ge__(self, other: LifeEvent) -> bool:
        return self._uid >= other._uid

    def __gt__(self, other: LifeEvent) -> bool:
        return self._uid > other._uid


class RandomLifeEvent(LifeEvent):
    """User-facing class for implementing behaviors around life events.

    Notes
    -----
    This is adapted from:
    https://github.com/ianhorswill/CitySimulator/blob/master/Assets/Codes/Action/Actions/ActionType.cs
    """

    __slots__ = "_roles"

    def __init__(
        self,
        timestamp: SimDateTime,
        roles: Iterable[Role],
    ) -> None:
        """
        Parameters
        ----------
        timestamp
            Timestamp for when this event
        roles
            The names of roles mapped to GameObjects
        """
        super().__init__(timestamp, roles)

    @abstractmethod
    def get_probability(self) -> float:
        """Get the probability of an instance of this event happening

        Returns
        -------
        float
            The probability of the event given the GameObjects bound
            to the roles in the LifeEventInstance
        """
        raise NotImplementedError

    @abstractmethod
    def execute(self, world: World) -> None:
        """Executes the LifeEvent instance, emitting an event."""
        raise NotImplementedError

    def is_valid(self, world: World) -> bool:
        """Check that all gameobjects still meet the preconditions for their roles."""
        return self.instantiate(world, bindings=self._roles) is not None

    @classmethod
    @abstractmethod
    def instantiate(
        cls,
        world: World,
        bindings: RoleList,
    ) -> Optional[RandomLifeEvent]:
        """Attempts to create a new LifeEvent instance

        Parameters
        ----------
        world
            Neighborly world instance
        bindings
            Suggested bindings of role names mapped to GameObjects

        Returns
        -------
        LifeEventInstance or None
            An instance of this life event if all roles are bound successfully
        """
        raise NotImplementedError


class RandomLifeEventLibrary:
    """Class used to store LifeEvents that can be triggered randomly."""

    __slots__ = "_event_types"

    _event_types: OrderedSet[Type[RandomLifeEvent]]
    """Collection of RandomLifeEvent types used in the simulation."""

    def __init__(self) -> None:
        self._event_types = OrderedSet([])

    def add(self, life_event_type: Type[RandomLifeEvent]) -> None:
        """Register a new random LifeEvent type"""
        self._event_types.add(life_event_type)

    def pick_one(self, rng: random.Random) -> Type[RandomLifeEvent]:
        """
        Return a random registered random life event

        Parameters
        ----------
        rng
            A random number generator

        Returns
        -------
        Type[RandomLifeEvent]
            A randomly-chosen random event from the registry
        """
        return rng.choice(list(self._event_types))

    def __len__(self) -> int:
        """Get the number of registered random life events."""
        return len(self._event_types)


class EventHistory(Component, ISerializable):
    """Stores a record of all past events for a specific GameObject."""

    __slots__ = "_history"

    _history: List[LifeEvent]
    """A list of events in chronological-order."""

    def __init__(self) -> None:
        super().__init__()
        self._history = []

    def append(self, event: LifeEvent) -> None:
        """Record a new life event.

        Parameters
        ----------
        event
            The event to record.
        """
        self._history.append(event)

    def __iter__(self) -> Iterator[LifeEvent]:
        return self._history.__iter__()

    def to_dict(self) -> Dict[str, Any]:
        return {"events": [e.get_id() for e in self._history]}

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return "{}({})".format(
            self.__class__.__name__,
            [f"{type(e).__name__}({e.get_id()})" for e in self._history],
        )


class EventLog(ISerializable):
    """Stores a record of all past life events."""

    __slots__ = "_history"

    _history: Dict[int, LifeEvent]
    """All recorded life events mapped to their event ID."""

    def __init__(self) -> None:
        super().__init__()
        self._history = {}

    def append(self, event: LifeEvent) -> None:
        """Record a new life event.

        Parameters
        ----------
        event
            The event to record.
        """
        self._history[event.get_id()] = event

    def to_dict(self) -> Dict[str, Any]:
        return {str(key): entry.to_dict() for key, entry in self._history.items()}

    def __iter__(self) -> Iterator[LifeEvent]:
        return self._history.values().__iter__()

    def __getitem__(self, key: int) -> LifeEvent:
        return self._history[key]
