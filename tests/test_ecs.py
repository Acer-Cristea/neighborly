from dataclasses import dataclass
from typing import Any, Dict

import pytest

from neighborly.core.ecs import (
    Component,
    ComponentNotFoundError,
    GameObjectNotFoundError,
    ISystem,
    ResourceNotFoundError,
    World,
)


@dataclass
class Actor(Component):
    name: str

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name}


@dataclass
class CurrentLocation(Component):
    location: int

    def to_dict(self) -> Dict[str, Any]:
        return {"location": self.location}


@dataclass
class Money(Component):
    amount: int

    def to_dict(self) -> Dict[str, Any]:
        return {"money": self.amount}


@dataclass
class Job(Component):
    title: str
    salary: int

    def to_dict(self) -> Dict[str, Any]:
        return {"title": self.title, "salary": self.salary}


@dataclass
class Location(Component):
    name: str

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name}


class ComponentA(Component):
    pass


class ComponentB(Component):
    pass


@dataclass
class FakeResource:
    config_value: int = 5


@dataclass
class AnotherFakeResource:
    config_value: int = 43


class SalarySystem(ISystem):
    def on_update(self, world: World) -> None:
        for _, (job, money) in world.get_components((Job, Money)):
            money.amount += job.salary


#########################################
# TEST WORLD GAMEOBJECT-RELATED METHODS
#########################################


def test_spawn_gameobject():
    """Test that gameobjects are spawned properly"""
    world = World()

    adrian = world.gameobject_manager.spawn_gameobject([Actor("Adrian")])

    assert adrian.exists is True
    assert world.gameobject_manager.has_gameobject(adrian)
    assert adrian.get_component(Actor).name == "Adrian"

    jamie = world.gameobject_manager.spawn_gameobject(name="Jamie")

    assert jamie.exists is True
    assert jamie.name == "Jamie"
    assert world.gameobject_manager.has_gameobject(jamie)


def test_get_gameobject():
    world = World()
    gameobject = world.gameobject_manager.spawn_gameobject()
    assert world.gameobject_manager.get_gameobject(gameobject.uid) == gameobject


def test_get_gameobject_raises_exception():
    with pytest.raises(GameObjectNotFoundError):
        world = World()
        world.gameobject_manager.get_gameobject(7)


def test_has_gameobject():
    world = World()
    gameobject = world.gameobject_manager.spawn_gameobject()
    assert world.gameobject_manager.has_gameobject(gameobject) is True


def test_get_gameobjects():
    world = World()
    g1 = world.gameobject_manager.spawn_gameobject()
    g2 = world.gameobject_manager.spawn_gameobject()
    g3 = world.gameobject_manager.spawn_gameobject()
    assert world.gameobject_manager.get_gameobjects() == [g1, g2, g3]


def test_delete_gameobject():
    world = World()

    g1 = world.gameobject_manager.spawn_gameobject([ComponentA()])

    # Make sure that the game objects exists
    assert world.gameobject_manager.has_gameobject(g1) is True

    world.gameobject_manager.destroy_gameobject(g1)

    # the GameObject should still exist and be removed
    # at the start of the next step
    assert world.gameobject_manager.has_gameobject(g1) is True

    world.step()

    # Now the gameobject should be deleted
    assert world.gameobject_manager.has_gameobject(g1) is False

    # Ensure that GameObjects that were always empty
    # are properly removed
    g2 = world.gameobject_manager.spawn_gameobject()
    assert world.gameobject_manager.has_gameobject(g2) is True
    world.gameobject_manager.destroy_gameobject(g2)
    world.step()
    assert world.gameobject_manager.has_gameobject(g2) is False

    # Ensure that GameObjects that are empty, but
    # once held components are properly removed
    g3 = world.gameobject_manager.spawn_gameobject([ComponentA()])
    assert g3.has_component(ComponentA) is True
    g3.remove_component(ComponentA)
    assert (
        g3.has_component(ComponentA) is False
    )  # This removes the component immediately
    assert world.gameobject_manager.has_gameobject(g3) is True
    world.step()
    assert g3.has_component(ComponentA) is False
    # When you remove the last component from an entity,
    # it technically does not exist within esper anymore
    assert world._ecs.entity_exists(g3) is False  # type: ignore
    g3.destroy()
    world.step()
    assert world.gameobject_manager.has_gameobject(g3) is False


