from demo_script_a import SCRIPT, INDEX_FILE
from src.demo import DemoAgent, ScriptedModule
from unaiverse.networking.node.node import Node

agent = DemoAgent(proc=ScriptedModule(
    SCRIPT, INDEX_FILE, agent_name="AI Expert"))

node = Node(agent, node_name="AI Expert", hidden=True, clock_delta=1. / 20.)
node.run(join_world="ACMECorp", role_preference="expert")
