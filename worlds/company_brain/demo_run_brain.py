from demo_script_a import SCRIPT, INDEX_FILE, LOG_ON_FINISH
from src.demo import DemoAgent, ScriptedModule
from unaiverse.networking.node.node import Node

agent = DemoAgent(proc=ScriptedModule(
    SCRIPT, INDEX_FILE, agent_name="Company Brain", log_on_finish=LOG_ON_FINISH))

node = Node(agent, node_name="Company Brain", hidden=True, clock_delta=1. / 20.)
node.run(join_world="ACMECorp", role_preference="team_manager")
