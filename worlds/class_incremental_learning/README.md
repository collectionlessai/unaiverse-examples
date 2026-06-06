# 🔁 Class-Incremental Learning

*Watch a model learn new digits and (maybe) forget the old ones.*

> A continual-learning lab in miniature. A teacher introduces MNIST digits one class at a time;
> students learn online and are examined on every class seen so far after each lesson, so the per-class
> accuracy table makes catastrophic forgetting visible in real time.
>
> Action names (`learn`, `process`, `all_sent_completed`, `received_some_asked_data`, ...) are
> explained inline and in full in the [Actions and Behaviors reference](../../behaviors/README.md).

---

## The big idea

Class-Incremental Learning (CIL) is the continual-learning setting where new classes arrive over time,
each class's data is shown only once, and the model must keep them all without revisiting old data. This
world stages CIL as a live classroom over the network on MNIST (digits 0 to 9).

The teacher's own docstring spells out the loop:

> ```
> 1. welcoming  -> wait for at least one student.
> 2. brainstorm -> pick the next action: teach a new class or evaluate.
> 3. lesson     -> fan-out `learn` to every student for one class, wait for completion.
> 4. exam       -> fan-out `process` to every student, collect predictions, then score.
> ```

Why it is a good teacher:

- The teacher controls the data schedule; the student controls the model. A class is streamed exactly
  once, in its own lesson, which is the CIL constraint, enforced by construction.
- Exams are cumulative: every exam tests all classes taught so far, so the colored accuracy table
  directly visualizes forgetting as new digits arrive.
- It is the honest baseline. The student is a plain SGD CNN with no anti-forgetting mechanism, so you
  can see forgetting happen, then swap in a continual-learning model and compare.
- It teaches distributed orchestration: one teacher fans the same lesson/exam out to N students at
  once, with per-interaction timeouts so a slow or dead student cannot stall the class.

---

## The story, step by step

1. MNIST is loaded locally (10 classes, standard normalization).
2. Per-class slices. When the teacher accepts its role ([`src/teacher.py`](./src/teacher.py)
   `accept_new_role`) it builds, per class: a teach set of `TEACH_PER_CLASS=50` train images (streams
   `images@teach_{cls}` and `labels@teach_{cls}`), and an eval set of `EVAL_PER_CLASS=20` test images
   concatenated in class order into one combined `images@eval` stream.
3. Welcoming. The teacher waits (`welcoming`) until at least one student connects or 90 seconds elapse.
4. Brainstorm to teach or evaluate (`should_teach_or_evaluate`): teach while fewer than 10 classes have
   been taught, otherwise evaluate.
5. Lesson (incremental). `init_lesson` fans the `learn` action out to all students over one class's
   `teach_{cls}` stream (50 samples). Students train online; the teacher blocks until
   `all_sent_completed(action_name="learn")` is true.
6. Exam (cumulative). After each lesson `send_exam` fans `process` out over `images@eval` for
   `20 * (number of classes seen)` samples, testing every class so far, with a 120-second timeout.
7. Collect and score. `received_some_asked_data(processing_fcn="collect_predictions")` gathers each
   student's predicted class index; `score_exam` computes overall and per-class accuracy and prints a
   colored table (green at or above 90 percent, yellow at or above 70, orange at or above 50, red
   below).
8. Loop. Back to welcoming, learning the next class, so the class set grows 0, then 0 and 1, then 0,1,2
   and so on, with exams revealing retention.

---

## Roles and how they are assigned

[`src/world.py`](./src/world.py): first world master to `teacher`, everyone else to `student`.
`world_masters_node_names=["Test1"]`, so [`run_1.py`](./run_1.py) (`Test1`) is the teacher and
[`run_2.py`](./run_2.py) (`Test2`) is a student. Launch more students by copying `run_2.py` with new
node names.

---

## The agents (the `proc`)

Teacher ([run_1.py](./run_1.py)): `Agent(proc=None, buffer_generated_by_others="one")`. No network;
pure orchestration and data provider. All the rich logic lives in [`src/teacher.py`](./src/teacher.py)'s
`WAgent`.

Student ([run_2.py](./run_2.py)):

```python
net = CNNMNIST(d_dim=10, seed=62)   # 1x28x28 in, 10 logits out, gray_mnist transform built in
agent = Agent(proc=net,
    proc_inputs =[StreamType(data_type="tensor", tensor_shape=(None,1,28,28), tensor_dtype=torch.float32, private_only=True)],
    proc_outputs=[StreamType(data_type="tensor", tensor_shape=(None,), tensor_dtype=torch.long,
                             proc_to_stream_transforms=lambda x: torch.argmax(x, dim=1), private_only=True)],
    proc_opts   ={'optimizer': torch.optim.SGD(net.module.parameters(), lr=0.05),
                  'losses':    [torch.nn.functional.cross_entropy]})
```

