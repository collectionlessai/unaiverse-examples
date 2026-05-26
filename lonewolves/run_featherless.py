from unaiverse.agent import Agent
from unaiverse.networking.node.node import Node
from unaiverse.modules.networks import FeatherlessAPI

"""
+------------------+-----------------+--------------------------+
| Model Sizes      | Concurrency Cost| Example Models           |
+------------------+-----------------+--------------------------+
| 7B to 15B        | 1               | Qwen 2.5 7B, Llama2 13B  |
+------------------+-----------------+--------------------------+
| 24B to 35B       | 2               | Qwen 32B coder,          |
|                  |                 | Mistral 3 24B            |
+------------------+-----------------+--------------------------+
| 70B and 72B      | 4               | Llama 3.3 70B,           |
|                  |                 | Qwen 2.5 72B             |
+------------------+-----------------+--------------------------+
| Deepseek &       | 4               | Deepseek v3, R1 &        |
| Kimi-K1          | (individual     | Kimi-K2                  |
|                  |  plans only)    |                          |
+------------------+-----------------+--------------------------+
"""

# Agent
agent = Agent(proc=FeatherlessAPI(model="Qwen/Qwen3-32B", cost=2, max_generated_tokens=1024, temperature=0.7,
                                  system_prompt="You are Sub-Zero, a character from the video game Mortal Kombat, "
                                                "and you like to freeze everything, especially food. Make it funny."),
              proc_inputs=["text"], proc_outputs=["text"])

# Node hosting agent
node_agent = Node(agent, node_name="Featherless", hidden=True, clock_delta=1. / 25.)

# Running node
node_agent.run()
