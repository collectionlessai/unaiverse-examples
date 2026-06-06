# 🤝 Social Learning

*Does talking to peers help you learn? A runnable experiment.*

> This world is an actual controlled experiment. Several students learn MNIST from a teacher; the best
> student of each round is promoted to teach the others by labeling fresh digits for them. A separate
> isolated student never joins those peer lectures (the control group). Compare their final test errors
> and you have answered: does social interaction improve learning?
>
> Action names (`set_pref_streams`, `evaluate`, `compare_eval`, `send_subscribe`, ...) are explained
> inline and in full in the [Actions and Behaviors reference](../../behaviors/README.md).

---

## The big idea

A teacher teaches MNIST digits. Three students learn; the best one becomes teacher and labels fresh
digits for the others. Does social interaction improve learning?

The mechanism:

1. A teacher (no model of its own) owns MNIST and runs lecture/exam rounds, streaming labeled batches to
   students (supervised online learning), then exams on a held-out set.
2. After each exam it picks the best student.
3. The best student is promoted: it runs inference on a pool of the teacher's unlabeled digits and
   publishes its own predicted labels as supervision for its peers (a form of peer co-training or
   distillation). Non-isolated peers learn from that possibly-noisy peer supervision.
4. Isolated students skip the peer step entirely: they only learn from the teacher.

The `teach` action's docstring states the social step precisely:

> "Best-student social-teaching step: run one inference on the teacher's unlabeled data ... and relay
> the input image plus our predicted label into our pubsub `best_student_stream`, published under
> `relay_uuid` (the UUID the other students read while learning)."

And `student_isolated.py`:

> "The isolated student never participates in the social step, so it uses the plain built-in 'process'
> action (grandfather call) instead of the student's relay-augmented one."

Each student self-evaluates on the full MNIST test set when class ends, recording `full_test_err`, which
is the metric the dashboard plots to answer the question.

---

## The story, step by step

The teacher's behavior loops: find and engage students, lecture rounds, best-student selection, social
round, repeat.

1. Engage students of roles `student` and `student_isolated`.
2. Set the lecture playlist (`set_pref_streams` over `teach_0` to `teach_{rounds-1}`).
3. Teach a round. `shuffle_round_datasets` reshuffles, then the teacher sends `learn` to all students
   (`stdin` images, `stdtar` labels). Students learn online from batched tensors and supervisions.
4. Exam. Send `process` over the private `eval` set; students run inference.
5. Correct exams. `evaluate(how="max")` then `compare_eval(cmp="min", thres=0.5)` selects the single
   best student (`cmp="min"` picks the lowest error among those under the threshold).
6. Badge. `manage_best_of_class` records the best error and awards an intermediate badge.
7. Social round (the key step). `social_round` subscribes the other non-isolated students to the best
   student's `best_student_stream`, asks them to `learn_from_student` on it, and asks the best student to
   `teach` over the teacher's `unlabeled` images. The best student labels those digits and relays
   image plus label into its pubsub stream, where peers consume them as supervision. Isolated students
   are excluded.
8. Next round or finish, then on `disengage` each non-isolated student computes its full-test-set error
   (`full_test_err`).

---

## Roles and how they are assigned

[`src/world.py`](./src/world.py): first master to `teacher`; non-masters default to `student` but honor
a `role_preference` (the only special value is `student_isolated`):

```python
if 'tmp_role_preference' in profile.get_dynamic_profile():
    pref = profile.get_dynamic_profile()['tmp_role_preference']
    return "student_isolated" if pref == "student_isolated" else "student"
```

`world_masters_node_names=["DigitClassifier1"]`:

| Script | Node | Role | Model |
|---|---|---|---|
| [run_1.py](./run_1.py) | `DigitClassifier1` | teacher | `proc=None` |
| [run_2.py](./run_2.py) | `DigitClassifier2` | student | `CNN(seed=42)`, Adam lr 0.001 |
| [run_3.py](./run_3.py) | `DigitClassifier3` | student | `CNN(seed=52)`, Adam lr 0.0025 |
| [run_4.py](./run_4.py) | `DigitClassifier4` | student_isolated (control) | `CNN(seed=62)`, Adam lr 0.005 |
| [run_demo.py](./run_demo.py) | `Test1` | student (diagnostic) | joins ~90s; prints error before vs after |

Different seeds and learning rates make the best-student selection meaningful.

---

## The agents (the `proc`)

All students wrap the same class:

```python
net = CNN(d_dim=10, in_channels=1, seed=<42|52|62>)
proc_inputs =[StreamType(data_type="tensor", tensor_shape=(None,1,28,28), tensor_dtype=torch.float32, private_only=True)]
proc_outputs=[StreamType(data_type="tensor", tensor_shape=(None,), tensor_dtype=torch.long, private_only=True,
                         proc_to_stream_transforms=lambda x: torch.argmax(x, dim=1))]
proc_opts   ={'optimizer': torch.optim.Adam(net.parameters(), lr=<...>),
              'losses':    [torch.nn.functional.cross_entropy]}
```

The teacher is `proc=None` with `buffer_generated_by_others="one"` (so it can ingest the best student's
relayed predictions).

student versus student_isolated: the model is identical. The difference is purely behavioral, the
isolated student does not create a `best_student_stream`, uses plain `process`, and is never targeted by
`social_round`.

---

## The data streams

All MNIST data lives on the teacher (built in [`src/teacher.py`](./src/teacher.py) `accept_new_role`),
all private, with disjoint index ranges so splits never overlap:

