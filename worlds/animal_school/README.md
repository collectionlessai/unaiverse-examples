# 🐾 School of Animals

*Online image classification, and earning the right to teach.*

> The natural next step after [`cat_library`](../cat_library): the same teacher/student skeleton, but
> now the students are convolutional networks learning to recognize animals, the curriculum is
> class-incremental (one animal at a time), and a student who aces the exam is promoted to teacher. It
> is also a tidy head-to-head between two architectures.
>
> Action names (`record`, `set_pref_streams`, `evaluate`, ...) are explained inline and in full in the
> [Actions and Behaviors reference](../../behaviors/README.md).

---

## The big idea

A teacher streams pictures of three animals (albatross, cheetah, giraffe), one class per lecture.
Students are CNN agents that learn online from the picture stream. After the lectures the teacher
gives a mixed exam; students who pass get a badge and are promoted to `teacher` so they can teach the
next cohort. Knowledge propagates through a small society of agents.

What you learn here:

- **Class-incremental learning as a playlist.** Each class is a separate recorded lecture;
  `set_pref_streams` plus `next_pref_stream` plus `check_pref_stream` turn three single-class streams
  into a sequential curriculum, the classic setting where catastrophic forgetting shows up.
- **Architecture matters.** Two students differ only in their classifier head: one uses a Continual
  Neural Unit (CNU) key-memory layer designed to resist forgetting; the other is a plain CNN baseline.
  Run both and compare.
- **Roles are earned.** The chain `evaluate`, `compare_eval`, `suggest_badges_to_world`,
  `suggest_role_to_world("teacher")` is a complete social-learning loop.

---

## The story, step by step

1. The world boots ([`run_w.py`](./run_w.py), node `AnimalSchool`) and publishes four image groups as
   streams: `albatross`, `cheetah`, `giraffe`, and `all` (a mixed 3-class set). Training images skip
   the first 10 per class; the `all` exam set uses the first images, so training and exam do not
   overlap.
2. The teacher joins ([`run_1.py`](./run_1.py), node `Test1`, `proc=None`). It snapshots the streams
   into four teacher-owned recordings: `recorded1 = all` (the exam, 30 samples) and
   `recorded2/3/4 = albatross/cheetah/giraffe` (lectures, 40 samples each).
3. The teacher recruits students via the `engage_by_role` template (`<roles_to_engage>` = `student`).
4. Students join: [`run_2.py`](./run_2.py) (`Test2`, CNN plus CNU) and [`run_3.py`](./run_3.py)
   (`Test3`, plain CNN).
5. Teaching the playlist. The teacher sets its preferred streams to the three lectures and loops: for
   each lecture it sends the student a `learn` request (40 samples), advances with `next_pref_stream`,
   and `check_pref_stream` decides "teach again" versus "time for the exam". The student trains online
   on each class in turn.
6. The exam. The teacher sends a `process` request over `recorded1` (the mixed `all` set, 30 samples).
   The student runs inference; the teacher buffers its predictions.
7. Grading. `evaluate(stream_hash=<agent>:recorded1, how="max", steps=30)` then
   `compare_eval(cmp="<=", thres=0.65)`. The metric is an error, so lower is better: error at most 0.65
   passes.
8. Reward and promotion. Each passing student gets the badge "Completed the Animal School
   #ImageClassification #AnimalPictures", is promoted to `teacher` via `suggest_role_to_world`, and is
   disengaged.

---

## Roles and how they are assigned

[`src/world.py`](./src/world.py):

```python
def assign_role(self, profile, is_world_master):
    if is_world_master:
        return "teacher" if len(self.world_masters) <= 1 else "student"
    return "student"
```

`world_masters_node_names=["Test1"]`, so `Test1` is the first master and the teacher; everyone else is
a student. After promotion, a successful student can become a teacher too.

| Script | Node | Role | Model |
|---|---|---|---|
| [run_1.py](./run_1.py) | `Test1` | teacher | `proc=None` (orchestrator) |
| [run_2.py](./run_2.py) | `Test2` | student | `CNNCNU` (CNN plus Continual Neural Unit) |
| [run_3.py](./run_3.py) | `Test3` | student | `CNN` (plain baseline) |

---

## The agents (the `proc`)

Student #2, CNN plus Continual Neural Unit ([run_2.py](./run_2.py)):

```python
net = CNNCNU(3, cnu_memories=5, seed=42)   # 3 classes, 5 key-memory units
agent = Agent(proc=net,
    proc_opts={'optimizer': torch.optim.SGD([
                   {'params': net.module[:-2].parameters(), 'lr': 0.0001},   # backbone: slow
                   {'params': net.module[-2:].parameters(), 'lr': 0.005}],   # CNU head: fast
                   lr=0.0001),
               'losses': [torch.nn.functional.binary_cross_entropy]},
    buffer_generated_by_others="all")
out.set_tensor_labels(["albatross", "cheetah", "giraffe"])
```

