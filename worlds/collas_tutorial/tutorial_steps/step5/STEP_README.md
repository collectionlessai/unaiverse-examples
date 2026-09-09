# Step 5 - Humans as peers (UAI)

Same world as step 4, plus the **UAI components** that make it friendly for human participants:

- `hook_before_sending_sample` (teacher): right before an exam/feedback label sample leaves the node, it is
  replaced by an interactive **form** (a `uai` block with one button per class) - AI students ignore it, humans
  get clickable exercises.
- `on_data` now parses both kinds of answers: a plain class name (AI students) or the UAI form response (humans),
  matching answers to exercises through the form id.
- The student welcome message becomes a UAI block too (title + conference logo).
- The world runner clears feedback-related images, starting from scratch all the time (hey, this is just to illustrate 
  what is going on).

**Run it**: as before, and additionally join as a human (web app, or `run_human.py --world CoLLAsTutorial`):
you attend the same lectures, answer the same exams through buttons, and your feedback counts like anyone's.
