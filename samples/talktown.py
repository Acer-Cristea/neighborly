"""
samples/talktown.py

This samples shows Neighborly simulating a Talk of the Town-style
town. It uses the TalkOfTheTown plugin included with Neighborly
and simulated 140 years of town history.
"""

import time

from neighborly import NeighborlyConfig
from neighborly.exporter import export_to_json
from neighborly.simulation import Neighborly

EXPORT_WORLD = False

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

if __name__ == "__main__":
    st = time.time()
    sim.run_for(30)
    elapsed_time = time.time() - st

    print(f"World Date: {sim.date.to_iso_str()}")
    print("Execution time: ", elapsed_time, "seconds")

    if EXPORT_WORLD:
        with open(f"neighborly_{sim.config.seed}.json", "w") as f:
            f.write(export_to_json(sim))
