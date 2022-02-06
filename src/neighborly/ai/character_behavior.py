"""Special components and behavior tree nodes for implementing character behaviors"""

from typing import Protocol, Dict

import esper

from neighborly.ai import behavior_utils
from neighborly.ai.behavior_tree import BehaviorTree, SelectorBTNode, NodeState, Blackboard, \
    DecoratorBTNode


class CharacterBehavior(BehaviorTree):
    """Wraps a behavior tree and manages a single behavior that a character can perform"""


class IBehaviorSelectorNode(Protocol):
    """Abstract base class for nodes that select which behavior character will perform"""

    def choose_behavior(self) -> CharacterBehavior:
        """Choose a behavior to perform"""
        raise NotImplementedError()

    def get_available_behaviors(self) -> Dict[str, CharacterBehavior]:
        """Get all behaviors whose preconditions pass"""
        raise NotImplementedError()

    def get_all_behaviors(self) -> Dict[str, CharacterBehavior]:
        """Get all behaviors available to the selector"""
        raise NotImplementedError()


class PriorityNode(DecoratorBTNode):
    """Wraps a single subtree with a priority value"""

    __slots__ = "_priority"

    def __init__(self, priority: int = 0) -> None:
        super().__init__()
        self._priority = priority

    def get_priority(self) -> int:
        """Returns the priority of this tree"""
        return self._priority

    def evaluate(self, blackboard: Blackboard) -> NodeState:
        """Runs the underlying behavior tree"""
        self._state = self._children[0].evaluate(blackboard)
        return self._state


class PrioritySelectorNode(SelectorBTNode):
    """Evaluates subtrees in priority order and stops at the first successful evaluation"""

    def add_child(self, node: PriorityNode) -> None:
        """Add a child node to this node"""
        self._children.append(node)
        self._children.sort(key=lambda n: n.get_priority())


class RandomSelectorNode(SelectorBTNode):

    def evaluate(self, blackboard: Blackboard) -> NodeState:
        world: esper.World = blackboard.get_value("world")
        engine = behavior_utils.get_engine(world)
        engine.get_rng().shuffle(self._children)
        return super().evaluate(blackboard)
