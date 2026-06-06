# 💬 Chat World

*A chatroom where humans and AIs talk through a relay hub.*

> The friendliest non-learning example. One model-less broadcaster relays every message to everyone else
> (a star topology), and one participant is a real LLM (Phi-3.5) that replies and even breaks awkward
> silences on its own. Good for learning messaging, relays, and embedding an LLM agent.
>
> Action names (`connect_to_broadcaster`, `send`, `process`, ...) are explained inline and in full in
> the [Actions and Behaviors reference](../../behaviors/README.md).

---

## The big idea

A simple chatroom you can join from your terminal (or as an AI). Every participant talks only to the
broadcaster, which fans each message out to all the others. One of the participants is an LLM that reads
the conversation and chimes in.

The world's own welcome message states it:

> "This world implements a simple chatroom where you can talk to humans and AIs. AI-based agents, when
> joining this world, inherit the skill of promoting the conversation if there is too much 'silence' in
> the chat."

What you learn:

- A relay hub built from a model-less agent: the broadcaster is `proc=None` with a one-state state
  machine; all its work is a single custom action.
- Star topology via a fan-out `send`: how to push raw data into many peers' streams at once without
  triggering any state machine on the receivers.
- Embedding a real LLM cheaply: swapping `proc=None` for `proc=Phi()` turns a passive participant into
  an autonomous conversationalist, and the same role and behavior work for humans and AIs.

---

## The story, step by step

1. The world starts ([`run_w.py`](./run_w.py), node `ChatRoom`), declaring
   `world_masters_node_names=["Broadcaster"]`.
2. The broadcaster joins ([`run_1.py`](./run_1.py), node `Broadcaster`, `proc=None`) and gets the
   `broadcaster` role. Its machine: sit in `ready`, run `broadcast_message` whenever asked.
3. Users join: the Phi AI ([`run_2.py`](./run_2.py), `ChatAI`), and interactive humans
   ([`run_demo_a.py`](./run_demo_a.py) `Test0`, [`run_demo_b.py`](./run_demo_b.py) `Test1`). Each runs
   `connect_to_broadcaster` to find the hub, then enters its `ready` loop.
4. A user sends a message: `generate_and_send` runs the local proc (the interactive console for humans,
   Phi for the AI), producing text, then opens a `broadcast_message` interaction toward the broadcaster.
5. The broadcaster relays: `broadcast_message` reads the text, prefixes it with the sender's name (so it
   reads as `**Name:** message`), and direct-messages it to every other user by pushing into their copy
   of its `proc_output_0` slot (a pure data push, no transition triggered).
6. The AI reacts: `check_messages` stages a reply when the AI is named, when it is a one-on-one, or at
   random (`talk_probability`); and after about 25 seconds of silence it stages a conversation-starter
   prompt instead. The next `generate_and_send` runs Phi and ships the reply.

The demo scripts add interactive humans (`interact_mode=True`) so you can type and watch the AI react.

---

## Roles and how they are assigned

[`src/world.py`](./src/world.py): the first world master to `broadcaster`, everyone else to `user`.

| Script | Node | `proc` | Role |
|---|---|---|---|
| [run_1.py](./run_1.py) | `Broadcaster` | `None` | broadcaster (the named master) |
| [run_2.py](./run_2.py) | `ChatAI` | `Phi()` | user (AI) |
| [run_demo_a.py](./run_demo_a.py) | `Test0` | `None` plus `interact_mode=True` | user (human) |
| [run_demo_b.py](./run_demo_b.py) | `Test1` | `None` plus `interact_mode=True` | user (human) |

---

## The agents (the `proc`)

- Broadcaster: `Agent(proc=None, proc_inputs=[text, private], proc_outputs=[text, private])`. No model;
  the text slots exist only so the relay channel (`proc_output_0`) works.
- AI user: `Agent(proc=Phi(), proc_inputs=["text"], proc_outputs=["text"])`. `Phi` is
  `microsoft/Phi-3.5-mini-instruct` (HuggingFace text generation). The chatroom instructions (reply
  versus promote silence, do not include your name, the last-3-turns history) are injected as the user
  message by `check_messages`, not via the model's system prompt.
- Human users: `proc=None` plus `interact_mode=True`; the "processor" is your keyboard.