The `LinearCNU` head is a key-addressable memory layer meant to mitigate catastrophic forgetting during
sequential teaching. Note the two learning-rate groups: slow backbone, fast head.

Student #3, plain CNN baseline ([run_3.py](./run_3.py)): the identical network with a plain
`Linear(2048, 3)` head and a single SGD group (`lr=0.0025`). This is the control: comparing it to #2 is
the whole point of running both.

I/O for both students: input one RGB image resized to 32x32 (`data_type="img"`); output a 3-logit
tensor labeled `["albatross","cheetah","giraffe"]`; loss is `binary_cross_entropy` (paired with a final
sigmoid).

---

## The data streams

Defined in [`src/world.py`](./src/world.py), sourced from [`data/animals`](../../data/animals)
(ImageNet images). Each group is an `ImageFileStream` plus a matching `LabelStream`, all private
(`public=False`):

| Group | CSV | Rows | Role |
|---|---|---|---|
| `albatross` | `c1_skip_10i.csv` | 40 | lecture 1, becomes teacher's `recorded2` |
| `cheetah` | `c2_skip_10i.csv` | 40 | lecture 2, becomes teacher's `recorded3` |
| `giraffe` | `c3_skip_10i.csv` | 40 | lecture 3, becomes teacher's `recorded4` |
| `all` | `first3c_10i.csv` | ~28 | mixed exam, becomes teacher's `recorded1` |

---

## The behavior state machines

_Every action named here is documented in the [Actions and Behaviors reference](../../behaviors/README.md)._

Generated by `create_behav_files()`; saved to [`src/teacher.json`](./src/teacher.json) and
[`src/student.json`](./src/student.json). Templates reused: `engage_by_role`,
`teach-playlist_eval-recorded1`, `listening_to_teacher`.

Teacher, in four phases (each action links to its [reference](../../behaviors/README.md) entry):

1. Snapshot: `record` the `all`, `albatross`, `cheetah`, `giraffe` streams into `recorded1..4`.
2. Recruit: the `engage_by_role` template with `<roles_to_engage>` = `student`.
3. Teach and exam: `set_pref_streams([recorded2,3,4])`, loop `learn` per class (one `learn` per
   lecture, 40 samples), then `process` over `recorded1`, then `evaluate` plus
   `compare_eval(cmp="<=", thres=0.65)`.
4. Reward: `suggest_badges_to_world` and `suggest_role_to_world("teacher")` for the passers in
   `<valid_cmp>`.

Student: `engage(acceptable_role="teacher")` then `teacher_engaged`, reacting to `learn` / `process`,
returning home on `disengage`.

Every action here is a built-in: this world writes no custom Python actions at all. Its `WAgent`
classes are empty `class WAgent(Agent): pass`. The full meaning of each action is in the
[Actions reference](../../behaviors/README.md).

---

## How to run it

Four terminals, world first:

```bash
python run_w.py     # node "AnimalSchool" (Test1 = world master / teacher)
python run_1.py     # node "Test1": teacher (proc=None)
python run_2.py     # node "Test2": student (CNN plus CNU)
python run_3.py     # node "Test3": student (plain CNN)
```

Or from the repo root: `python run_asynch.py animal_school`.

What to expect: the teacher records the four snapshots, recruits both students, teaches albatross then
cheetah then giraffe (40 samples each), runs the mixed 30-sample exam, and grades. Students with exam
error at most 0.65 get the badge, are promoted to `teacher`, and are disengaged. Compare how the CNU
student (`Test2`) fares against the plain CNN (`Test3`) after sequential teaching.

---

## Key takeaways

1. Class-incremental learning via playlists: `set_pref_streams`, `next_pref_stream`,
   `check_pref_stream` sequence single-class streams into a curriculum, the natural place to observe
   forgetting.
2. Swap the head, change the behavior: `CNNCNU` versus `CNN` is a controlled comparison of forgetting
   resistance with everything else held constant.
3. Roles are earned: passing the exam triggers a badge and promotion to teacher, growing the society of
   teachers.
4. You can build a rich world with zero custom actions: composition of built-in actions and templates
   is often enough.

Next: [`social_learning`](../social_learning) scales this to peer teaching on MNIST with an isolated
control group; [`class_incremental_learning`](../class_incremental_learning) makes the forgetting
experiment explicit.

<sub>Part of the [UNaIVERSE examples](../../README.md). Action names are explained in the [Actions reference](../../behaviors/README.md).</sub>
