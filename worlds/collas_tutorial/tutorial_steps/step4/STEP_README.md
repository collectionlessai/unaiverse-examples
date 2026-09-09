# Step 4 - The full classroom (AI agents only)

Every action is now **implemented**: this is a fully working continual-learning classroom for AI students.

- Lectures: the teacher streams image+label pairs (`teach` sends a `learn` interaction pointing the students'
  processors at the lecture streams).
- Exam: `hand_out_exam` sends a `process` interaction; `on_data` collects the students' predictions from their
  processor streams; `evaluate_results` scores them and updates a per-student quality index.
- Feedback: unlabeled images go out, answers from high-quality students are aggregated (`augment_lectures`) and
  the agreed ones are added to the lecture data for the next round.
- Plus the operational details: the space-bar pause in the teacher terminal, the no-students recovery, the
  settle waits for late responses.

Still left out: the UAI blocks for human participants (step 5) and the stats (step 6).

**Run it**: world, teacher, and the two AI students - full rounds of lectures, exams (watch the scores and the
stars), feedback and lecture augmentation, forever.
