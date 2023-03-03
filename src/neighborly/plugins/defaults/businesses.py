import os
import pathlib

from neighborly.loaders import load_business_prefab, load_occupation_types
from neighborly.simulation import Neighborly, PluginInfo

_RESOURCES_DIR = pathlib.Path(os.path.abspath(__file__)).parent / "data"

plugin_info: PluginInfo = {
    "name": "default businesses plugin",
    "plugin_id": "default.businesses",
    "version": "0.1.0",
}


def setup(sim: Neighborly):
    load_occupation_types(sim.world, _RESOURCES_DIR / "occupation_types.yaml")

    load_business_prefab(sim.world, _RESOURCES_DIR / "business.default.yaml")
    load_business_prefab(sim.world, _RESOURCES_DIR / "business.default.library.yaml")
    load_business_prefab(sim.world, _RESOURCES_DIR / "business.default.cafe.yaml")
