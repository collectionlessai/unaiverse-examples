# 📡 Signal School

*Forward (backprop-free) learning of signals, and generalizing the notion of amplitude.*

> The most research-flavored school world. A student learns to reproduce time signals by free-running a
> state-space model, trained online and forward in time, with no backpropagation through time. Then it
> faces a generalization exam on a signal it was never taught.
>
> Action names are explained inline and in full in the
> [Actions and Behaviors reference](../../behaviors/README.md).

---

## The big idea

A teacher streams a family of 1-D time signals; a student must learn to regenerate each signal forward
in time (as a generator/predictor, not by replaying a buffer), is examined per signal, and finally must
generalize the concept of amplitude on a held-out signal.

Why this example is special:

- **Forward learning instead of BPTT.** The student is optimized by `HL` (Hamiltonian Learning), not a
  `torch.optim` optimizer. `HL` carries costates for the hidden state and the weights and integrates
  them forward with an Euler step, updating the model one tick at a time (`local=True`). This is the
  cleanest demonstration in the repo of a genuine forward, lifelong learner.
- **A state-space generator.** The model is `CTBEInitStateBZeroInput`, an antisymmetric oscillatory
  state-space net. The trick: it zeros its running input and encodes everything into the initial hidden
  state (`init_h = B(udu)/sum(udu)`), so once primed by a signal descriptor it free-runs and generates
  the signal from its own dynamics.
- **Measuring generalization, not memorization.** Eight signals vary along three binary axes: waveform
  (smooth sines versus square), frequency (high/low), amplitude (high/low). The teacher teaches 7 and
  holds out `squLfLa` (square, low frequency, low amplitude). It is the low-amplitude twin of a signal
  the student did see, so the final exam asks: did you learn what amplitude means?

---

## The story, step by step

1. The world `SignalSchool` starts; the first master becomes the teacher, others become students.
2. The teacher builds its lecture material. Only upon accepting the `teacher` role does it instantiate
   the eight signal generators as its own private streams (see [`src/teacher.py`](./src/teacher.py)),
   each paired with an `AllHotLabelStream` carrying that signal's symbolic features (its description).
3. Engagement. The teacher recruits the student (`engage_by_role`, `<roles_to_engage>` = `student`);
   the student waits in `teacher_engaged` (the `listening_to_teacher` template).
4. Lectures (a 7-signal playlist, `repeat=4`). For each signal the teacher sends a `learn` request
   (the signal serves as both input and target). The student updates its model online for up to 10000
   samples per lecture. Because of `repeat=4`, rounds 1 to 3 are pure teaching and only the 4th (last)
   round triggers exams, so each signal is taught 3 times and examined once. The teach-versus-exam
   split is decided by `check_pref_stream("not_last_round")` versus `("last_round")`.
5. Per-signal exams. The teacher sends a `process` request (1000 samples); the student free-runs to
   generate the signal. The teacher runs `evaluate(how="mse", re_offset=True)` and
   `compare_eval(cmp="<=", thres=0.2)`: good (pass) or bad (restart teaching). `re_offset=True` realigns
   the generated output's time origin against the target, necessary because a free-running generator may
   start at an arbitrary phase.
6. The amplitude generalization final exam. After the playlist, the teacher asks the student to
   `process` 1000 samples of the never-taught `squLfLa`, then `evaluate` plus
   `compare_eval(cmp="<=", thres=0.2)`: MSE at most 0.2 reaches state `very_good` (it generalized
   amplitude), otherwise `not_good`.

---

## Roles and how they are assigned

[`src/world.py`](./src/world.py): first world master to `teacher`, everyone else to `student`.
`world_masters_node_names=["Test1"]`, so [`run_1.py`](./run_1.py) (`Test1`) is the teacher and
[`run_2.py`](./run_2.py) (`Test2`) is the student.

---

## The agents (the `proc`)

Teacher ([run_1.py](./run_1.py)): `Agent(proc=None, buffer_generated_by_others="all",
merge_flat_stream_labels=True)`. No network; it generates and streams signals and orchestrates. Its
`accept_new_role` registers the 8 signal and label streams.

Student ([run_2.py](./run_2.py)), a real state-space model:

```python
net = CTBEInitStateBZeroInput(u_shape=(1,), d_dim=6, y_dim=1, h_dim=1000,
                              local=True, delta=0.1, cnu_memories=20, seed=42)
agent = Agent(proc=net,
    proc_opts={'optimizer': HL(net.module, gamma=1., theta=0.2, beta=0.01,
                               reset_neuron_costate=False, reset_weight_costate=False, local=True),
               'losses': [torch.nn.functional.mse_loss]})
```

