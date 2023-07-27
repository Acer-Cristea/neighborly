"""Neighborly Relationship Module.

Relationships between agents are at the core of social simulation. Neighborly represents relationships as independent
GameObjects that collectively form a directed graph. This means that each relationship has an owner and a target, and
characters can have asymmetrical feeling toward each other. All relationship GameObjects have a Relationship component
that tracks the owner and target of the relationships. They also have one or more RelationshipStat components that
track things like feelings of friendship, romance, trust, and reputation.

"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict, Iterator, List, Protocol, Type, Union

from ordered_set import OrderedSet

from neighborly import Event
from neighborly.core.ecs import Component, GameObject, ISerializable, World
from neighborly.stat_system import ClampedStatComponent, StatComponent
from neighborly.status_system import Statuses


class Friendship(ClampedStatComponent):
    """Tracks platonic affinity from one character to another."""

    def __init__(self):
        super().__init__(base_value=0, max_value=100, min_value=-100)


class Romance(ClampedStatComponent):
    """Tracks romantic affinity from one character to another."""

    def __init__(self):
        super().__init__(base_value=0, max_value=100, min_value=-100)


class InteractionScore(ClampedStatComponent):
    """Tracks a score for how often characters interact in a year."""

    def __init__(self):
        super().__init__(base_value=0, max_value=100, min_value=0)


class RomanticCompatibility(StatComponent):
    def __init__(self) -> None:
        super().__init__(base_value=0)


class PlatonicCompatibility(StatComponent):
    def __init__(self) -> None:
        super().__init__(base_value=0)


class Relationship(Component, ISerializable):
    """Tags a GameObject as a relationship and tracks the owner and target."""

    __slots__ = ("_target", "_owner", "_active_rules")

    _owner: GameObject
    """Who owns this relationship."""

    _target: GameObject
    """Who is the relationship directed toward."""

    _active_rules: List[ISocialRule]
    """Social rules currently applied to this relationship."""

    def __init__(self, owner: GameObject, target: GameObject) -> None:
        super().__init__()
        self._owner = owner
        self._target = target
        self._active_rules = []

    @property
    def owner(self) -> GameObject:
        return self._owner

    @property
    def target(self) -> GameObject:
        return self._target

    def on_add(self, gameobject: GameObject) -> None:
        self.owner.get_component(Relationships).outgoing[self.target] = gameobject
        self.target.get_component(Relationships).incoming[self.owner] = gameobject

    def on_remove(self, gameobject: GameObject) -> None:
        del self.owner.get_component(Relationships).outgoing[self.target]
        del self.target.get_component(Relationships).incoming[self.owner]

    def add_rule(self, rule: ISocialRule) -> None:
        """Apply a social rule to the relationship."""
        self._active_rules.append(rule)

    def remove_rule(self, rule: ISocialRule) -> None:
        """Remove a social rule from the relationship."""
        self._active_rules.remove(rule)

    def iter_active_rules(self) -> Iterator[ISocialRule]:
        """Return iterator to active rules."""
        return self._active_rules.__iter__()

    def clear_active_rules(self) -> None:
        """Clear all active rules."""
        self._active_rules.clear()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "owner": self.owner.uid,
            "target": self.target.uid,
        }

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return "{}(owner={}, target={})".format(
            self.__class__.__name__, self.owner.name, self.target.name
        )


class Relationships(Component, ISerializable):
    """Tracks all relationships associated with a GameObject.

    Notes
    -----
    This component helps build a directed graph structure within the ECS.
    """

    __slots__ = "incoming", "outgoing"

    incoming: Dict[GameObject, GameObject]
    """Relationship owners mapped to the Relationship GameObjects."""

    outgoing: Dict[GameObject, GameObject]
    """Relationship targets mapped to the Relationship GameObjects."""

    def __init__(self) -> None:
        super().__init__()
        self.incoming = {}
        self.outgoing = {}

    def add_incoming(self, owner: GameObject, relationship: GameObject) -> None:
        """Add a new incoming relationship.

        Parameters
        ----------
        owner
            The relationship owner.
        relationship
            The relationship.
        """
        self.incoming[owner] = relationship

    def add_outgoing(self, target: GameObject, relationship: GameObject) -> None:
        """Add a new outgoing relationship.

        Parameters
        ----------
        target
            The relationship target.
        relationship
            The relationship.
        """
        self.outgoing[target] = relationship

    def deactivate_relationships(self) -> None:
        """Deactivate all associated relationships."""
        for _, relationship in self.outgoing.items():
            relationship.deactivate()

        for _, relationship in self.incoming.items():
            relationship.deactivate()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "outgoing": {str(k.uid): v.uid for k, v in self.outgoing.items()},
            "incoming": {str(k.uid): v.uid for k, v in self.incoming.items()},
        }

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return "{}(outgoing={}, incoming={})".format(
            self.__class__.__name__, self.outgoing, self.incoming
        )


class ISocialRule(Protocol):
    """An interface for rules that define how characters feel about each other using status effects and modifiers."""

    @property
    @abstractmethod
    def is_active(self) -> bool:
        """Return True if this rule is active."""
        raise NotImplementedError

    @abstractmethod
    def check_preconditions(
        self, owner: GameObject, target: GameObject, relationship: GameObject
    ) -> bool:
        """Check if a relationship passes the preconditions for this rule to apply.

        Parameters
        ----------
        owner
            The relationship's owner.
        target
            The relationship's target.
        relationship
            A relationship from one gameobject to another.

        Returns
        -------
        bool
            True if the relationship passes, False otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    def apply(
        self, owner: GameObject, target: GameObject, relationship: GameObject
    ) -> None:
        """Apply the effects of this rule.

        Parameters
        ----------
        owner
            The relationship's owner.
        target
            The relationship's target.
        relationship
            A relationship from one gameobject to another.
        """
        raise NotImplementedError

    @abstractmethod
    def remove(
        self, owner: GameObject, target: GameObject, relationship: GameObject
    ) -> None:
        """Remove the effects of this rule.

        Parameters
        ----------
        owner
            The relationship's owner.
        target
            The relationship's target.
        relationship
            A relationship from one gameobject to another.
        """
        raise NotImplementedError


