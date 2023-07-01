#!/usr/bin/env python3
"""
Using Authored Characters Sample
--------------------------------

This samples shows how users may inject user-specified characters into the simulation.
Normally characters are spawned into the settlement based on the spawn table.
"""
import time
from typing import Any, Dict

from neighborly import ISystem, Neighborly, NeighborlyConfig, SimDateTime
from neighborly.command import SpawnSettlement, SpawnCharacter, SpawnResidence
from neighborly.components.character import GameCharacter
from neighborly.core.ecs import World, TagComponent, GameObjectPrefab
from neighborly.core.relationship import (
    Friendship,
    InteractionScore,
    RelationshipManager,
    Romance,
)
from neighborly.core.status import StatusComponent, StatusManager
from neighborly.data_collection import DataCollector
from neighborly.decorators import component, system
from neighborly.exporter import export_to_json
from neighborly.utils.common import (
    add_character_to_settlement,
    add_residence_to_settlement,
    set_residence,
)

sim = Neighborly(
    NeighborlyConfig.parse_obj(
        {
            "time_increment": "1mo",
            "relationship_schema": {
                "components": {
                    "Friendship": {
                        "min_value": -100,
                        "max_value": 100,
                    },
                    "Romance": {
                        "min_value": -100,
                        "max_value": 100,
                    },
                    "InteractionScore": {
                        "min_value": -5,
                        "max_value": 5,
                    },
                }
            },
            "plugins": [
                "neighborly.plugins.defaults.all",
                "neighborly.plugins.talktown.spawn_tables",
                "neighborly.plugins.talktown",
            ],
        }
    )
)


@component(sim.world)
class Robot(TagComponent):
    """Tags a character as a Robot"""

    pass


@component(sim.world)
class OwesDebt(StatusComponent):
    """Marks a character as owing money to another character"""

    def __init__(self, amount: int) -> None:
        super().__init__()
        self.amount: int = amount

    def to_dict(self) -> Dict[str, Any]:
        return {**super().to_dict(), "amount": self.amount}


@system(sim.world)
class RelationshipReporter(ISystem):
    def on_create(self, world: World) -> None:
        world.resource_manager.get_resource(DataCollector).create_new_table(
            "relationships",
            (
                "timestamp",
                "owner",
                "target",
                "friendship",
                "romance",
                "interaction_score",
                "statuses",
            ),
        )

    def on_update(self, world: World) -> None:
        timestamp = world.resource_manager.get_resource(SimDateTime).to_iso_str()
        data_collector = world.resource_manager.get_resource(DataCollector)
        for guid, (game_character, relationship_manager) in world.get_components(
            (GameCharacter, RelationshipManager)
        ):
            if (
                game_character.first_name == "Delores"
                and game_character.last_name == "Abernathy"
            ):
                for target, relationship in relationship_manager.outgoing.items():
                    data_collector.add_table_row(
                        "relationships",
                        {
                            "timestamp": timestamp,
                            "owner": guid,
                            "target": target.uid,
                            "friendship": relationship.get_component(
                                Friendship
                            ).get_value(),
                            "romance": relationship.get_component(Romance).get_value(),
                            "interaction_score": relationship.get_component(
                                InteractionScore
                            ).get_value(),
                            "statuses": str(relationship.get_component(StatusManager)),
                        },
                    )


EXPORT_SIM = False
YEARS_TO_SIMULATE = 50


def main():
    """Main entry point for this module"""

    west_world = SpawnSettlement(name="West World").execute(sim.world).get_result()

    sim.world.gameobject_manager.add_prefab(
        GameObjectPrefab(
            name="westworld::host",
            extends=["character::default::female"],
            components={"Robot": {}},
        )
    )

    dolores = (
        SpawnCharacter(
            "westworld::host",
            first_name="Dolores",
            last_name="Abernathy",
            age=32,
        )
        .execute(sim.world)
        .get_result()
    )

    add_character_to_settlement(dolores, west_world)

    house = SpawnResidence("residence::default::house").execute(sim.world).get_result()

    add_residence_to_settlement(house, west_world)

    set_residence(dolores, house)

    st = time.time()
    sim.run_for(YEARS_TO_SIMULATE)
    elapsed_time = time.time() - st

    print(f"World Date: {str(sim.world.resource_manager.get_resource(SimDateTime))}")
    print("Execution time: ", elapsed_time, "seconds")

    if EXPORT_SIM:
        with open(f"neighborly_{sim.config.seed}.json", "w") as f:
            f.write(export_to_json(sim))


if __name__ == "__main__":
    main()
