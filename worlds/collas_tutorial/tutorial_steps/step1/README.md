# Step 1 - Skeleton

The bare bones of a UNaIVERSE World. What is here:

- `src/world.py` - the `WWorld` class: it assigns a **role** to every joining agent (`assign_role`: the world
  master becomes `teacher`, everybody else `student`) and it creates the **behavior files** (`teacher.json`,
  `student.json`). For now each behavior is just a welcome message and a single idle state.
- `src/teacher.py`, `src/student.py` - the two role classes, **empty** for now.
- `src/stats.py` - an **empty** stats class, not used yet (the world will create it in step 6).
- The usual runners (the `data/` folder of the main world is shared by all the steps, not used yet).

**Run it** (world, then teacher, then students - as in the final world): every agent joins, receives its role,
prints its welcome message... and does nothing else. That is a complete, running World already: roles, join
handshake, code shipping from world to agents all happen with ~40 lines of world code.
