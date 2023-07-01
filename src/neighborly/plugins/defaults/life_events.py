from __future__ import annotations

import random
from typing import Any, List, Optional

from neighborly.command import SetCharacterName
from neighborly.components.business import Business, OpenForBusiness
from neighborly.components.character import (
    CanGetPregnant,
    Dating,
    GameCharacter,
    LifeStage,
    LifeStageType,
    Married,
    ParentOf,
    Pregnant,
)
from neighborly.components.residence import Residence, Resident
from neighborly.components.shared import Age, Lifespan
from neighborly.config import NeighborlyConfig
from neighborly.core.ecs import Active, GameObject, World
from neighborly.core.life_event import (
    EventRole,
    EventRoleList,
    RandomLifeEvent,
    RandomLifeEventLibrary,
)
from neighborly.core.query import QB
from neighborly.core.relationship import (
    Relationship,
    RelationshipManager,
    Romance,
    add_relationship_status,
    get_relationship,
    get_relationships_with_statuses,
    has_relationship,
    remove_relationship_status,
)
from neighborly.core.status import add_status, has_status
from neighborly.core.time import DAYS_PER_YEAR, SimDateTime
from neighborly.plugins.defaults.actions import Die
from neighborly.simulation import Neighborly, PluginInfo
from neighborly.utils.common import set_residence, shutdown_business
from neighborly.utils.query import are_related, is_married, is_single, with_relationship


class StartDatingLifeEvent(RandomLifeEvent):
    def __init__(
        self, world: World, date: SimDateTime, initiator: GameObject, other: GameObject
    ) -> None:
        super().__init__(
            world, date, [EventRole("Initiator", initiator), EventRole("Other", other)]
        )

    def get_probability(self) -> float:
        return 1

    def execute(self) -> None:
        initiator = self["Initiator"]
        other = self["Other"]

        add_relationship_status(initiator, other, Dating())
        add_relationship_status(other, initiator, Dating())

    @staticmethod
    def _bind_initiator(
        world: World, candidate: Optional[GameObject] = None
    ) -> Optional[GameObject]:
        if candidate:
            candidates = [candidate]
        else:
            candidates = [
                world.gameobject_manager.get_gameobject(result[0])
                for result in world.get_components((GameCharacter, Active))
            ]

        candidates = [
            c
            for c in candidates
            if is_single(c)
            and c.get_component(LifeStage).life_stage >= LifeStageType.Adolescent
        ]

        if candidates:
            return world.resource_manager.get_resource(random.Random).choice(candidates)

        return None

    @staticmethod
    def _bind_other(
        world: World, initiator: GameObject, candidate: Optional[GameObject] = None
    ) -> Optional[GameObject]:
        romance_threshold = world.resource_manager.get_resource(
            NeighborlyConfig
        ).settings.get("dating_romance_threshold", 25)

        if candidate:
            if has_relationship(initiator, candidate) and has_relationship(
                candidate, initiator
            ):
                candidates = [candidate]
            else:
                return None
        else:
            candidates = [
                c for c in initiator.get_component(RelationshipManager).outgoing
            ]

        matches: List[GameObject] = []

        for character in candidates:
            outgoing_relationship = get_relationship(initiator, character)
            incoming_relationship = get_relationship(character, initiator)

            outgoing_romance = outgoing_relationship.get_component(Romance)
            incoming_romance = incoming_relationship.get_component(Romance)

            if not character.has_component(Active):
                continue

            if character.get_component(LifeStage).life_stage < LifeStageType.Adolescent:
                continue

            if not is_single(character):
                continue

            if outgoing_romance.get_value() < romance_threshold:
                continue

            if incoming_romance.get_value() < romance_threshold:
                continue

            if are_related(initiator, character):
                continue

            if character == initiator:
                continue

            matches.append(character)

        if matches:
            return world.resource_manager.get_resource(random.Random).choice(matches)

        return None

    @classmethod
    def instantiate(
        cls,
        world: World,
        bindings: Optional[EventRoleList] = None,
    ) -> Optional[RandomLifeEvent]:
        bindings = bindings if bindings is not None else EventRoleList()

        initiator = cls._bind_initiator(world, bindings.get_first_or_none("Initiator"))

        if initiator is None:
            return None

        other = cls._bind_other(world, initiator, bindings.get_first_or_none("Other"))

        if other is None:
            return None

        return cls(
            world, world.resource_manager.get_resource(SimDateTime), initiator, other
        )


