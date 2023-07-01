from typing import List

from neighborly.components.character import GameCharacter, LifeStage, LifeStageType
from neighborly.core.ecs import Active, GameObject, ISystem, World
from neighborly.core.life_event import EventRole, LifeEvent
from neighborly.core.status import StatusComponent, add_status, remove_status
from neighborly.core.time import SimDateTime
from neighborly.plugins.talktown.business_components import School


class Student(StatusComponent):
    pass


class CollegeGraduate(StatusComponent):
    pass


class EnrolledInSchoolEvent(LifeEvent):
    def __init__(self, world: World, date: SimDateTime, character: GameObject) -> None:
        super().__init__(
            world,
            date,
            [EventRole("Character", character)],
        )


class GraduatedFromSchoolEvent(LifeEvent):
    def __init__(self, world: World, date: SimDateTime, character: GameObject) -> None:
        super().__init__(
            world,
            date,
            [EventRole("Character", character)],
        )


class SchoolSystem(ISystem):
    """Enrolls new students and graduates old students"""

    @staticmethod
    def get_unenrolled_students(world: World) -> List[GameObject]:
        candidates = [
            world.gameobject_manager.get_gameobject(res[0])
            for res in world.get_components((GameCharacter, Active, LifeStage))
        ]

        candidates = [
            c
            for c in candidates
            if c.get_component(LifeStage).life_stage <= LifeStageType.Adolescent
            and not c.has_component(Student)
        ]

        return candidates

    @staticmethod
    def get_adult_students(world: World) -> List[GameObject]:
        candidates = [
            world.gameobject_manager.get_gameobject(res[0])
            for res in world.get_components((GameCharacter, Active, Student, LifeStage))
        ]

        candidates = [
            c
            for c in candidates
            if c.get_component(LifeStage).life_stage >= LifeStageType.YoungAdult
        ]

        return candidates

    def on_update(self, world: World) -> None:
        date = world.resource_manager.get_resource(SimDateTime)

        for _, school in world.get_component(School):
            for character in self.get_unenrolled_students(world):
                school.add_student(character.uid)
                add_status(character, Student())
                event = EnrolledInSchoolEvent(world, date, character)
                world.event_manager.dispatch_event(event)

            # Graduate young adults
            for character in self.get_adult_students(world):
                school.remove_student(character.uid)
                remove_status(character, Student)
                event = GraduatedFromSchoolEvent(world, date, character)
                world.event_manager.dispatch_event(event)
