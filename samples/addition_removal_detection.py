"""
samples/addition_removal_detection

This sample script shows how simulation authors can detect when components are added
or removed. This may be helpful when you need to change the state of other components
based on the change in presence of another component. In this example, we add and remove
a status buffer on the character.

Adding new components triggers a ComponentAddedEvent, and we can use the info inside
the event to make changes.
"""
from dataclasses import dataclass
from typing import Any, Dict

from neighborly import Component, Neighborly
from neighborly.core.ecs import ComponentAddedEvent, ComponentRemovedEvent
from neighborly.core.status import StatusManager
from neighborly.decorators import component

sim = Neighborly()


@component(sim.world)
@dataclass
class Actor(Component):
    name: str

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name}


@component(sim.world)
@dataclass
class AdventurerStats(Component):
    attack: int
    defense: int

    def to_dict(self) -> Dict[str, Any]:
        return {"attack": self.attack, "defense": self.defense}


@component(sim.world)
@dataclass()
class AttackBuff(Component):
    amount: int

    def to_dict(self) -> Dict[str, Any]:
        return {"amount": self.amount}


def on_attack_buff_added(event: ComponentAddedEvent) -> None:
    if isinstance(event.component, AttackBuff):
        stats = event.gameobject.get_component(AdventurerStats)
        stats.attack += event.component.amount


def on_attack_buffer_removed(event: ComponentRemovedEvent) -> None:
    if isinstance(event.component, AttackBuff):
        stats = event.gameobject.get_component(AdventurerStats)
        stats.attack -= event.component.amount


sim.world.event_manager.on_event(ComponentAddedEvent, on_attack_buff_added)
sim.world.event_manager.on_event(ComponentRemovedEvent, on_attack_buffer_removed)


def main():
    alice = sim.world.gameobject_manager.spawn_gameobject(
        [Actor("Alice"), StatusManager(), AdventurerStats(5, 7)]
    )

    print(alice.get_component(AdventurerStats))

    alice.add_component(AttackBuff(10))

    print(alice.get_component(AdventurerStats))

    alice.remove_component(AttackBuff)

    print(alice.get_component(AdventurerStats))


if __name__ == "__main__":
    main()
