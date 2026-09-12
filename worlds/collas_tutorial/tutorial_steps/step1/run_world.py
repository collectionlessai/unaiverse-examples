from src.world import WWorld
from unaiverse.custom import Custom
from unaiverse.networking.node.node import Node

if __name__ == "__main__":

    # Setting up debug-like env variables for local testing
    Custom.SKIP_WAS_ALIVE_CHECK = True
    Custom.ENV_IS_ISOLATED = True
    Custom.ENV_IS_PUBLIC = True

    # World
    world = WWorld()

    # Node hosting world
    node = Node(node_name="CoLLAsTutorial_", hosted=world, hidden=True, clock_delta=1./10.,
                world_masters_node_names=["CoLLAsTeacher_"])

    # Running node
    node.run()