#########################################
# TEST WORLD COMPONENT-RELATED METHODS
#########################################


def test_world_get_component():
    world = World()
    world.gameobject_manager.spawn_gameobject([ComponentA()])
    world.gameobject_manager.spawn_gameobject([ComponentB()])
    world.gameobject_manager.spawn_gameobject([ComponentA(), ComponentB()])

    with_a = world.get_component(ComponentA)

    assert list(zip(*with_a))[0] == (1, 3)

    with_b = world.get_component(ComponentB)

    assert list(zip(*with_b))[0] == (2, 3)


def test_world_get_components():
    world = World()
    world.gameobject_manager.spawn_gameobject([ComponentA()])
    world.gameobject_manager.spawn_gameobject([ComponentB()])
    world.gameobject_manager.spawn_gameobject([ComponentA(), ComponentB()])

    with_a = world.get_components((ComponentA,))

    assert list(zip(*with_a))[0] == (1, 3)

    with_b = world.get_components((ComponentB,))

    assert list(zip(*with_b))[0] == (2, 3)


#########################################
# TEST WORLD SYSTEM-RELATED METHODS
#########################################


def test_world_add_get_system():
    world = World()

    assert world.system_manager.get_system(SalarySystem) is None
    world.system_manager.add_system(SalarySystem())
    assert world.system_manager.get_system(SalarySystem) is not None


def test_world_remove_system():
    world = World()

    assert world.system_manager.get_system(SalarySystem) is None
    world.system_manager.add_system(SalarySystem())
    assert world.system_manager.get_system(SalarySystem) is not None
    world.system_manager.remove_system(SalarySystem)
    assert world.system_manager.get_system(SalarySystem) is None


def test_world_step():
    world = World()
    world.system_manager.add_system(SalarySystem())

    adrian = world.gameobject_manager.spawn_gameobject(
        [Actor("Adrian"), Money(0), Job("Teacher", 24_000)]
    )

    assert adrian.get_component(Money).amount == 0

    world.step()

    assert adrian.get_component(Money).amount == 24_000

    world.step()

    assert adrian.get_component(Money).amount == 48_000


#########################################
# TEST WORLD RESOURCE-RELATED METHODS
#########################################


def test_get_all_resources():
    world = World()

    fake_resource = FakeResource()
    another_fake_resource = AnotherFakeResource

    world.resource_manager.add_resource(fake_resource)
    world.resource_manager.add_resource(another_fake_resource)

    assert world.resource_manager.get_all_resources() == [
        fake_resource,
        another_fake_resource,
    ]


def test_has_resource():
    world = World()
    assert world.resource_manager.has_resource(FakeResource) is False
    world.resource_manager.add_resource(FakeResource())
    assert world.resource_manager.has_resource(FakeResource) is True


def test_get_resource():
    world = World()
    fake_resource = FakeResource()
    assert world.resource_manager.has_resource(FakeResource) is False
    world.resource_manager.add_resource(fake_resource)
    assert world.resource_manager.get_resource(FakeResource) == fake_resource


def test_get_resource_raises_exception():
    """
    Test that the .get_resource(...) method throws
    a ResourceNotFoundError when attempting to get
    a resource that does not exist in the world instance.
    """
    world = World()
    with pytest.raises(ResourceNotFoundError):
        assert world.resource_manager.get_resource(FakeResource)


def test_remove_resource():
    world = World()
    world.resource_manager.add_resource(FakeResource())
    assert world.resource_manager.has_resource(FakeResource) is True
    world.resource_manager.remove_resource(FakeResource)
    assert world.resource_manager.has_resource(FakeResource) is False


def test_remove_resource_raises_exception():
    """
    Test that .remove_resource(...) method throws a
    ResourceNotFoundError when attempting to remove a
    resource that does not exist in the World instance.
    """
    world = World()
    with pytest.raises(ResourceNotFoundError):
        world.resource_manager.remove_resource(FakeResource)


def test_try_resource():
    world = World()

    assert world.resource_manager.try_resource(FakeResource) is None

    world.resource_manager.add_resource(FakeResource())

    assert world.resource_manager.try_resource(FakeResource) is not None


def test_add_resource():
    world = World()
    fake_resource = FakeResource()
    assert world.resource_manager.has_resource(FakeResource) is False
    world.resource_manager.add_resource(fake_resource)
    assert world.resource_manager.has_resource(FakeResource) is True


