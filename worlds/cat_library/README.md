# 📚 Cat Library

*The smallest possible "teacher to student" world. Start here.*

> If you have never read a UNaIVERSE world, read this one first. It is the minimal end-to-end example:
> one teacher, one student, one stream of words, no custom code. Everything here reappears, scaled up,
> in every other world.
>
> New to the action names below (`record`, `engage`, `set_pref_streams`, ...)? Each one is explained
> inline, and in full in the [Actions and Behaviors reference](../../behaviors/README.md).

---

## The big idea

A teacher recites a little "poem" about cats (a fixed sequence of word tokens) and a student has to
memorize it and recite it back. The student is a tiny recurrent language model that learns the
sequence online, while it streams, then sits an exam where it must reproduce the poem.

What you learn in one sitting:

- **The anatomy of a world**: a `World` subclass that owns a data stream and assigns roles, an `Agent`
  that wraps a PyTorch model, and behaviors (state machines) that choreograph who does what and when.
- **Behaviors are assembled, not written from scratch**: the teacher and student behaviors are built
  by snapping together reusable templates from [`../../behaviors`](../../behaviors) and filling in a
  few blanks (wildcards).
- **Learning happens inside the student; teaching is just orchestration**: the teacher has no neural
  network at all (`proc=None`). It only records the stream, sends the student requests, and grades.

---

## The story, step by step

1. The world boots ([`run_w.py`](./run_w.py)) hosting `WWorld`. Its constructor publishes one private
   data stream named `cats`, a `TokensStream` read from
   [`data/cats/stream_of_words.csv`](../../data/cats/stream_of_words.csv) (max 998 tokens).
2. The teacher joins ([`run_1.py`](./run_1.py), node `Test1`). It is declared a world master, so it
   gets the `teacher` role. Its model is `proc=None`: a pure orchestrator.
3. The teacher prepares the "book". Its behavior first runs `record`, which snapshots the live `cats`
   stream into a teacher-owned buffer called `recorded1` (998 samples). This frozen copy is both the
   lesson and the exam.
4. The teacher recruits a student with the `engage_by_role` template (with the wildcard
   `<roles_to_engage>` set to `student`): it searches the world, connects, finds a handshaked student,
   and engages it.
5. The student joins ([`run_2.py`](./run_2.py), node `Test2`) and gets the `student` role. Via the
   `listening_to_teacher` template it waits in a `teacher_engaged` state, ready to react.
6. The lesson (50 repetitions). The teacher sets its preferred stream to `recorded1` with `repeat=50`
   and sends the student `learn` requests over it. The student trains its small RNN online, one token
   at a time, predicting the next word, repeated 50 times so the sequence sinks in.
7. The exam. The teacher sends a `process` request over the same `recorded1`. The student now runs
   inference only (no learning) and streams back its reconstructed poem.
8. Grading. The teacher runs `evaluate` to compare the student's output against the ground truth, then
   `compare_eval(cmp="<=", thres=0.2)`: pass if the error is small enough.

---

## Roles and how they are assigned

[`src/world.py`](./src/world.py):

```python
def assign_role(self, profile, is_world_master):
    if is_world_master:
        return "teacher" if len(self.world_masters) <= 1 else "student"
    return "student"
```

The first world master becomes the `teacher`; everyone else is a `student`. [`run_w.py`](./run_w.py)
declares `world_masters_node_names=["Test1"]`, so node `Test1` ([`run_1.py`](./run_1.py)) is the
teacher and `Test2` ([`run_2.py`](./run_2.py)) is the student.

---

## The agents (the `proc`)

| Node | Role | `proc` (model) | Why |
|---|---|---|---|
| `Test1` ([run_1](./run_1.py)) | teacher | `None` | Pure orchestrator. `buffer_generated_by_others="all"` so it can capture the student's exam output for grading. |
| `Test2` ([run_2](./run_2.py)) | student | `RNNTokenLM` | A small recurrent token language model: `emb_dim=16, h_dim=100`, vocabulary-sized input and output. |

The student's I/O is text tokens from the cats vocabulary:

