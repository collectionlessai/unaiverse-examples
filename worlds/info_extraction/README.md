# 🌐 Social Information Extraction

*Many different models observing one shared stream, and pooling what they see.*

> One agent streams images. Several "extractor" agents, each wrapping a *different* vision model,
> watch the same stream in parallel and each contributes its own kind of description. The user
> collects every extractor's feedback into a single JSON file. New extractors can join on the fly and
> are discovered and used automatically.
>
> Action names (`connect_by_role`, `send_engage`, `received_some_asked_data`, ...) are explained inline
> and in full in the [Actions and Behaviors reference](../../behaviors/README.md).

---

## The big idea

A "user" node streams a sequence of images into the world. Any number of "extractor" agents connect
to that user, each processes the *same* image stream, and each sends back its own textual feedback.
The user aggregates everything, keyed by image and by extractor, into `extracted_info.json`.

What makes it instructive:

- **Heterogeneous agents on one stream.** The user does not know which models exist in advance. Three
  different families (a ViT image classifier, a SmolVLM vision-language model, a Faster R-CNN object
  detector) all consume the identical image stream and each contributes a different *kind* of answer.
- **Open membership, role by capability.** Extractors are matched to a role by the *shape* of their
  declared inputs and outputs, not by hard-coded identity. `run_demo_b.py` shows you can add another
  extractor at runtime and it is picked up automatically.
- **Collaborative extraction with deduplication.** The user asks every extractor to process the
  stream, aggregates the multiple replies per image, and never re-asks an extractor it has already
  used.

The world's welcome message states it directly:

> "Welcome to the world of Information Extraction. There are two types of citizens: 'users' who stream
> images (through an environmental stream) and 'extractors' who provide a textual feedback about the
> streamed images."

---

## The story, step by step

1. **The world starts** ([`run_w.py`](./run_w.py), node `InfoExtraction`), defining the two roles and
   their behaviors.
2. **A user joins and streams images.** [`run_demo_a.py`](./run_demo_a.py) builds an `ImageFileStream`
   over [`data/animals`](../../data/animals) driven by `first3c_1i.csv`, which lists three images
   (albatross, cheetah, giraffe). The stream is private, non-circular, and shown on screen. The user's
   `proc` is `None`: it is a pure data source.
3. **Extractors join.** [`run_1.py`](./run_1.py) wraps a `ViT` classifier (emits ImageNet labels);
   [`run_2.py`](./run_2.py) wraps `SmolVLM` (emits a free-text caption); [`run_demo_b.py`](./run_demo_b.py)
   wraps `FasterRCNN` (emits detected object names).
4. **The user orchestrates.** It connects to the available extractors, engages them, and sends a
   `process` request asking each to run over all samples of the `animal_stream`.
5. **Feedback is collected.** As each extractor replies, `handle_received_data` records the text into
   `extracted_info.json`, keyed by image tag and by extractor node id.
6. **Adding an extractor on the fly.** Start `run_demo_b.py` at any time. Because role assignment is by
   capability, the user discovers the new extractor, asks it to process the same stream, and merges its
   detections into the same JSON. A filter ensures already-used extractors are not re-used.

Resulting JSON shape:

```json
{
  "<image_tag>": {
    "<node_id>": {
      "info": ["<textual feedback>"],
      "extractor": "<node_name>: <description> (<N> badges)"
    }
  }
}
```

---

## Roles and how they are assigned

`WWorld.assign_role` ([`src/world.py`](./src/world.py)) inspects the joining node's profile:

- **`user`** if the node offers a private, environmental image stream (an image stream that is not
  public and not a model input port).
- **`extractor`** if the node's `proc` consumes images (private image input) and emits text-like
  output (private text output, or a labeled tensor output).
- otherwise **no role**.

| Script | Node | Role | Why |
|---|---|---|---|
| [run_demo_a.py](./run_demo_a.py) | `_Test0` | user | offers a private image stream, `proc=None` |
| [run_1.py](./run_1.py) | `ViT` | extractor | image in, labeled-tensor out |
| [run_2.py](./run_2.py) | `SmolVLM` | extractor | image+text in, text out |
| [run_demo_b.py](./run_demo_b.py) | `Test1` | extractor | image in, tensor+text out (Faster R-CNN) |

This world does not use `world_masters_node_names`: roles are decided purely by capability.

---

## The agents (the `proc`)

- **User** ([run_demo_a.py](./run_demo_a.py)): `Agent(proc=None)`. A data streamer and orchestrator.
  The behavior lives in [`src/user.py`](./src/user.py).
- **ViT** ([run_1.py](./run_1.py)): `ViT()` (torchvision `vit_b_16`, ImageNet weights). Output is a
  labeled tensor over the 1000 ImageNet classes, which the user renders as a class name.
- **SmolVLM** ([run_2.py](./run_2.py)): `SmolVLM()` (HF `SmolVLM2-500M-Video-Instruct`). Given an
  image and a default question "what is this?", it returns a caption.
