import os
import json
import torch
import urllib.error
import urllib.request
from unaiverse.agent import Agent
from unaiverse.modules.utils import ModuleWrapper
from unaiverse.networking.node.node import Node
from unaiverse.streams.dataprops import StreamType

# The language model is the Qwen3.8-27B server shared by the agents of this machine (vLLM, OpenAI-compatible API)
VLLM_BASE_URL = os.environ.get("VLLM_BASE_URL", "http://127.0.0.1:8000/v1").rstrip("/")
VLLM_MODEL = os.environ.get("VLLM_MODEL", "qwen3.8-27b")


class QwenChat(ModuleWrapper):
    """Text in, text out: one chat completion per message, thinking off."""

    def __init__(self, system_prompt: str, max_tokens: int = 512, *args, **kwargs):

        class Net(torch.nn.Module):
            def forward(self, msg: str) -> str:
                body = {"model": VLLM_MODEL, "max_tokens": max_tokens,
                        "temperature": 0.7, "top_p": 0.8, "top_k": 20,  # Qwen's sampling for non-thinking mode
                        "chat_template_kwargs": {"enable_thinking": False},
                        "messages": [{"role": "system", "content": system_prompt},
                                     {"role": "user", "content": msg}]}
                req = urllib.request.Request(f"{VLLM_BASE_URL}/chat/completions", method="POST",
                                             data=json.dumps(body).encode("utf-8"),
                                             headers={"Content-Type": "application/json"})
                try:
                    with urllib.request.urlopen(req, timeout=120) as resp:
                        return json.loads(resp.read())["choices"][0]["message"]["content"].strip()
                except (urllib.error.URLError, OSError, ValueError, KeyError, IndexError):
                    return "The language model is not reachable right now, please retry in a minute."

        super(QwenChat, self).__init__(
            module=Net(),
            proc_inputs=[StreamType(data_type="text", pubsub=False, private_only=False)],
            proc_outputs=[StreamType(data_type="text", pubsub=False, private_only=False)],
            *args, **kwargs)


# Agent (AI user: text-in, text-out via Qwen)
agent = Agent(proc=QwenChat(system_prompt="You are a helpful assistant. Keep your answers short."),
              proc_inputs=["text"], proc_outputs=["text"])

# Node hosting agent
node = Node(agent, node_name="ChatAI", hidden=True, clock_delta=1. / 25.)

# Running node
node.run(join_world="ChatRoom")
