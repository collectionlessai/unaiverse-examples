import os
from src.world import WWorld
from unaiverse.networking.node.node import Node

if __name__ == "__main__":

    # Setting up debug-like env variables for local testing
    os.environ["NODE_IGNORE_ALIVE"] = "1"
    os.environ["NODE_IS_PUBLIC"] = "1"
    os.environ["NODE_IS_ISOLATED"] = "1"

    # Clearing spurious data from previous runs (images added by the teacher's augmentation are numbered above 60)
    for i in range(1, 4):
        folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "lectures", str(i))
        for file_name in os.listdir(folder):
            num = file_name.split("_")[0]
            if num.isdigit() and int(num) > 60:
                os.remove(os.path.join(folder, file_name))

    # World
    world = WWorld()

    # Node hosting world
    node = Node(node_name="CoLLAsTutorial_", hosted=world, hidden=True, clock_delta=1./10.,
                world_masters_node_names=["CoLLAsTeacher_"])

    # Running node
    node.run()