The output transform `argmax` converts logits to a class index before it hits the stream, so the
teacher's `collect_predictions` receives a ready-made label. The student needs no custom Python: it just
reacts to incoming `learn` / `process` requests.

---

## The data streams

Created by the teacher in `accept_new_role`, all private:

| Stream | Source | Size | Purpose |
|---|---|---|---|
| `images@eval` | MNIST test | 20 x 10 in class order | combined cumulative exam set |
| `images@teach_{cls}`, `labels@teach_{cls}` (10 of each) | MNIST train | 50 per class | one class's lesson |

Streams are addressed as `peer:name@group`, for example `f"{teacher_private_id}:images@teach_{cls}"`.

---

## The behavior state machines

_Every action named here is documented in the [Actions and Behaviors reference](../../behaviors/README.md)._

Note, different from the school worlds: this world ships hand-authored JSON
([`src/teacher.json`](./src/teacher.json), [`src/student.json`](./src/student.json)) and
`create_behav_files()` only renders them to PDF. The JSON is the source of truth: no templates, no
wildcards; step counts are passed at runtime via `num_steps` in the teacher's `send` calls.

Teacher (`init` to `wait_for_students` to `brainstorm` to lesson or exam): `brainstorm` branches on
`_current_intent` (`building_lesson` versus `building_evaluation`). `lesson_in_progress` (a blocking
state) exits on `all_sent_completed(action_name="learn")`. `exam_in_progress` self-loops on
`received_some_asked_data(processing_fcn="collect_predictions")` to drain replies, then
`all_sent_completed(action_name="process")` moves to `scoring` and back to `wait_for_students`.

Student, almost entirely reactive (`"ready": false` means wait for the teacher to trigger it):
`init` to `searching` to `connected` to `wait`, and in `wait`: an incoming `learn` triggers online
training, an incoming `process` triggers inference and emits predictions, then back to `wait`.

The fan-out plus completion plus collect idiom (`send(..., timeout=...)`, `all_sent_completed(...)`, and
a self-looping state with `received_some_asked_data(processing_fcn=...)`) is documented in the
[Actions reference](../../behaviors/README.md#asking-others-to-do-work-and-sending-data).

---

## Custom actions (all on the teacher)

_These are custom methods, built like (and used alongside) the built-in actions in the [Actions and Behaviors reference](../../behaviors/README.md)._

Defined in [`src/teacher.py`](./src/teacher.py), referenced by name in `teacher.json`:

- `on_tick`: refresh the connected-student roster, log joins and leaves.
- `welcoming`: true once at least one student is present or after the timeout.
- `should_teach_or_evaluate`, `building_lesson`, `building_evaluation`: choose and gate the next phase.
- `init_lesson`: fan `learn` out to all students over one class's `teach_{cls}` streams.
- `send_exam`: fan `process` out over `images@eval` for all classes seen so far (120-second timeout).
- `collect_predictions`: a processing function that records each student's predicted class.
- `score_exam`: compute overall and per-class accuracy, print the colored table.

The world also awards an "LOT2.0 champion!" badge to the overall best student via
`_process_custom_stat`. The student's `WAgent` is intentionally empty.

---

## How to run it

Manual (three terminals, world first):

```bash
python3 run_w.py     # world "ClassIncrementalWorld"
python3 run_1.py     # teacher "Test1" (world master)
python3 run_2.py     # student "Test2"
```

Or use the convenience launchers in this folder:

- [`run.sh`](./run.sh): an interactive launcher with two modes, a tmux dashboard (World in the
  background plus Teacher and Student panes) or detached `screen` sessions (`cil-world`, `cil-teacher`,
  `cil-student`), each with logging env toggles and a 10-second warm-up so the world comes up first.
- [`monitor.sh`](./monitor.sh): opens a tmux session that attaches to the three `screen` sessions in a
  World / Teacher / Student layout.

What to expect: the class set grows one digit per lesson; after each lesson the cumulative exam prints a
per-class accuracy table. With the plain SGD CNN you should see older digits' columns degrade as new
ones are learned, which is catastrophic forgetting made visible.

[`src/stats.py`](./src/stats.py) defines a live dashboard (network graph, exam error, per-class
accuracy, best-student table) for human visitors via the web platform.

---

## Key takeaways

1. Separation of concerns: the teacher owns when and which class is shown (once, never replayed); the
   student owns the model. Swap student models without touching the curriculum.
2. Behaviors can be authored as plain JSON: here `create_behav_files` only renders PDFs; the committed
   JSON is the protocol.
3. The fan-out, completion, collect idiom is robust to slow or dead peers thanks to per-interaction
   timeouts.
4. Forgetting is observable, not hidden: cumulative exams plus a per-class table turn the abstract idea
   of catastrophic forgetting into something you literally watch. Extend it with a continual-learning
   model (for example a CNU variant) to demonstrate mitigation; compare with
   [`animal_school`](../animal_school).

<sub>Part of the [UNaIVERSE examples](../../README.md). Action names are explained in the [Actions reference](../../behaviors/README.md).</sub>
