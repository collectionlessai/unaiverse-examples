import os
from src.world import WWorld
from unaiverse.networking.node.node import Node

if __name__ == "__main__":

    # Setting up debug-like env variables for local testing
    os.environ["NODE_IGNORE_ALIVE"] = "1"
    os.environ["NODE_IS_PUBLIC"] = "1"
    os.environ["NODE_IS_ISOLATED"] = "1"

    # World
    world = WWorld()

    # Node hosting world
    node = Node(node_name="CoLLAsTutorial_", hosted=world, hidden=True, clock_delta=1./10.,
                world_masters_node_names=["CoLLAsTeacher_"])

    # Running node
    node.run()