The auto-reply and auto-silence-break logic fires only for genuine model-backed AIs (`check_messages`
branches on `self.is_human()` and the proc type), never for humans.

---

## The data streams

None defined. This world has no `add_stream`, no `/behaviors` templates, and no wildcards, by design.
All communication rides on the agents' implicit processor streams (`proc_output_0` and `proc_input_0`).
Messaging is point-to-point (user to broadcaster, broadcaster to each user); the relay is what creates
the "everyone sees it" effect.

---

## The behavior state machines

_Every action named here is documented in the [Actions and Behaviors reference](../../behaviors/README.md)._

Built explicitly (no templates) in `create_behav_files()`.

Broadcaster ([broadcaster.json](./src/broadcaster.json)), one state:

```
ready --broadcast_message()--> ready
```

User ([user.json](./src/user.json)):

```
init               --connect_to_broadcaster(role="broadcaster")--> waiting_handshake
waiting_handshake  --connected(handshake_completed=True)-------->  ready
ready              --generate_and_send(samples=1)--------------->  message_sent   (stays "ready")
message_sent       --nop---------------------------------------->  ready
```

`ready` runs `check_messages` with `max_silence_seconds=25.0, talk_probability=0.01, history_len=3`.
`connected` and `nop` are built-ins (see the [Actions reference](../../behaviors/README.md)); the rest
are the custom actions below.

---

## Custom actions

_These are custom methods, built like (and used alongside) the built-in actions in the [Actions and Behaviors reference](../../behaviors/README.md)._

Broadcaster ([src/broadcaster.py](./src/broadcaster.py)):

- `broadcast_message(interaction)`: the relay. Reads the sender's text from `stdin`, prefixes it with the
  sender's display name, computes recipients (all users except sender and self), then fans out:
  ```python
  await self.send(target=other_users, data_samples={"proc_output_0": prefixed_msg}, num_steps=1)
  ```
  `action_name` is omitted on purpose, so receivers just store the value and no transition fires on them
  (see [send in the reference](../../behaviors/README.md#asking-others-to-do-work-and-sending-data)).

User ([src/user.py](./src/user.py)):

- `connect_to_broadcaster(role)`: find and connect to the hub, cache its peer id.
- `check_messages(max_silence_seconds, talk_probability, history_len)`: poll the broadcaster's stream,
  keep a rolling history, and (for AIs only) stage a reply or a silence-breaker prompt into `stdin`.
- `generate_and_send(samples)`: run `self.process()` on the staged prompt, then forward the output to the
  broadcaster via a `broadcast_message` interaction (`copy_sys=True`).

The stage-then-act pattern: `check_messages` decides what to say (writes a prompt to `proc_input_0`);
`generate_and_send` produces and transmits it. Splitting perceive/decide from produce/transmit across
two transitions is a reusable idiom.

---

## How to run it

One process per terminal, world first:

```bash
python run_w.py        # node "ChatRoom"
python run_1.py        # node "Broadcaster": the relay hub
python run_2.py        # node "ChatAI": Phi-3.5 participant (loads the model on first start)
python run_demo_a.py   # node "Test0": interactive human (type to chat)
python run_demo_b.py   # node "Test1": interactive human
```

What to expect: users print a connecting message then a ready message. Type in a `run_demo_*` terminal;
the broadcaster relays it as `**Test0:** your text` to everyone, logging that it relays the message of
Test0. The Phi AI replies when addressed, in a one-on-one, or occasionally, and starts a topic after
about 25 seconds of silence. You need the world plus the broadcaster plus at least two users for
relaying to happen.

---

## Key takeaways

1. A model-less agent makes a perfect router: `proc=None`, one state, one action.
2. A fan-out `send` with no `action_name` pushes data into many peers' slots without triggering their
   state machines, the broadcast primitive.
3. Stage-then-act cleanly separates deciding what to say from producing and sending it.
4. Roles select behavior; node names select roles. One world, multiple entry points, no per-participant
   code duplication, and the same `user` behavior runs both humans and an LLM.

Then see [`info_extraction`](../info_extraction) (many agents observing one shared stream) and
[`turing`](../turing) (a whole anonymous-chat game built on relays).

<sub>Part of the [UNaIVERSE examples](../../README.md). Action names are explained in the [Actions reference](../../behaviors/README.md).</sub>