```python
proc_inputs  = [StreamType(data_type="text", stream_to_proc_transforms={w:i ...}, proc_to_stream_transforms=voc)]
proc_outputs = [StreamType(data_type="text", ...same vocabulary...)]
proc_opts    = {'optimizer': torch.optim.SGD(net.parameters(), lr=0.01),
                'losses':    [torch.nn.functional.cross_entropy]}
```

Why declare `proc_inputs` at all? The framework wires the model's stdin by iterating over
`proc_inputs`. Leave it empty and stdin stays unbound, so `process` and `learn` silently do nothing.
Input and output share one vocabulary because the model predicts the next token of the same language
it reads.

---

## The data stream

```python
self.add_stream(DataStream.create(
    name="cats", public=False,
    stream=TokensStream(tokens_file_csv=".../data/cats/stream_of_words.csv", max_tokens=998)))
```

One private (`public=False`) text-token stream. The student rebuilds its own vocabulary from the same
CSV (a private, non-shared copy) so its embedding and output sizes match.

---

## The behavior state machines

_Every action named here is documented in the [Actions and Behaviors reference](../../behaviors/README.md)._

Both behaviors are generated by `create_behav_files()` in [`src/world.py`](./src/world.py) and saved
to [`src/teacher.json`](./src/teacher.json) and [`src/student.json`](./src/student.json). They are
assembled by chaining three templates from [`../../behaviors`](../../behaviors).

Teacher (`init` to `book_prepared` to the teach/exam loop). The actions it uses, with the parameter
rationale:

- `record` (args `streams=["<world>:cats"]`, `num_steps=998`, `record_uuid=None`): snapshot the world
  stream into `recorded1`. `record_uuid=None` because a plain world stream is not published per
  interaction. See [reference](../../behaviors/README.md#recording-a-stream-into-an-owned-snapshot).
- the `engage_by_role` template: recruit students of role `<roles_to_engage>`.
- `set_pref_streams(net_hashes=[<agent>:recorded1], repeat=50)`: make the recorded book the playlist,
  laid down 50 times so it is taught 50 times.
  See [reference](../../behaviors/README.md#playlists-turning-streams-into-a-curriculum).
- the `teach-playlist_eval-recorded1` template: teach the playlist, then exam against `recorded1`,
  with wildcards `<learn_steps>=998`, `<eval_steps>=998`, `<cmp_thres>=0.2`.

Student (`init` to `teacher_engaged`): chains `listening_to_teacher` via
`engage(acceptable_role="teacher")` (accept only a teacher), then reactively runs `learn` / `process`
as asked, returning to `init` on `disengage`.

A real gotcha preserved in the code: text data tags are not reliable at eval time, so the world forces
`re_offset=True` on the `evaluate` action to re-align the first compared pair. Details like this are
exactly what the examples exist to show.

---

## How to run it

Three terminals, world first:

```bash
python run_w.py     # world node "CatLibrary" (declares Test1 as world master / teacher)
python run_1.py     # node "Test1": teacher (proc=None, orchestrator)
python run_2.py     # node "Test2": student (RNN token LM, learns the poem)
```

All nodes are `hidden=True` (private to you). Watch the teacher march through
record, engage, teach (50 times), exam, evaluate, and the student flip between `teacher_engaged`,
`finished_learning`, and `finished_exam`. Set `NODE_PRINT=1` (basic) or `NODE_PRINT=2` (debug) to see
more.

---

## Key takeaways

1. A world is streams plus `assign_role` plus per-role behaviors. That is the whole pattern.
2. The teacher needs no model. Orchestration (record, engage, teach, exam, grade) is expressed
   entirely as state-machine actions.
3. Behaviors are composed from reusable templates parameterized by wildcards. You rarely write a
   machine by hand.
4. Learning is online: the student trains token by token as the stream flows, then is graded by
   reproducing it. This is the seed of every "school" world in this repo.

Next: read [`signal_school`](../signal_school) (forward learning of signals) or
[`animal_school`](../animal_school) (image classification and promotion to teacher).

<sub>Part of the [UNaIVERSE examples](../../README.md). Action names are explained in the [Actions reference](../../behaviors/README.md).</sub>
