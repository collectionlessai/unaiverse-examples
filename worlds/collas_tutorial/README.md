# CoLLAs 2026 Tutorial World: a Continual Learning Classroom

This world was built for the tutorial **"Lifelong Learning in Peer-to-Peer Communities of Human and AI Agents"**
(Stefano Melacci, Tommaso Guidi, Christian Di Maio) at [CoLLAs 2026](https://lifelong-ml.cc), as a hands-on example
of a continual learning World in [UNaIVERSE](https://unaiverse.io): a class-incremental setup where models learn
over a live stream, inside a community of agents that join and leave — with humans participating as peers, not
supervisors.

## What happens in this world

A **teacher** runs a classroom that loops forever:

1. 📚 **Lectures** — three lectures, each streaming pictures of two new categories (named as cartoon creatures to make it look less trivial - hey, we are in the context of a tutorial not of a competition :)) together
   with their names: six classes in total, appearing incrementally over time (Class Incremental Learning).
2. 📝 **Exam** — the teacher streams unseen pictures and collects the students' predictions, scoring each student
   and updating a per-student quality index.
3. 🙋 **Feedback** — the teacher asks for help on *unlabeled* pictures; when high-quality students agree on a
   category, the picture is added to the corresponding lecture material for the next round.

**Students** join, get taught, get examined, get consulted. An AI student can host any PyTorch model (the provided
runners use a frozen pretrained backbone with a continually-adapted head based on [Continual Neural Units (CNUs)](https://dl.acm.org/doi/10.1007/978-3-031-70344-7_20)); a **human** joins exactly the same way,
sees the same lectures, and answers the same exam and feedback requests through simple forms.

## Files

| File | Purpose                                                                                                                                         |
|---|-------------------------------------------------------------------------------------------------------------------------------------------------|
| `run_world.py` | The world node (hosts the classroom, assigns roles).                                                                                            |
| `run_teacher.py` | The teacher agent (world master; owns the image streams).                                                                                       |
| `run_student1.py`, `run_student2.py` | Two AI students (frozen backbone + continual neural unit-based head, see [the CNU paper](https://dl.acm.org/doi/10.1007/978-3-031-70344-7_20)). |
| `src/` | World definition: roles, behaviors (HSMs), teacher/student logic, stats.                                                                        |
| `data/` | Lecture, exam, and feedback images.                                                                                                             |

## How to run

Launch in this order (in different terminal sessions), 
waiting for each node to be up (before doing this: register at [unaiverse.io](https://unaiverse.io)):

```bash
python3 run_world.py
```

```bash
python3 run_teacher.py
```

```bash
python3 run_student1.py
```

```bash
python3 run_student2.py
```

Join as a **human student** from the UNaIVERSE web at [unaiverse.io](https://unaiverse.io). If you like you can also
do the same thing using another terminal:

```bash
python3 ../../lonewolves/run_human.py --world CoLLAsTutorial
```

Notes:

- The teacher is recognized as world master by its node name (see `world_masters_node_names` in `run_world.py`);
  adapt the node names to your own account if you replicate the setup.
- In the teacher terminal, hit the **space bar** to pause the classroom (it finishes the current activity first);
  hit it again to resume.
- The world node packs and ships the code in `src/` to every joining agent: after editing anything in `src/`,
  restart `run_world.py` (and then the other nodes).
- Images added by the feedback-driven augmentation are cleaned up automatically at the next world start.
