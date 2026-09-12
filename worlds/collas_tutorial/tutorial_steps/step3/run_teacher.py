import os
from unaiverse.agent import Agent
from unaiverse.custom import Custom
from unaiverse.networking.node.node import Node

if __name__ == "__main__":

    # Setting up debug-like env variables for local testing
    Custom.SKIP_WAS_ALIVE_CHECK = True
    Custom.ENV_IS_ISOLATED = True
    Custom.ENV_IS_PUBLIC = True

    # The source from where the teacher will stream its data
    os.environ["TEACHER_DATA_PATH"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")

    # Agent
    agent = Agent(proc=None)

    # Node hosting the teacher agent
    node = Node(node_name="CoLLAsTeacher_", hosted=agent, hidden=True, clock_delta=1./10.)

    # Running node
    node.run(join_world="CoLLAsTutorial_")
