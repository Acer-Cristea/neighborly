import esper

from neighborly.core.social_practice import CharacterBehavior
from neighborly.ai.behavior_tree import AbstractBTNode, NodeState, Blackboard
from neighborly.ai import behavior_utils


class DieAction(AbstractBTNode):
    def evaluate(self, blackboard: 'Blackboard') -> 'NodeState':
        world: esper.World = blackboard.get_value('world')
        character_id: int = blackboard.get_value('self')
        character = behavior_utils.get_character(world, character_id)

        behavior_utils.stop_social_practice(world, character_id, "default")

        return NodeState.SUCCESS


_die_behavior = CharacterBehavior(
    name="die",
    preconditions=[lambda world, character_id: behavior_utils.can_die(world, character)]
    behavior_tree=
)
