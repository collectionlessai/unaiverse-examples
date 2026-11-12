from unaiverse.agent import Agent
from unaiverse.modules.utils import MultiIdentity
from unaiverse.networking.node.node import Node


# Model-free lone wolf for the Session smoke test: it answers a text with the same text.
agent = Agent(proc=MultiIdentity(), proc_inputs=["text"], proc_outputs=["text"])
node = Node(agent, node_name="SessionSmokeEcho", hidden=True, clock_delta=1./25.)
node.run()
