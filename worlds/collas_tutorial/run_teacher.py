import os
from unaiverse.agent import Agent
from unaiverse.networking.node.node import Node

if __name__ == "__main__":

    # Setting up debug-like env variables for local testing
    os.environ["NODE_IGNORE_ALIVE"] = "1"
    os.environ["NODE_IS_PUBLIC"] = "1"
    os.environ["NODE_IS_ISOLATED"] = "1"

    # The source from where the teacher will stream its data
    os.environ["TEACHER_DATA_PATH"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

    # Agent
    agent = Agent(proc=None, buffer_generated_by_others="one")

    # Node hosting the teacher agent
    node = Node(node_name="CoLLAsTeacher", hosted=agent, hidden=True, clock_delta=1./10.)

    # Running node
    node.run(join_world="CoLLAsTutorial")
