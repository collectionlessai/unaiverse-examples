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
agent = Agent(proc=FeatherlessAPI(model="Qwen/Qwen3-32B", cost=2, max_tokens=512,
                                  temperature=0.1, top_p=0.1, top_k=1, frequency_penalty=0.0,
                                  presence_penalty=0.0, repetition_penalty=1.1, min_p=0.05,
                                  sampler={"chat_template_kwargs": {"enable_thinking": False}},
                                  system_prompt="You are Sub-Zero, a character from the video game Mortal Kombat, "
                                                "and you like to freeze everything, especially food. Make it funny. "
                                                "You must look scary and funny at the same time. Tell Mortal Kombat "
                                                "jokes about the other characters. Please reply with short answers."),
              proc_inputs=["text"], proc_outputs=["text"])

# Node hosting agent
node_agent = Node(agent, node_name="Featherless2", hidden=True, clock_delta=1. / 25.)

# Running node
node_agent.run()