- `h_dim=1000` gives 500 learnable rotation blocks; `delta=0.1` matches the signal generators'
  timestep; `cnu_memories=20` is a `LinearCNU` readout keyed on the descriptor; `d_dim=6` matches the 6
  distinct feature tokens `{3sin, square, hf, lf, ha, la}`.
- `HL` parameters: `gamma` weights the loss term in the Hamiltonian, `theta` is costate decay, `beta`
  scales the weight update; `local=True` selects the local (forward) update rule.
- I/O: inputs are the signal value `u` `(None,1)` and descriptor `du` `(None,6)`; output is the
  reproduced value `(None,1)`; loss is plain MSE.

---

## The data streams (the eight signals)

There is no `add_stream` in the world: the signal streams live on the teacher and are created in
[`src/teacher.py`](./src/teacher.py) `accept_new_role` only when the node actually holds the `teacher`
role. All have `delta=0.1` and are private:

| Signal | Waveform | Freq | Amp |
|---|---|---|---|
| `smoHfHa`, `smoHfLa`, `smoLfHa`, `smoLfLa` | sum of 3 sines | hi/lo | hi/lo |
| `squHfHa`, `squHfLa`, `squLfHa` | square | hi/lo | hi/lo |
| `squLfLa` (held out) | square | low | low |

Amplitude high/low is a 2x scaling of the coefficients; the held-out `squLfLa` is the low-amplitude
twin of the taught `squLfHa`, which is the crux of the generalization test.

---

## The behavior state machines

_Every action named here is documented in the [Actions and Behaviors reference](../../behaviors/README.md)._

Built in `create_behav_files()` from three templates: `engage_by_role`,
`teach-playlist_eval-playlist` (the teach-then-exam loop), and `listening_to_teacher`.

Teacher highlights (actions explained in the [reference](../../behaviors/README.md)):

- recruit (`engage_by_role`), then `set_pref_streams([7 signals], repeat=4)` to lay the curriculum down
  4 times.
- teach loop: `check_pref_stream("not_last_round")` keeps teaching; `"last_round"` triggers the exam.
- exam: `process` for 1000 samples, then `evaluate(how="mse", re_offset=True)` and
  `compare_eval(cmp="<=", thres=0.2)`.
- generalization tail (hand-written, not from the template): `process` over `<agent>:squLfLa` for 1000
  samples, then `evaluate` plus `compare_eval` reaching `very_good` or `not_good`.
- wildcards: `<learn_steps>`, `<eval_steps>=1000`, `<cmp_thres>=0.2`.

Student: `engage(acceptable_role="teacher")` then `teacher_engaged`, reacting to `learn` / `process`,
home on `disengage`.

This world defines no custom action methods; only the teacher overrides `accept_new_role` to register
its signal streams. Everything else is a built-in action.

---

## How to run it

```bash
python run_w.py     # node "SignalSchool" (Test1 = master / teacher)
python run_1.py     # node "Test1": teacher (proc=None, owns the signals)
python run_2.py     # node "Test2": student (CTBE state-space model plus HL)
```

Or from the repo root: `python run_asynch.py signal_school`. Nodes run at 100 Hz, `hidden=True`.

What to expect: teaching of each of the 7 signals 3 times (10000-sample `learn` requests), per-signal
`process` plus `evaluate` exams (MSE at most 0.2), and finally the held-out `squLfLa` exam ending in
`very_good` (amplitude generalized) or `not_good`.

---

## Key takeaways

1. Forward, online, backprop-free learning is first-class: the `HL` optimizer with `local=True` updates
   the model tick by tick, no BPTT.
2. State-space models as generators: prime the initial hidden state from a descriptor, zero the running
   input, and free-run to reproduce a signal.
3. Curriculum plus held-out exam equals measurable generalization: teach 7, grade the 8th to isolate
   the amplitude concept; `repeat=4` plus `check_pref_stream("last_round")` separates teaching from
   exams.
4. Streams can be owned by a role and created on demand: the teacher builds its signal streams in
   `accept_new_role`, and playlist references like `<agent>:smoHfHa` resolve at runtime to the
   role-holder's streams.

Compare with [`cat_library`](../cat_library) (online token reproduction with an RNN) and
[`animal_school`](../animal_school) (online image classification).

<sub>Part of the [UNaIVERSE examples](../../README.md). Action names are explained in the [Actions reference](../../behaviors/README.md).</sub>
