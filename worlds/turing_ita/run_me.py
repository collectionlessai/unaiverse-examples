"""
Our test participant for the Turing Hotel Italy world.

The "best-suited showcase couple", assembled from what the framework ships:
  * processor     = Phi                  (local LLM; the lone-wolf showcase model)
  * policy filter = PolicyHumanLikeDelay (human-like turn timing: log-normal +
                    momentum + distraction — closer to the Turing game's intent
                    than the basic PolicyFilterDelayAction the run_* examples use)

The whole agent is these two parts plus three lines of wiring. For a non-programmer
the only knobs that are genuinely plug-and-play are the two policy-filter numbers.

KNOWN FRICTION (see reports/2026-08-03_turing_ita_test_plan.md, findings #6-#8):
the processor's persona/system prompt is hardcoded inside Phi ("You are a helpful
assistant", in English), so this agent cannot be told to "act like a human Italian
guest" without subclassing/editing framework source.
"""
from unaiverse.agent import Agent
from unaiverse.modules.networks import Phi
from unaiverse.utils.misc import PolicyHumanLikeDelay
from unaiverse.networking.node.node import Node

# ---- The two parts a participant builds -------------------------------------
processor = Phi()                        # WHAT it says (device auto/PROC_DEVICE)

policy_filter = PolicyHumanLikeDelay(    # WHEN it says it (tweak these two numbers)
    {"process"},
    median_delay=5.0,                    # typical seconds before replying
    variability=0.6,                     # 0 = metronome, higher = more human jitter
)

agent = Agent(proc=processor, proc_inputs=["text"], proc_outputs=["text"],
              policy_filter=policy_filter)

# Node hosting the agent as a guest (this name is NOT in managers.txt -> "guest")
node = Node(node_name="EdoTestGuest-Phi", hosted=agent, hidden=True, clock_delta=1. / 10.)

node.run(join_world="TuringHotelItaly")