class DatingBreakUp(RandomLifeEvent):
    def __init__(
        self, world: World, date: SimDateTime, initiator: GameObject, other: GameObject
    ) -> None:
        super().__init__(
            world, date, [EventRole("Initiator", initiator), EventRole("Other", other)]
        )

    def get_probability(self) -> float:
        return 1

    def execute(self) -> None:
        initiator = self["Initiator"]
        other = self["Other"]

        remove_relationship_status(initiator, other, Dating)
        remove_relationship_status(other, initiator, Dating)

    @staticmethod
    def _bind_initiator(
        world: World, candidate: Optional[GameObject] = None
    ) -> Optional[GameObject]:
        if candidate:
            candidates = [candidate]
        else:
            candidates = [
                world.gameobject_manager.get_gameobject(result[0])
                for result in world.get_components((GameCharacter, Active))
            ]

        candidates = [
            c for c in candidates if len(get_relationships_with_statuses(c, Dating)) > 0
        ]

        if candidates:
            return world.resource_manager.get_resource(random.Random).choice(candidates)

        return None

    @staticmethod
    def _bind_other(
        world: World, initiator: GameObject, candidate: Optional[GameObject] = None
    ) -> Optional[GameObject]:
        romance_threshold = world.resource_manager.get_resource(
            NeighborlyConfig
        ).settings.get("breakup_romance_thresh", -10)

        if candidate:
            if has_relationship(initiator, candidate) and has_relationship(
                candidate, initiator
            ):
                candidates = [candidate]
            else:
                return None
        else:
            candidates = [
                c for c in initiator.get_component(RelationshipManager).outgoing
            ]

        matches: List[GameObject] = []

        for character in candidates:
            outgoing_relationship = get_relationship(initiator, character)

            outgoing_romance = outgoing_relationship.get_component(Romance)

            if not has_status(outgoing_relationship, Dating):
                continue

            if outgoing_romance.get_value() > romance_threshold:
                continue

            matches.append(character)

        if matches:
            return world.resource_manager.get_resource(random.Random).choice(matches)

        return None

    @classmethod
    def instantiate(
        cls,
        world: World,
        bindings: Optional[EventRoleList] = None,
    ) -> Optional[RandomLifeEvent]:
        bindings = bindings if bindings is not None else EventRoleList()

        initiator = cls._bind_initiator(world, bindings.get_first_or_none("Initiator"))

        if initiator is None:
            return None

        other = cls._bind_other(world, initiator, bindings.get_first_or_none("Other"))

        if other is None:
            return None

        return cls(
            world, world.resource_manager.get_resource(SimDateTime), initiator, other
        )


class DivorceLifeEvent(RandomLifeEvent):
    @classmethod
    def instantiate(
        cls,
        world: World,
        bindings: Optional[EventRoleList] = None,
    ) -> Optional[RandomLifeEvent]:
        query = QB.query(
            ("Initiator", "Other"),
            QB.with_((GameCharacter, Active), "Initiator"),
            with_relationship("Initiator", "Other", "?relationship"),
            QB.with_(Married, "?relationship"),
            QB.filter_(
                lambda rel: rel.get_component(Romance).get_value()
                <= rel.world.resource_manager.get_resource(
                    NeighborlyConfig
                ).settings.get("divorce_romance_thresh", -25),
                "?relationship",
            ),
        )

        if bindings:
            results = query.execute(world, {r.name: r.gameobject.uid for r in bindings})
        else:
            results = query.execute(world)

        if results:
            chosen_result = world.resource_manager.get_resource(random.Random).choice(
                results
            )
            chosen_objects = [
                world.gameobject_manager.get_gameobject(uid) for uid in chosen_result
            ]
            roles = dict(zip(query.get_symbols(), chosen_objects))
            return cls(
                world,
                world.resource_manager.get_resource(SimDateTime),
                [EventRole(title, gameobject) for title, gameobject in roles.items()],
            )

    def get_probability(self) -> float:
        return 0.8

    def execute(self):
        initiator = self["Initiator"]
        ex_spouse = self["Other"]

        remove_relationship_status(initiator, ex_spouse, Married)
        remove_relationship_status(ex_spouse, initiator, Married)


