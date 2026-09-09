# Step 6 - Stats (the final world)

The final touch: **per-student statistics**, persisted by the world and shown on its stats page.

- `src/stats.py` now defines the real `WStats`: one dynamic stat (`exam_result`, grouped by the student's
  UNaID), a pruning rule (last 30 exams per student), and a `plot()` method that renders the world's stats
  page as a simple HTML document (last 10 students, quality index and exam history each).
- `src/world.py` now instantiates `WStats` in its constructor and hands it to the world node.
- `src/teacher.py` stores one `exam_result` record per student at the end of `evaluate_results`; the records
  are batched to the world automatically.

This folder is identical to the final world in the parent directory.

**Run it**: after a couple of exam rounds, open the world's stats page: one card per student, quality stars,
and the last exams with their scores.
