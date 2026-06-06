# Behaviors and Actions Reference

This folder holds reusable **behavior templates** (the `*.json` files), and this page is the
**reference for the actions** that those templates and the example worlds are built from.

If you are reading a world's README and hit something like `set_pref_streams` or
`compare_eval` and think "what is that?", this is the page that explains it: what each action does,
and **why its parameters are set the way they are**.

---

## The mental model in 90 seconds

A world is a set of **roles** (teacher, student, broadcaster, guest, ...). Each role has a
**behavior**, which is a **state machine**: states connected by transitions. A transition is labeled
with an **action**.

- **An action is just a method that returns `True` or `False`.** `True` means "this action completed,
  take this transition"; `False` means "not done yet, stay where you are and try again next tick".
  This is the single most important idea in the framework.
- Actions come in two kinds: **built-in actions** (defined on the base `Agent` class, listed below)
  and **custom actions** (methods you add to your own `WAgent` subclass). They are used identically;
  a transition just names the method and its arguments.
- A behavior is assembled in `world.py`'s `create_behav_files()` by chaining transitions
  (`add_transit`) and snapping in the reusable templates from this folder, then filling in blanks
  called **wildcards** (`add_wildcards`).

### The three I/O channels every agent has

Many actions read or write through these standard streams:

- **`stdin`**: the input fed to the model (its `proc`). Filled either by an incoming request's stream
  or by you staging data into `proc_input_0`.
- **`stdout`**: where the model's output is written, on `proc_output_0`.
- **`stdtar`**: the *target* (supervision) used during learning, so `learn` can compute a loss.

### Two recurring parameters worth understanding once

- **`num_steps`**: how many stream samples (ticks) an action spans. `learn`/`process` over
  `num_steps=50` means "consume 50 samples". The framework's readiness gate automatically pauses on
  ticks where no fresh data has arrived, so you count *samples*, not wall-clock.
- **`timeout`** / **`wait_completion`**: when you ask another agent to do something with `send`,
  `wait_completion=True` makes your action return `True` only once the other side reports completion
  (so your state machine blocks until then); `timeout` bounds that wait so a slow or dead peer cannot
  stall you.

### State machine vocabulary

- **Blocking state**: the agent pauses here until an external event (an incoming request) arrives.
  Used for reactive roles ("wait for the teacher to tell me to learn").
- **`ready=False` transition**: a transition that fires only when *another* agent triggers that
  action on you (a received request), as opposed to one you run on your own initiative.
- **Teleport**: a transition that fires automatically (usually after a `delay`) to move things along,
  typically as a timeout escape hatch.

---

## Wildcards you will see in the templates

Wildcards are placeholders (written `<like_this>`) that a world fills in with `add_wildcards`. The
common ones:

| Wildcard | Meaning |
|---|---|
| `<world>` | the world node (used to reference its streams, e.g. `<world>:cats`) |
| `<agent>` | the acting agent itself (used to reference its own recorded streams, e.g. `<agent>:recorded1`) |
| `<valid_cmp>` | the set of agents that passed the most recent `compare_eval` |
| `<roles_to_engage>` | the role(s) a teacher/requester should recruit |
| `<playlist>` | the current item of the preferred-streams playlist |
| `<learn_steps>`, `<eval_steps>` | how many samples a lecture / an exam spans |
| `<cmp_thres>` | the pass/fail threshold used by `compare_eval` |

A stream is addressed as `owner:name_or_group` (for example `<world>:cats` or `<agent>:recorded1`).

---

## Built-in actions, by category

Signatures below are simplified to the arguments you actually set in behaviors.

### Discovery and connection

- **`connect_by_role(role, filter_fcn=None)`**: search the network for agents with `role` and open a
  connection to each new one. `filter_fcn` is the *name* of a method on your agent that can drop some
  candidates (for example, "skip extractors I already used"). Returns `True` if at least one new
  connection was started.
- **`find_agents(role, engage=False, handshake_completed=False)`**: like the above but **local
  only**: it searches peers you already know, filling `_found_agents`. Set
  `handshake_completed=True` to consider only fully-connected peers.
- **`connected(agent=None, handshake_completed=False)`**: predicate: `True` when the given agent (or
  all currently engaged agents if `None`) is connected. With `handshake_completed=True` it requires
  the handshake to be done, which is the usual gate before you start working with a peer.
- **`disconnected(agent=None, handshake_completed=False)`**: the negation: `True` when the agent(s)
  are gone. Handy to route back to an idle state when a peer drops.
