# Step 3 - Actions and behaviors (HSMs)

The full **Hybrid State Machines** appear, together with the (still empty) actions they reference.

- `src/world.py` now builds the complete teacher HSM (init -> in_class -> lectures -> exam -> feedback -> init)
  and the complete student HSM (connect to a teacher, then react to `learn`/`process`/`print` interactions),
  with states, transitions, waiting times, timeouts and teleports.
- `src/teacher.py` declares every action used by the teacher HSM (`teach`, `hand_out_exam`, `on_data`, ...) as an
  **empty stub returning True**; `src/student.py` declares its `print` action and the `one_at_random` filter.

**Run it**: the world generates `teacher.json` / `student.json` (and the PDFs of the machines) from the code
above - open them! With a student connected, the teacher's HSM visibly walks through its states (the state
messages print in sequence); since every action succeeds instantly and no data is sent, it keeps looping
through the lecture states forever. The skeleton moves - the next step gives it something to do.