class SocialRule(ISocialRule, ABC):
    """An abstract base class for social rules to inherit from."""

    __slots__ = "_active"

    _active: bool
    """Is this rule active."""

    @property
    def is_active(self) -> bool:
        return self._active

    @is_active.setter
    def is_active(self, value: bool) -> None:
        self._active = value


class SocialRuleLibrary:
    """Repository of social rules to use during the simulation."""

    __slots__ = "_rules"

    _rules: OrderedSet[ISocialRule]
    """Collection of all registered rule instances."""

    def __init__(self) -> None:
        self._rules = OrderedSet([])

    def add_rule(self, rule: ISocialRule) -> None:
        """Register a social rule.

        Parameters
        ----------
        rule
            The rule to register.
        """
        self._rules.append(rule)

    def iter_rules(self) -> Iterator[ISocialRule]:
        """Return an iterator to the registered social rules."""
        return self._rules.__iter__()


class RelationshipType(Component, ABC):
    @classmethod
    @abstractmethod
    def instantiate(
        cls, world: World, owner: GameObject, target: GameObject, **kwargs: Any
    ) -> GameObject:
        """Create new residence instance.

        Parameters
        ----------
        world
            The world instance to spawn into.
        owner
            The GameObject that owns the relationship
        target
            The GameObject that is the target of the relationship
        **kwargs
            Additional keyword arguments.

        Returns
        -------
        GameObject
            The residence instance.
        """
        raise NotImplementedError


class BaseRelationship(RelationshipType):
    base_components: ClassVar[Dict[Union[str, Type[Component]], Dict[str, Any]]] = {
        Friendship: {},
        Romance: {},
        InteractionScore: {},
        PlatonicCompatibility: {},
        RomanticCompatibility: {},
    }

    @classmethod
    def instantiate(
        cls, world: World, owner: GameObject, target: GameObject, **kwargs: Any
    ) -> GameObject:
        relationship = world.gameobject_manager.spawn_gameobject(
            components={
                Relationship: {"owner": owner, "target": target},
                **BaseRelationship.base_components,
                Statuses: {},
                cls: {},
            },
            name=f"Rel({owner.name} -> {target.name})",
        )

        return relationship


def add_relationship(owner: GameObject, target: GameObject) -> GameObject:
    """
    Creates a new relationship from the subject to the target

    Parameters
    ----------
    owner
        The GameObject that owns the relationship
    target
        The GameObject that the Relationship is directed toward

    Returns
    -------
    GameObject
        The new relationship instance
    """
    relationships = owner.get_component(Relationships)

    if target in relationships.outgoing:
        return relationships.outgoing[target]

    relationship = BaseRelationship.instantiate(owner.world, owner, target)

    RelationshipCreatedEvent(
        relationship=relationship, owner=owner, target=target
    ).dispatch()

    # Test all the rules in the library and apply those with passing preconditions
    social_rules = owner.world.resource_manager.get_resource(SocialRuleLibrary)

    for rule in social_rules.iter_rules():
        if rule.check_preconditions(owner, target, relationship):
            rule.apply(owner, target, relationship)

    return relationship


def get_relationship(
    subject: GameObject,
    target: GameObject,
) -> GameObject:
    """Get a relationship from one GameObject to another.

    This function will create a new instance of a relationship if one does not exist.

    Parameters
    ----------
    subject
        The owner of the relationship.
    target
        The target of the relationship.

    Returns
    -------
    GameObject
        A relationship instance.
    """
    if target not in subject.get_component(Relationships).outgoing:
        return add_relationship(subject, target)

    return subject.get_component(Relationships).outgoing[target]


def has_relationship(owner: GameObject, target: GameObject) -> bool:
    """Check if there is an existing relationship from the owner to the target.

    Parameters
    ----------
    owner
        The owner of the relationship.
    target
        The target of the relationship.

    Returns
    -------
    bool
        True if there is an existing Relationship between the GameObjects,
        False otherwise.
    """
    return target in owner.get_component(Relationships).outgoing


def get_relationships_with_components(
    gameobject: GameObject, *component_types: Type[Component]
) -> List[GameObject]:
    """Get all the relationships with the given component types.

    Parameters
    ----------
    gameobject
        The character to check for relationships on.
    *component_types
        Component types to check for on relationship instances.

    Returns
    -------
    List[GameObject]
        Relationships with the given component types.
    """
    if len(component_types) == 0:
        return []

    relationship_manager = gameobject.get_component(Relationships)
    matches: List[GameObject] = []

    for _, relationship in relationship_manager.outgoing.items():
        if all([relationship.has_component(st) for st in component_types]):
            matches.append(relationship)

    return matches


class RelationshipCreatedEvent(Event):
    __slots__ = "_relationship", "_owner", "_target"

    def __init__(
        self, relationship: GameObject, owner: GameObject, target: GameObject
    ) -> None:
        super().__init__(world=relationship.world)
        self._relationship = relationship
        self._owner = owner
        self._target = target

    @property
    def relationship(self) -> GameObject:
        return self._relationship

    @property
    def owner(self) -> GameObject:
        return self._owner

    @property
    def target(self) -> GameObject:
        return self._target