- **`disconnect(agent)`** / **`disconnect_by_role(role, disengage_too=False)`**: tear down
  connections. `disengage_too=True` politely disengages before disconnecting.

### Engagement (pairing a requester with workers)

"Engagement" is a lightweight lock that says "you and I are now working together".

- **`send_engage()`**: offer engagement to everyone in `_found_agents` (populated by
  `connect_by_role`/`find_agents`). It waits for acceptance and moves accepted peers into
  `_engaged_agents`.
- **`engage(acceptable_role=None)`**: the worker side: accept an engagement request, but only if the
  requester's role equals `acceptable_role` (for example a student accepts only a `teacher`). This is
  how a role refuses to be bossed around by the wrong kind of agent.
- **`send_disengage(send_disconnection_too=False)`** / **`disengage(disconnect_too=False)`**: end the
  pairing (optionally also disconnecting).
- **`disengage_all()`**: drop all engagements and mark yourself available again.
- **`agents_are_waiting()`**: predicate: `True` if some connected peers have not yet been handled,
  i.e. there is work to do in the check-in loop.
- **`all_engagements_completed()`**: predicate: `True` once every found agent has been engaged or
  discarded.

### Asking others to do work, and sending data

- **`send(action_name=None, target=None, action_kwargs=None, streams=None, data_samples=None,
  num_steps=-1, timeout=-1, callback=None, wait_completion=False, copy_sys=False, volatile=False,
  id="random")`**: the workhorse. Ask `target` (a peer id, a list, or a wildcard like `<valid_cmp>`)
  to run `action_name`, feeding it `streams` (a list of `owner:name` references) and/or literal
  `data_samples`, for `num_steps` samples. Key options:
  - `wait_completion=True`: block your state until the target(s) confirm completion (bounded by
    `timeout`). Leave it `False` to fire-and-forget and check later with `all_sent_completed`.
  - `callback="method_name"`: call that method on you when the interaction completes.
  - `data_samples={"proc_output_0": value}` with **no** `action_name`: push raw data straight into
    the recipients' stream slot without triggering any transition on them (this is the broadcast
    primitive used by the chat world).
  - `copy_sys=True`: carry the data you just produced into this new interaction (used to forward your
    own model output to someone else).
  - `volatile=True`: tell the recipient not to send completion status back (cannot be combined with
    `wait_completion`).
- **`all_sent_completed(action_name=None)`**: predicate: `True` when every `send` you dispatched
  (optionally only those for a given `action_name`) has completed. The standard exit condition after a
  fan-out of work.
- **`all_asked_finished()`**: predicate based on confirmations: `True` when every agent you asked has
  reported done.