class MarriageLifeEvent(RandomLifeEvent):
    def __init__(
        self, world: World, date: SimDateTime, initiator: GameObject, other: GameObject
    ) -> None:
        super().__init__(
            world, date, [EventRole("Initiator", initiator), EventRole("Other", other)]
        )

    @staticmethod
    def _bind_initiator(
        world: World, candidate: Optional[GameObject] = None
    ) -> Optional[GameObject]:
        if candidate:
            candidates = [candidate]
        else:
            candidates = [
                world.gameobject_manager.get_gameobject(result[0])
                for result in world.get_components((GameCharacter, Active))
            ]

        candidates = [
            c for c in candidates if len(get_relationships_with_statuses(c, Dating)) > 0
        ]

        if candidates:
            return world.resource_manager.get_resource(random.Random).choice(candidates)

        return None

    @staticmethod
    def _bind_other(
        world: World, initiator: GameObject, candidate: Optional[GameObject] = None
    ) -> Optional[GameObject]:
        romance_threshold = world.resource_manager.get_resource(
            NeighborlyConfig
        ).settings.get("marriage_romance_threshold", 60)

        current_date = world.resource_manager.get_resource(SimDateTime)

        if candidate:
            if has_relationship(initiator, candidate) and has_relationship(
                candidate, initiator
            ):
                candidates = [candidate]
            else:
                return None
        else:
            candidates = [
                c for c in initiator.get_component(RelationshipManager).outgoing
            ]

        matches: List[GameObject] = []

        for character in candidates:
            outgoing_relationship = get_relationship(initiator, character)
            incoming_relationship = get_relationship(character, initiator)

            outgoing_romance = outgoing_relationship.get_component(Romance)
            incoming_romance = incoming_relationship.get_component(Romance)

            if dating := outgoing_relationship.try_component(Dating):
                if (current_date - dating.created).years < 1:
                    continue
            else:
                continue

            if not has_status(incoming_relationship, Dating):
                continue

            if not character.has_component(Active):
                continue

            if outgoing_romance.get_value() < romance_threshold:
                continue

            if incoming_romance.get_value() < romance_threshold:
                continue

            if character == initiator:
                continue

            matches.append(character)

        if matches:
            return world.resource_manager.get_resource(random.Random).choice(matches)

        return None

    @classmethod
    def instantiate(
        cls,
        world: World,
        bindings: Optional[EventRoleList] = None,
    ) -> Optional[RandomLifeEvent]:
        bindings = bindings if bindings is not None else EventRoleList()

        initiator = cls._bind_initiator(world, bindings.get_first_or_none("Initiator"))

        if initiator is None:
            return None

        other = cls._bind_other(world, initiator, bindings.get_first_or_none("Other"))

        if other is None:
            return None

        return cls(
            world, world.resource_manager.get_resource(SimDateTime), initiator, other
        )

    def get_probability(self) -> float:
        return 0.8

    def execute(self) -> None:
        initiator = self["Initiator"]
        other = self["Other"]

        remove_relationship_status(initiator, other, Dating)
        remove_relationship_status(other, initiator, Dating)
        add_relationship_status(initiator, other, Married())
        add_relationship_status(other, initiator, Married())

        # Move in together
        former_residence = other.get_component(Resident).residence
        new_residence = initiator.get_component(Resident).residence

        movers: List[GameObject] = [
            *former_residence.get_component(Residence).residents
        ]

        for character in movers:
            is_owner = former_residence.get_component(Residence).is_owner(character)
            set_residence(character, new_residence, is_owner)

        # Change last names
        new_last_name = initiator.get_component(GameCharacter).last_name

        SetCharacterName(other, last_name=new_last_name).execute(world)

        for relationship in get_relationships_with_statuses(other, ParentOf):
            target = relationship.get_component(Relationship).target

            if target not in movers:
                continue

            if not target.has_component(Active):
                continue

            if target.get_component(
                LifeStage
            ).life_stage < LifeStageType.YoungAdult and not is_married(target):
                SetCharacterName(target, last_name=new_last_name).execute(world)


class GetPregnantLifeEvent(RandomLifeEvent):
    """Defines an event where two characters stop dating"""

    def __init__(
        self,
        world: World,
        date: SimDateTime,
        pregnant_one: GameObject,
        other: GameObject,
    ) -> None:
        super().__init__(
            world,
            date,
            [EventRole("PregnantOne", pregnant_one), EventRole("Other", other)],
        )

    @staticmethod
    def _bind_pregnant_one(
        world: World, candidate: Optional[GameObject] = None
    ) -> Optional[GameObject]:
        if candidate:
            candidates = [candidate]
        else:
            candidates = [
                world.gameobject_manager.get_gameobject(result[0])
                for result in world.get_components((GameCharacter, Active))
            ]

        candidates = [
            c
            for c in candidates
            if c.has_component(CanGetPregnant) and not c.has_component(Pregnant)
        ]

        if candidates:
            return world.resource_manager.get_resource(random.Random).choice(candidates)

        return None

    @staticmethod
    def _bind_other(
        world: World, initiator: GameObject, candidate: Optional[GameObject] = None
    ) -> Optional[GameObject]:
        if candidate:
            if has_relationship(initiator, candidate) and has_relationship(
                candidate, initiator
            ):
                candidates = [candidate]
            else:
                return None
        else:
            candidates = [
                c for c in initiator.get_component(RelationshipManager).outgoing
            ]

        matches: List[GameObject] = []

        for character in candidates:
            outgoing_relationship = get_relationship(initiator, character)

            if not character.has_component(Active):
                continue

            if not (
                has_status(outgoing_relationship, Dating)
                or has_status(outgoing_relationship, Married)
            ):
                continue

            matches.append(character)

        if matches:
            return world.resource_manager.get_resource(random.Random).choice(matches)

        return None

    @classmethod
    def instantiate(
        cls,
        world: World,
        bindings: Optional[EventRoleList] = None,
    ) -> Optional[RandomLifeEvent]:
        bindings = bindings if bindings is not None else EventRoleList()

        pregnant_one = cls._bind_pregnant_one(
            world, bindings.get_first_or_none("Initiator")
        )

        if pregnant_one is None:
            return None

        other = cls._bind_other(
            world, pregnant_one, bindings.get_first_or_none("Other")
        )

        if other is None:
            return None

        return cls(
            world, world.resource_manager.get_resource(SimDateTime), pregnant_one, other
        )

    def execute(self):
        current_date = self["PregnantOne"].world.resource_manager.get_resource(
            SimDateTime
        )
        due_date = current_date.copy()
        due_date.increment(months=9)

        add_status(
            self["PregnantOne"],
            Pregnant(
                partner_id=self["Other"].uid,
                due_date=due_date,
            ),
        )

    def get_probability(self):
        gameobject = self["PregnantOne"]
        num_children = len(get_relationships_with_statuses(gameobject, ParentOf))

        return 1.0 - (num_children / 5.0)


