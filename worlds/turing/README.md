# 🏨 Turing Hotel

*A distributed multi-agent Turing test, run as a social-deduction game.*

> The flagship complex world. Humans and LLM bots check into a hotel, get anonymously matched into
> rooms of four, chat for a fixed time, then each guest votes on who they think was a bot. It
> showcases nearly every advanced framework feature: three roles each with its own behavior, a
> three-tier management hierarchy, pubsub and direct streams, live matchmaking, timed conversation,
> vote parsing and scoring, and a custom HTML leaderboard.
>
> This world hand-builds its state machines from raw actions, so it is the best place to learn the
> action API. Every action is explained in the [Actions and Behaviors reference](../../behaviors/README.md).

---

## The big idea

A multi-agent Turing test framed as a hotel. From `Config.init_message`:

> "This is a unique destination composed of rooms that implement the multi-agent Turing Test, where
> you will act as both the judge and a conversation partner. You will judge others to detect who is
> human, while others judge whether you are a human or a machine (remember to act human)."

Why it is worth studying:

- **Anonymity by design.** Real peer ids and nickname are never shown. Each room mints disposable fake
  names ("Ada", "Ben", "Cal", ...) and all chat is relayed through the floor manager, so guests never
  connect to each other directly. The test only works if you cannot see who you are talking to.
- **A real matchmaking problem.** Agents arrive and leave at arbitrary times across independent nodes;
  the system continuously packs them into rooms of four, handling overbooking, disconnections, and
  timeouts, and reconciles a global view from per-floor pubsub updates with sequence-tagged,
  gap-detecting reconstruction.
- **A three-tier hierarchy** (Hotel, Floor, Room) that mirrors how you would shard a real coordination
  workload: the hotel manager load-balances onto floors, the floor manager owns per-room conversation,
  timing, and voting, and the Room is a pure in-memory bookkeeping object.
- **Humans and bots, transparently.** The same `guest.json` behavior runs whether the guest is a
  person typing at the keyboard or an LLM. The only branch is whether to wait for a human to press
  enter.
- **An elaborate "act human" prompt.** `Config.history_incipit` is a long persona prompt (identity,
  how to write like a real person, anti-repetition, a bot-detection guide), a concrete study in
  adversarial persona prompting.

This world uses no behavior templates and no wildcards: every machine is hand-built transition by
transition, which makes it the best place to learn the raw state-machine API.

---

## The story, step by step

1. **Check-in.** A guest joins, gets the `guest` role, and enters `init`. A human sees the welcome and
   must type to begin; a bot skips straight to `ready`. In `ready` the guest picks a random hotel
   manager and connects. After the handshake it lands in `hall`. If the manager never acks within the
   timeout, it disconnects, waits a decompression period, and retries.
2. **Assignment to a floor.** The hotel manager's `check_in` finds connected guests not yet on a floor
   and packs them across the floors it knows about; `send_to_floor` tells each guest which floor
   manager to connect to.
3. **Assignment to a room.** From `hall` the guest connects to its floor manager and declares its
   sponsor. The floor manager's `check_in` picks a room (at most four guests, with one overbooking
   slot), inserts the guest into the `Room` with a fresh fake name, and sends `goto_room`.
4. **Timed anonymous chat.** When a guest arrives at a room, the floor manager sends a start message
   ("You were named Ada and the other guests are Ben, Cal..."). The guest parses the names, seeds its
   conversation history with the persona prompt, and loops: write a message, send it to the floor
   manager, which relays it to the others under the sender's fake name. Reminders with time remaining
   are sent periodically; typing "exit" leaves early.
5. **Voting.** When a guest's time at the table reaches `test_duration`, it is sent to the voting
   booth and asked to list who it thinks were humans.
6. **Scoring and display.** The floor manager packages each vote (voter, voter nature, vote text,
   ground truth per fake name, message counts) and sends it to the sponsoring hotel manager. The hotel
   manager validates it, parses the free text into a per-name human/ai judgment, drops votes about
   people you barely talked to, and stores one stat per voter/votee pair. The world's stats build the
   leaderboard: a confusion matrix, a votee "Turing score" (fooling rate weighted by conversation
   length), and a voter "detection score" (F1 of human detection).

---

## Roles and how they are assigned

`WWorld.assign_role` ([`src/world.py`](./src/world.py)) is file-driven:

```python
unaid = build_unaid(profile)
if unaid in self.hotel_managers:  return "hotel_manager"
if unaid in self.floor_managers:  return "floor_manager"
return "guest"
```

The manager sets are loaded from `src/managers.txt` and hot-reloaded when the file changes. So role is
identity in a config file, and everyone else defaults to guest.

The hotel/floor/room abstraction (pure in-memory bookkeeping, no networking):

- **`Hotel`** ([src/hotel.py](./src/hotel.py)), held by a hotel manager: a reconstructed view of
  floors, rooms, and where each guest is, rebuilt from floor-update packets.
- **`Floor`** ([src/floor.py](./src/floor.py)), the authoritative structure created by a floor
  manager: owns its rooms and the mapping of guests to rooms and sponsors.
- **`Room`** ([src/room.py](./src/room.py)), the heart of anonymity and ground truth: maps peer id to
  fake name, tracks who is human vs artificial, per-guest status and timers, and the directed
  message-exchange counters used to gate votes and compute scores. There is no separate "room manager"
  node; the room is owned by the floor manager.

Which script is which:

- [run_1.py](./run_1.py): node `TuringHotelManager`, `proc=None`, hotel manager.
- [run_2.py](./run_2.py): node `TuringFloorManager`, `proc=None`, floor manager.
- [run_3.py](./run_3.py) through [run_11.py](./run_11.py): nine guest nodes (Grace, Tony, Jenny, Bear,
  Cat, Andrew, Taylor, Carlos, Giovanni).

---

## The agents (the `proc`)

- **Hotel manager and floor manager:** `proc=None`. They never run inference; all their work is
  orchestration in action methods. Both raise the max concurrent interactions and use a thread pool for
  fan-out. The floor manager also creates the world's streams.
- **Guests in this example:** `proc=LoggerModule()`, a module whose forward ignores input and returns a
  cycling dummy word. So out of the box these nine guests are placeholder bots that emit nonsense,
  useful for load-testing the orchestration with no API cost. Each is wrapped with a policy filter that
  adds a small delay and jitter to message timing (one guest, Jenny, is deliberately slow).
- **Real LLM bots** would swap the proc, exactly as in the sibling [`lonewolves`](../../lonewolves)
  examples: `proc=Phi()` (a local Hugging Face model) or
  `proc=FeatherlessAPI(model="Qwen/Qwen3-32B", ...)` (a hosted model). In this world the persona is
  injected as conversation context (`history_incipit`), not as the proc's system prompt.
- **Human guests:** `proc=None` with a human node type; the human types at the keyboard, and the guest
  waits for input before starting.

Guests and the floor manager declare `["text"]` in and `["text"]` out; the hotel manager declares no
processor I/O.

---

## The data streams

Created by the floor manager and advertised in its profile:

- **`floor_updates`** (pubsub): JSON floor-state packets published every few seconds, each stamped with
  an increasing tag. Hotel managers subscribe and reconstruct their `Hotel` view, detecting missed tags
  and count discrepancies.
- **`chat`** (direct): individual chat messages broadcast from the floor manager to room members.
- **`votes`** (direct): the JSON vote packets the floor manager sends to the sponsoring hotel manager.
- **`processor_in` / `processor`:** each guest's own model I/O, where the assembled history goes in and
  the reply comes out.

---

## The behavior state machines

_Every action named here is documented in the [Actions and Behaviors reference](../../behaviors/README.md)._

All three are built in `create_behav_files()`. Useful vocabulary: `add_state(name, blocking, msg,
action)`; `add_transit(from, to, action, args, ready, teleport, delay, callback)`. A `teleport`
transition fires automatically to advance when no real action matched, which is how each machine loops.
A `ready=False` transition handles externally triggered (sent) actions.

- **Hotel manager** ([hotel_manager.json](./src/hotel_manager.json)): a six-state loop, discover floor
  managers, check guests in, assign them to floors, ingest pubsub floor updates, process votes, report
  violations, repeat.
- **Floor manager** ([floor_manager.json](./src/floor_manager.json)): an eight-state loop, collect
  sponsorships, check guests in, assign them to rooms, run the conversation and timing engine
  (`handle_guests_by_status`), publish floor updates, send votes, relay chat.
- **Guest** ([guest.json](./src/guest.json)): a thirteen-state journey with user-facing status
  messages, from `init` and `ready` to `hall`, `floor`, `room_round_table` (the chat loop), and
  `room_voting_booth` (the vote), then back to `hall`.