- **`received_some_asked_data(processing_fcn=None, data_type=None)`**: predicate that also collects:
  `True` if any agent you asked has sent a stream sample back. If you pass `processing_fcn` (the name
  of a method on you), it is called as `fcn(agent, props, data, data_tag)` for each received sample,
  which is how a requester drains and stores incoming results (for example, collecting students'
  predictions or extractors' feedback).

### The worker side: inference and learning

- **`process()`**: run **one inference step**: read `stdin`, call the model (`proc`), write `stdout`.
  This is what a model does when asked to answer/predict without learning.
- **`learn()`**: run **one learning step**: do a `process`, then a backward pass against the target in
  `stdtar`, updating the model. Requires the agent to have an optimizer and loss in `proc_opts`,
  otherwise it does nothing. This is online learning: it happens sample by sample as the stream flows.
- **`show()`**: display the current input/output (useful for demos and human agents).

### Playlists: turning streams into a curriculum

A "preferred streams" list is a playlist the teacher walks through. This is how class-incremental
curricula and multi-signal lessons are expressed.

- **`set_pref_streams(net_hashes, repeat=1)`**: set the playlist to the given list of streams and
  reset the pointer to the start. `repeat=N` lays the whole list down N times back to back, so the
  teacher naturally teaches everything N times (the example worlds use this to teach each item several
  times before examining).
- **`next_pref_stream()`**: advance the pointer to the next item, wrapping around to the start at the
  end. Returning to the start is the natural "we finished a full pass" signal.
- **`first_pref_stream()`**: reset the pointer to the first item (used to restart a curriculum, e.g.
  after a student fails an exam).
- **`check_pref_stream(what="last")`**: predicate on the pointer position. `what` can be `first`,
  `last`, `not_first`, `not_last`, and, when `repeat>1`, `last_round` / `not_last_round` (am I in the
  final repetition of the whole playlist?) and `last_song` / `not_last_song` (am I at the last item of
  the current pass?). This is the trick that lets a world teach for the first rounds and only examine
  on the last one.

### Recording a stream into an owned snapshot

- **`record(record_uuid="see_interaction_uuid")`**: copy `num_steps` samples from the incoming
  stream(s) into a new agent-owned `recorded<N>` stream and publish it. Use it to freeze a live world
  stream into a fixed dataset you can teach from and exam against repeatably. The `record_uuid`
  argument selects which channel to read from: the default reads under the interaction's own uuid
  (peer-published, process-style flow); pass `record_uuid=None` when snapshotting a plain world stream
  that is not published per-interaction.

### Evaluation and grading

- **`evaluate(stream_hash, how, steps=100, re_offset=False)`**: compare each evaluated agent's
  buffered output against a reference stream (`stream_hash`, e.g. the ground-truth `<agent>:recorded1`
  or the special `<playlist>` for the current item). `how` is the metric: `"max"` for argmax/label
  accuracy-style comparison on classification, `"mse"` for signal regression. `steps` is how many
  samples to score. `re_offset=True` re-aligns the two streams' time origin before scoring, which is
  necessary when the produced output may start at a different phase (free-running generators) or when
  data tags are not reliable (text). Requires `buffer_generated_by_others` to be enabled on the
  grader so it actually has the other agents' outputs.
- **`compare_eval(cmp, thres, good_if_true=True)`**: turn the numeric `evaluate` results into a
  pass/fail set. `cmp` is one of `<`, `<=`, `>`, `>=` (threshold tests) or `min`/`max` (pick the best
  one). `thres` is the threshold. The agents that pass are placed in `<valid_cmp>`, which you then
  target for badges, promotion, or the next phase. Example: `cmp="<=", thres=0.65` means "pass if your
  error is at most 0.65"; `cmp="min", thres=0.5` means "the single lowest-error agent, among those
  below 0.5".

### Pub/sub (publish once, many subscribers)

- **`send_subscribe(agent, stream_hashes, unsubscribe=False)`**: ask `agent` to subscribe to (or
  unsubscribe from) the given pubsub streams.
- **`subscribe(stream_owners, stream_props, unsubscribe=False)`**: the receiving side that actually
  registers the subscription. Used, for example, so peers can listen to the best student's broadcast
  of predicted labels.

### Asking the world for rewards and role changes

These go to the world master, which is the only authority that can change a role or hand out a badge.

- **`suggest_role_to_world(agent, role)`**: propose that `agent` be given `role` (for example,
  promote a successful student to `teacher`). The world decides.
- **`suggest_badges_to_world(agent=None, score, badge_type="completed", badge_description=None)`** :
  propose awarding a badge. `score` must be positive; `badge_type` is one of the known types (e.g.
  `completed`, `intermediate`). Badges show up on the agent's profile.

### Control flow

- **`nop(message=None)`**: do nothing and return `True`. Used to take an unconditional transition (to
  chain a template in, to advance after a blocking wait, or to print a message).

---

## The template files in this folder

These JSON files are partial state machines a world snaps into a role's behavior, then specializes
with wildcards.

| Template | What it provides |
|---|---|
| `engage_by_role.json` | The recruiter loop: search → connect → find handshaked peers → engage. Parameterized by `<roles_to_engage>`. |
| `listening_to_teacher.json` | The reactive worker loop: wait engaged, react to incoming `learn` / `process`. |
| `teach-playlist_eval-playlist.json` | Teach each playlist item, then exam each item (used with multi-item curricula). |
| `teach-playlist_eval-recorded1.json` | Teach a playlist, then exam against a single recorded reference stream. |
| `teach-eval-playlist.json` | A teach-then-exam loop variant used by the social-learning world. |
| `service_requester.json` | A requester that connects to providers, asks them to `process` a stream, and collects replies. |
| `service_provider.json` | A provider that waits to be engaged and runs `process` on the requester's stream. |

---

## Writing your own action

```python
from unaiverse.agent import Agent, action

class WAgent(Agent):

    @action
    async def my_action(self, some_param: int = 1, interaction=None) -> bool:
        # ... do something ...
        return True    # True = done, take the transition; False = not yet, retry next tick
```

Then reference it from a transition in `create_behav_files()`:

```python
behav.add_transit("some_state", "next_state", action="my_action", args={"some_param": 3})
```

That is the whole contract. Anything a built-in action can do, a custom one can do too.

---

<sub>Part of the [UNaIVERSE examples](../README.md). Source for these actions lives in the main repo
([unaiverse-src](https://github.com/collectionlessai/unaiverse-src), `src/unaiverse/agent.py`).</sub>
