"""
samples/using_statuses.py

This sample shows how to apply and remove statuses from characters.

Statuses are essentially components with a little extra tracking information.
You can use the world's ".get_component(s)(...)" methods to query for their
presence. The only requirement is that game objects have a StatusManager component
attached to user the add_status/has_status utility functions.

This sample builds on the using events sample and adds a pays taxes status to the
character to prevent them from having to pay again.
"""
from dataclasses import dataclass
from typing import Any, Dict

from neighborly import (
    Component,
    Event,
    GameObject,
    ISystem,
    Neighborly,
    NeighborlyConfig,
    SimDateTime,
)
from neighborly.core.status import (
    StatusComponent,
    StatusManager,
    add_status,
    has_status,
)
from neighborly.decorators import component, system

sim = Neighborly(NeighborlyConfig(verbose=False))


@component(sim)
@dataclass
class Actor(Component):
    name: str

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name}


@component(sim)
@dataclass
class Money(Component):
    amount: int

    def to_dict(self) -> Dict[str, Any]:
        return {"amount": self.amount}


@component(sim)
@dataclass
class Job(Component):
    title: str
    salary: int

    def to_dict(self) -> Dict[str, Any]:
        return {"title": self.title, "salary": self.salary}


@component(sim)
class PaysTaxes(StatusComponent):
    pass


@system(sim)
class SalarySystem(ISystem):
    sys_group = "update"

    def process(self, *args: Any, **kwargs: Any):
        for _, (actor, job, money) in self.world.get_components((Actor, Job, Money)):
            money.amount += job.salary // 12
            print(f"{actor.name} has ${money.amount}.")


@system(sim)
class BecomeMillionaireEventSystem(ISystem):
    sys_group = "update"

    def process(self, *args: Any, **kwargs: Any) -> None:
        for guid, money in self.world.get_component(Money):
            character = self.world.get_gameobject(guid)
            if money.amount > 1_000_000:
                character.fire_event(
                    BecomeMillionaireEvent(
                        self.world.get_resource(SimDateTime), character
                    )
                )


class BecomeMillionaireEvent(Event):
    def __init__(self, date: SimDateTime, character: GameObject) -> None:
        super().__init__(date)
        self.character = character


def on_become_millionaire(
    gameobject: GameObject, event: BecomeMillionaireEvent
) -> None:
    actor = gameobject.get_component(Actor)

    if not has_status(gameobject, PaysTaxes):
        print(f"{actor.name} became a millionaire. Here comes the IRS")
        gameobject.get_component(Money).amount -= 750_000
        add_status(gameobject, PaysTaxes())
    else:
        print(f"{actor.name} already paid their taxes.")


# You need to register the event listener with the GameObject class
GameObject.on(BecomeMillionaireEvent, on_become_millionaire)


def main():
    sim.world.spawn_gameobject(
        [Actor("Alice"), Money(0), Job("Intern", 1_000_000), StatusManager()]
    )

    for _ in range(24):
        sim.step()


if __name__ == "__main__":
    main()