The chat timing and the voting deadlines live inside the floor manager's per-guest handler, driven by
each room's per-guest timers against `Config.test_duration` and `Config.survey_reply_time`. The state
machine provides the states; the action implements the clock.

---

## Custom actions

_These are custom methods, built like (and used alongside) the built-in actions in the [Actions and Behaviors reference](../../behaviors/README.md)._

Each role's `WAgent` defines its own action methods (transition names match these methods). Highlights:

- **Hotel manager** ([src/hotel_manager.py](./src/hotel_manager.py)): `discover_floor_managers`,
  `check_in`, `send_to_floor`, `update_hotel` (reconstruct the global view from pubsub diffs),
  `send_violations`, `get_votes` (validate, parse, gate by message count, store per-votee stats).
- **Floor manager** ([src/floor_manager.py](./src/floor_manager.py)): `accept_new_role` (create the
  floor and streams), `get_guest_sponsor`, `check_in` and `send_to_room` (matchmaking and fake-name
  allocation), `handle_guests_by_status` (the conversation, timing, and voting engine),
  `pub_floor_updates`, `send_votes`, `get_msg_and_broadcast` (relay chat under fake names and count
  exchanges).
- **Guest** ([src/guest.py](./src/guest.py)): `connect_to_hotel_manager`, `connect_to_floor_manager`,
  `send_guest_sponsor`, `get_status_msg` (parse tagged start/join/leave/reminder messages and grow the
  history), `get_msgs`, `send_msg`, plus an `on_tick` watchdog that recovers from lost managers and
  stuck states.

Supporting utilities ([src/utils.py](./src/utils.py)): `parse_vote_msg` turns free-text votes into a
per-name human/ai judgment with robust handling of "nobody", "everyone", lists, and reversed phrasing;
`compute_check_in_proposals` is the matchmaking algorithm (prefer partly full rooms, then overbooking,
then a new empty room), shared by both Hotel and Floor; `print_live` renders the live console table.
[src/html_renderer.py](./src/html_renderer.py) renders the themed leaderboard dashboard from the stats
defined in [src/stats.py](./src/stats.py).

---

## How to run it

Each script is a node; start the world first, then the managers, then the guests, all joining
`"TuringHotel"`:

```bash
python run_w.py    # world node "TuringHotel" (generates the three behavior JSONs)
python run_1.py    # "TuringHotelManager": hotel manager
python run_2.py    # "TuringFloorManager": floor manager
python run_3.py    # ... through run_11.py: nine guest nodes
```

All nine shipped guests are placeholder bots (Jenny is the slow one). To get a real Turing test,
replace a guest's proc with `Phi()` or `FeatherlessAPI(...)`, or join as a human node. Manager
identities must be listed in `src/managers.txt` matching the node's `owner@nickname/NodeName`, or that
node would become a manager instead of a guest.

**What to expect:** the managers print live tables of floors, rooms, and occupancy; guests print status
lines as they move from hall to floor to room. With nine guests they pack into rooms of four, chat for
the configured duration, then get the vote survey, and the world serves the leaderboard.

---

## Key takeaways

1. **Roles map one-to-one to `WAgent` subclasses and hand-built state machines.** With no templates or
   wildcards, this is the clearest place to learn the raw state-machine API: teleports, `ready=False`
   transitions, blocking states, callbacks, and stuck-state recovery.
2. **The `proc` is orthogonal to behavior.** The same `guest.json` runs a human, a dummy bot, or a real
   LLM; swapping intelligence is one constructor argument in the run file, and the persona comes from
   the conversation context.
3. **Coordination is just action methods plus streams.** Managers with `proc=None` do all their work
   through actions, fan-out sends with callbacks, and pubsub plus direct streams: a complete pattern for
   distributed orchestration with no machine learning at all.
4. **Anonymity, matchmaking, and eventual consistency are first-class.** The room hides identities,
   the matchmaker packs a churning population into rooms, and the hotel manager reconstructs global
   state from tagged pubsub diffs with gap detection.
5. **Custom stats and a renderer turn interactions into a product.** Votes flow guest to floor to hotel
   to world as validated JSON, get parsed and scored with purpose-built metrics, and are rendered into
   a themed leaderboard.

See also: [`chat`](../chat) for the underlying relay pattern in isolation.

<sub>Part of the [UNaIVERSE examples](../../README.md). See [unaiverse.io](https://unaiverse.io) and [Collectionless AI](https://collectionless.ai).</sub>