class DieOfOldAge(RandomLifeEvent):
    """Characters can randomly die of old age"""

    @classmethod
    def instantiate(
        cls,
        world: World,
        bindings: Optional[EventRoleList] = None,
    ) -> Optional[RandomLifeEvent]:
        query = QB.query(
            "Deceased",
            QB.with_((GameCharacter, Active), "Deceased"),
            QB.filter_(
                lambda gameobject: gameobject.get_component(Age).value
                >= gameobject.get_component(Lifespan).value,
                "Deceased",
            ),
        )

        if bindings:
            results = query.execute(world, {r.name: r.gameobject.uid for r in bindings})
        else:
            results = query.execute(world)

        if results:
            chosen_result = world.resource_manager.get_resource(random.Random).choice(
                results
            )
            chosen_objects = [
                world.gameobject_manager.get_gameobject(uid) for uid in chosen_result
            ]
            roles = dict(zip(query.get_symbols(), chosen_objects))
            return cls(
                world,
                world.resource_manager.get_resource(SimDateTime),
                [EventRole(title, gameobject) for title, gameobject in roles.items()],
            )

    def get_probability(self) -> float:
        character = self["Deceased"]
        age = float(character.get_component(Age).value)
        lifespan = float(character.get_component(Lifespan).value)

        return age / (lifespan + 10.0)

    def execute(self) -> None:
        Die(self["Deceased"]).evaluate()


class GoOutOfBusiness(RandomLifeEvent):
    """Businesses can randomly go out of business"""

    def execute(self) -> None:
        business = self["Business"]

        owner = business.get_component(Business).owner

        shutdown_business(self["Business"])

    def get_probability(self) -> float:
        business = self["Business"]
        lifespan = business.get_component(Lifespan).value
        current_date = business.world.resource_manager.get_resource(SimDateTime)

        years_in_business = (
            float(
                (
                    current_date - business.get_component(OpenForBusiness).created
                ).total_days
            )
            / DAYS_PER_YEAR
        )

        return (years_in_business / (lifespan + 10)) ** 2

    @classmethod
    def instantiate(
        cls,
        world: World,
        bindings: Optional[EventRoleList] = None,
    ) -> Optional[RandomLifeEvent]:
        query = QB.query(
            "Business", QB.with_((Business, OpenForBusiness, Active), "Business")
        )

        processed_bindings = (
            {r.name: r.gameobject.uid for r in bindings} if bindings else {}
        )

        if results := query.execute(world, processed_bindings):
            chosen_result = world.resource_manager.get_resource(random.Random).choice(
                results
            )
            chosen_objects = [
                world.gameobject_manager.get_gameobject(uid) for uid in chosen_result
            ]
            roles = dict(zip(query.get_symbols(), chosen_objects))
            return cls(
                world,
                world.resource_manager.get_resource(SimDateTime),
                [EventRole(title, gameobject) for title, gameobject in roles.items()],
            )


plugin_info = PluginInfo(
    name="default life events plugin",
    plugin_id="default.life-events",
    version="0.1.0",
)


def setup(sim: Neighborly, **kwargs: Any):
    event_library = sim.world.resource_manager.get_resource(RandomLifeEventLibrary)
    # event_library.add(MarriageLifeEvent)
    # event_library.add(StartDatingLifeEvent)
    # event_library.add(DatingBreakUp)
    # event_library.add(DivorceLifeEvent)
    event_library.add(GetPregnantLifeEvent)
    event_library.add(DieOfOldAge)
    event_library.add(GoOutOfBusiness)