| Stream group | Source | Size | Purpose |
|---|---|---|---|
| `eval` (images and labels) | MNIST test | 20 per class | exam set |
| `teach_0`, `teach_1` (images and labels) | MNIST train | 50 per class each | lecture rounds |
| `unlabeled` (images only) | MNIST train (offset) | 100 per class | digits the best student labels for peers |

The best student also creates a pubsub `best_student_stream` (images and labels) in its
`accept_new_role`: the channel it publishes predicted supervision into and peers subscribe to. The
isolated student deliberately does not create it.

---

## The behavior state machines

_Every action named here is documented in the [Actions and Behaviors reference](../../behaviors/README.md)._

Built in `create_behav_files()` and saved to [`teacher.json`](./src/teacher.json),
[`student.json`](./src/student.json), [`student_isolated.json`](./src/student_isolated.json).

Teacher: reuses `engage_by_role` (with `<roles_to_engage>` = `["student","student_isolated"]`) and
`teach-eval-playlist`, then overrides the template's `best_found` transitions in code to insert the
social round:

```python
behav.transitions["best_found"] = {}
behav.add_transit("best_found", "best_teaching", action="social_round")
behav.add_transit("best_found", "change_lecture", action="nop")
behav.add_transit("best_teaching", "change_lecture", action="all_asks_done")
behav.add_teleport("best_teaching", "change_lecture", action="nop",
                   args={"delay": "<others_learn_exam_timeout>"})   # timeout escape
```

Key wildcards: `<learn_steps>`=16, `<eval_steps>`=7, `<cmp_thres>`=0.5,
`<others_learn_exam_timeout>` is about 9.9.

Student: `init` to `teacher_engaged`, with `learn` (follow a lecture) to `finished_learning` to
`process` (exam); `subscribe` to `listening_to_best_student` to `learn_from_student`; and a `teach`
self-loop (only the best student ever fires it). `student_isolated.json` is the same machine; the
difference is in the Python class, not the JSON.

---

## Custom actions (the heart of this world)

_These are custom methods, built like (and used alongside) the built-in actions in the [Actions and Behaviors reference](../../behaviors/README.md)._

Teacher ([src/teacher.py](./src/teacher.py)):

- `social_round`: the experiment's core. Find the best student, subscribe the other non-isolated
  students to its stream, then fan out two interactions: ask peers to `learn_from_student` (capturing
  `relay_uuid`) and ask the best student to `teach` with that `relay_uuid`.
- `on_asked_done` and `all_asks_done`: completion bookkeeping that gates the transition out of
  `best_teaching`.
- `shuffle_round_datasets`, `evaluate` (stores per-peer exam error), `manage_best_of_class` (badge).

Student ([src/student.py](./src/student.py)):

- `accept_new_role`: adds the pubsub `best_student_stream`.
- `learn_from_student`: a renaming of `learn`, so the lecture's `learn` transition cannot fire it.
- `teach(relay_uuid)`: runs inference on the teacher's unlabeled image, then republishes image plus
  prediction into its `best_student_stream` under `relay_uuid`. This is the actual peer teaching.
- `disengage`: overloaded to compute `full_test_err` on the full MNIST test set (the outcome metric).

Student isolated ([src/student_isolated.py](./src/student_isolated.py)): subclasses the student but
calls the grandfather `Agent` methods, so no `best_student_stream` and plain `process`.

The renaming of `learn` to `learn_from_student` and the `relay_uuid` plumbing are the two clever tricks
worth studying: they let one agent's output become another agent's training target without
state-machine ambiguity or UUID collisions.

---

## How to run it

Easiest (from the repo root, launches the world plus all `run_N.py`):

```bash
python run_asynch.py [-l] social_learning     # -l enables clean logging
```

Or by hand, world first:

```bash
python run_w.py    # world "DigitSocialLearning" (master = DigitClassifier1)
python run_1.py    # teacher
python run_2.py    # student (seed 42)
python run_3.py    # student (seed 52)
python run_4.py    # student_isolated (control, seed 62)
```

What to expect: engage, then 2 lecture rounds (learn 16, exam 7), then best-student selection, then a
social round where the best student labels 1000 unlabeled digits for the non-isolated peers, then
repeat. The world dashboard ([`src/stats.py`](./src/stats.py)) plots exam error and full test error per
student, which is where you compare the isolated student against the social ones.

[`run_demo.py`](./run_demo.py) is a standalone probe: it measures a fresh student's test error before
joining and after 90 seconds of living, printing both, to show participation lowered the error.

---

## Key takeaways

1. Roles plus state machines define the experiment. Behavior is data (JSON), composed from templates and
   customized in code (`behav.transitions["best_found"] = {}` then re-`add_transit`).
2. Agent-to-agent supervision via pubsub plus relay UUIDs: the best student publishes predictions; peers
   subscribe and learn, the mechanism for one agent's output to train another.
3. Designing a controlled experiment with a baseline: `student_isolated` is the no-interaction control
   (same model and curriculum, no peer lectures), so comparing `full_test_err` answers the research
   question.
4. World, Agent, and Stats cooperate to make the experiment observable: disjoint private data splits, an
   overridden `disengage` for the outcome metric, and a custom Plotly dashboard.

Builds on [`animal_school`](../animal_school) (promotion to teacher) and the school worlds' teach/exam
loop.

<sub>Part of the [UNaIVERSE examples](../../README.md). Action names are explained in the [Actions reference](../../behaviors/README.md).</sub>
