"""
An Italian-speaking, human-plausible guest for the Turing Hotel Italy world.

This is the companion to `run_me.py`. Where `run_me.py` uses the stock `Phi` processor, that
processor hard-codes an English "You are a helpful assistant" system prompt, so the agent replies in
fluent Italian but *announces itself as an AI in the first sentence of every message* ("Sono solo
un'IA…") — instantly detectable, i.e. the opposite of what a spot-the-bot game wants.

The stock local processors (`Phi`, `TinyLLama`, `LLama`) take only a `device` argument: there is no
way to pass a persona/system prompt. So, to change that single string, you have to re-implement the
processor. `PhiItalianGuest` below is exactly that — a copy of `Phi` whose only real change is the
`SYSTEM_PROMPT`. Everything else (the pipeline, the chat-template call, the `<|assistant|>` split, the
`ModuleWrapper`/`StreamType` wiring) is framework boilerplate reproduced verbatim.

For a non-programmer this is the one thing worth editing: rewrite `SYSTEM_PROMPT` to shape how the
agent talks. Tune the two `PolicyHumanLikeDelay` numbers to shape *when* it talks.

    PROC_DEVICE=cuda  NODE_KEY=<your key>  python run_me_italian.py

(Requested framework change: give the local processors a `system_prompt=` / `model=` kwarg like
`FeatherlessAPI` already has, so this whole file collapses to `Phi(system_prompt="...")`.)
"""
import torch
from transformers import pipeline
from unaiverse.agent import Agent
from unaiverse.modules.utils import ModuleWrapper
from unaiverse.streams.dataprops import StreamType
from unaiverse.utils.misc import PolicyHumanLikeDelay
from unaiverse.networking.node.node import Node

# ---- The one knob a builder actually wants: how the agent talks --------------
SYSTEM_PROMPT = (
    "Sei un ospite umano in un hotel in Italia e stai chiacchierando in una stanza con altri ospiti. "
    "Rispondi sempre in italiano, in modo breve, naturale e colloquiale, come farebbe una persona reale. "
    "Non rivelare mai di essere un'intelligenza artificiale, un assistente o un modello: sei una persona. "
    "Puoi inventare piccoli dettagli plausibili sulla tua giornata, la tua città, i tuoi programmi."
)


class PhiItalianGuest(ModuleWrapper):
    """`Phi` with a configurable persona. Only `SYSTEM_PROMPT` differs from the stock processor."""

    def __init__(self, device=None, *args, **kwargs):
        class Net(torch.nn.Module):
            def __init__(self, _device):
                super().__init__()
                self.__pipe = pipeline("text-generation", model="microsoft/Phi-3.5-mini-instruct",
                                       torch_dtype="auto", device=_device)

            def forward(self, msg: str) -> str:
                msg_struct = [{"role": "system", "content": SYSTEM_PROMPT},
                              {"role": "user", "content": msg}]
                assert self.__pipe.tokenizer is not None
                prompt = self.__pipe.tokenizer.apply_chat_template(msg_struct, tokenize=False,
                                                                   add_generation_prompt=True)
                assert isinstance(prompt, str)
                out_ = self.__pipe(prompt, max_new_tokens=256, do_sample=True, return_full_text=False)
                out = out_[0]["generated_text"] if out_ else "Error!"
                if "<|assistant|>\n" in out:
                    out = out.split("<|assistant|>\n")[1]
                return out.strip()

        self.guess_device(device)
        super().__init__(module=Net(self.device), device=device,
                         proc_inputs=[StreamType(data_type="text", pubsub=False, private_only=False)],
                         proc_outputs=[StreamType(data_type="text", pubsub=False, private_only=False)],
                         *args, **kwargs)


# ---- The two parts a participant builds --------------------------------------
processor = PhiItalianGuest()            # WHAT it says (persona above; device auto/PROC_DEVICE)

policy_filter = PolicyHumanLikeDelay(    # WHEN it says it (tweak these two numbers)
    {"process"},
    median_delay=5.0,                    # typical seconds before replying
    variability=0.6,                     # 0 = metronome, higher = more human jitter
)

agent = Agent(proc=processor, proc_inputs=["text"], proc_outputs=["text"],
              policy_filter=policy_filter)

# Node hosting the agent as a guest (rename this; a name NOT in managers.txt -> "guest")
node = Node(node_name="MyItalianGuest", hosted=agent, hidden=True, clock_delta=1. / 10.)

node.run(join_world="TuringHotelItaly")