- **Faster R-CNN** ([run_demo_b.py](./run_demo_b.py)): `FasterRCNN()` (torchvision
  `fasterrcnn_resnet50_fpn`). Keeps detections above a score threshold and returns class indices,
  scores, boxes, and a comma-joined text of class names. The trailing text output is what qualifies it
  as an extractor.

All extractor inputs and outputs are private (`private_only=True`), which is exactly what
`assign_role` requires.

---

## The data streams

Only the **user** publishes a stream; extractors expose model I/O ports rather than environmental
streams.

```python
stream = DataStream.create(group="animal_stream", public=False,
    stream=ImageFileStream(image_dir=".../data/animals", show_images=True, circular=False,
                           list_of_image_files=".../first3c_1i.csv"))
agent.add_stream(stream)
agent.add_behav_wildcard("<stream_name>", "animal_stream")
agent.add_behav_wildcard("<stream_len>", len(stream))
```

The two per-agent wildcards `<stream_name>` and `<stream_len>` fill the `send(streams=["<stream_name>"],
num_steps="<stream_len>")` transition in the user's behavior.

---

## The behavior state machines

_Every action named here is documented in the [Actions and Behaviors reference](../../behaviors/README.md)._

Built in `create_behav_files()` and saved to [`user.json`](./src/user.json) /
[`extractor.json`](./src/extractor.json). Both reuse templates from [`../../behaviors`](../../behaviors):
**`service_requester.json`** for the user and **`service_provider.json`** for the extractor.

**User** (a service requester): `ready` (runs `check_status`) connects to extractors
(`connect_by_role(role="extractor", filter_fcn="filter_addresses")`), engages them, sends `process`
over the stream, then drains replies with
`received_some_asked_data(processing_fcn="handle_received_data")` until `all_sent_completed`. The
template is specialized with wildcards:

```python
behav.add_wildcards({"<provider_role>": "extractor",
                     "<providers_filter_fcn>": "filter_addresses",
                     "<providers_data_processing_fcn>": "handle_received_data"})
```

**Extractor** (a service provider): `ready` waits for `engage(acceptable_role="user")`, runs the
built-in `process` on the engaged user's stream, then returns to `ready`. The only wildcard is
`{"<user_role>": "user"}`. Both machines include timeout teleports so neither side gets stuck.

---

## Custom actions

_These are custom methods, built like (and used alongside) the built-in actions in the [Actions and Behaviors reference](../../behaviors/README.md)._

All three live in [`src/user.py`](./src/user.py):

- `check_status` runs at the top of every cycle: drop stale engagements/connections, and either
  initialize, load, or persist `extracted_info.json`. Deleting that file mid-run is the user-facing
  "reset" signal that re-enables all extractors.
- `filter_addresses` is a `connect_by_role` callback that drops extractors already used in a previous
  round, giving the no-double-use behavior.
- `handle_received_data` is the `processing_fcn` for `received_some_asked_data`: it converts each reply
  to text (`props.to_text(...)`), records it under the sender's node id, marks that extractor as used,
  and flags that new info should be persisted.

The extractor has no custom actions: `engage` and `process` are built-ins.

---

## How to run it

Open four terminals from this folder, world first:

```bash
python run_w.py        # node "InfoExtraction"
python run_demo_a.py   # node "_Test0": streams 3 images, deletes and monitors extracted_info.json
python run_1.py        # node "ViT": classifier extractor
python run_2.py        # node "SmolVLM": captioner extractor
```

To add an extractor on the fly, at any time after the world is up:

```bash
python run_demo_b.py   # node "Test1": Faster R-CNN object detector
```

**What to expect:** the user pops up each of the three images, cycles through "look for extractors,
connect, engage, ask them to process, collect replies", and writes the aggregated result to
`extracted_info.json` in the directory where you launched the user. Delete that file to reset and
re-run all extractors.

---

## Key takeaways

1. **Role assignment by capability shape, not identity.** `assign_role` decides user vs extractor from
   declared stream and `proc` I/O types, which is what lets arbitrary models join and be used without
   the world knowing them in advance.
2. **Reusable templates plus wildcards build a protocol.** The generic `service_requester` /
   `service_provider` templates are specialized per world with `add_wildcards` and per agent with
   `add_behav_wildcard`.
3. **Custom actions are just methods named in transitions.** `received_some_asked_data(processing_fcn=...)`
   and `connect_by_role(filter_fcn=...)` are the hook points for injecting your logic into built-in actions.
4. **One stream, many parallel observers, aggregated results.** Heterogeneous extractors process the
   same stream concurrently and the user merges their feedback, with bookkeeping to avoid re-using the
   same extractor.

See also: [`chat`](../chat) for the simpler relay pattern, and [`turing`](../turing) for large-scale
multi-agent orchestration.

<sub>Part of the [UNaIVERSE examples](../../README.md). See [unaiverse.io](https://unaiverse.io) and [Collectionless AI](https://collectionless.ai).</sub>