#########################################
# TEST GAMEOBJECT METHODS
#########################################


def test_gameobject_get_components():
    world = World()

    actor_component = Actor("Adrian")
    money_component = Money(100)

    adrian = world.gameobject_manager.spawn_gameobject(
        [actor_component, money_component]
    )

    components = adrian.get_components()

    assert actor_component in components
    assert money_component in components


def test_gameobject_get_component_types():
    world = World()

    adrian = world.gameobject_manager.spawn_gameobject([Actor("Adrian"), Money(100)])

    component_types = set(adrian.get_component_types())

    assert component_types == {Actor, Money}


def test_gameobject_add_component():
    world = World()
    g1 = world.gameobject_manager.spawn_gameobject()
    assert g1.has_component(ComponentA) is False
    g1.add_component(ComponentA())
    assert g1.has_component(ComponentA) is True


def test_gameobject_get_component():
    world = World()
    a_component = ComponentA()
    g1 = world.gameobject_manager.spawn_gameobject([a_component])
    assert g1.get_component(ComponentA) == a_component


def test_gameobject_get_component_raises_exception():
    with pytest.raises(ComponentNotFoundError):
        world = World()
        g1 = world.gameobject_manager.spawn_gameobject()
        g1.get_component(ComponentA)
        g1.get_component(ComponentB)


def test_gameobject_remove_component():
    world = World()
    g1 = world.gameobject_manager.spawn_gameobject([ComponentA(), ComponentB()])
    assert g1.has_component(ComponentA) is True
    g1.remove_component(ComponentA)
    world.step()
    assert g1.has_component(ComponentA) is False


def test_gameobject_try_component():
    world = World()
    g1 = world.gameobject_manager.spawn_gameobject()
    assert g1.try_component(ComponentA) is None
    g1.add_component(ComponentA())
    assert g1.try_component(ComponentA) is not None


def test_gameobject_add_child():
    world = World()
    g1 = world.gameobject_manager.spawn_gameobject([ComponentA()])
    g2 = world.gameobject_manager.spawn_gameobject([ComponentB()])
    g1.add_child(g2)

    assert (g2 in g1.children) is True
    assert (g2.parent == g1) is True

    g3 = world.gameobject_manager.spawn_gameobject([ComponentA()])

    g3.add_child(g2)

    assert (g2 not in g1.children) is True
    assert (g2.parent != g1) is True
    assert (g2.parent == g3) is True
    assert (g2 in g3.children) is True


def test_gameobject_remove_child():
    world = World()
    g1 = world.gameobject_manager.spawn_gameobject([ComponentA()])
    g2 = world.gameobject_manager.spawn_gameobject([ComponentB()])
    g3 = world.gameobject_manager.spawn_gameobject([ComponentB()])

    g1.add_child(g2)
    g1.add_child(g3)

    assert (g2 in g1.children) is True
    assert (g3 in g1.children) is True
    assert (g1 == g3.parent) is True

    g1.remove_child(g3)

    assert (g3 in g1.children) is False
    assert g3.parent is None


def test_gameobject_remove_gameobject_with_children():
    world = World()

    g1 = world.gameobject_manager.spawn_gameobject([ComponentA()])
    g2 = world.gameobject_manager.spawn_gameobject([ComponentB()])
    g3 = world.gameobject_manager.spawn_gameobject([ComponentB()])
    g4 = world.gameobject_manager.spawn_gameobject([ComponentB()])
    g5 = world.gameobject_manager.spawn_gameobject([ComponentB()])

    g1.add_child(g2)
    g2.add_child(g3)
    g3.add_child(g4)
    g3.add_child(g5)

    # Removing g3 should remove g4 and g5
    assert world.gameobject_manager.has_gameobject(g3) is True
    assert world.gameobject_manager.has_gameobject(g4) is True
    assert world.gameobject_manager.has_gameobject(g5) is True

    world.gameobject_manager.destroy_gameobject(g3)
    world.step()

    # Removing g3 should remove g4 and g5
    assert world.gameobject_manager.has_gameobject(g3) is False
    assert world.gameobject_manager.has_gameobject(g4) is False
    assert world.gameobject_manager.has_gameobject(g5) is False

    world.gameobject_manager.destroy_gameobject(g2)
    world.step()

    assert world.gameobject_manager.has_gameobject(g2) is False
