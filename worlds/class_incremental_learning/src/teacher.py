"""
 █████  █████ ██████   █████           █████ █████   █████ ██████████ ███████████    █████████  ██████████
░░███  ░░███ ░░██████ ░░███           ░░███ ░░███   ░░███ ░░███░░░░░█░░███░░░░░███  ███░░░░░███░░███░░░░░█
 ░███   ░███  ░███░███ ░███   ██████   ░███  ░███    ░███  ░███  █ ░  ░███    ░███ ░███    ░░░  ░███  █ ░
 ░███   ░███  ░███░░███░███  ░░░░░███  ░███  ░███    ░███  ░██████    ░██████████  ░░█████████  ░██████
 ░███   ░███  ░███ ░░██████   ███████  ░███  ░░███   ███   ░███░░█    ░███░░░░░███  ░░░░░░░░███ ░███░░█
 ░███   ░███  ░███  ░░█████  ███░░███  ░███   ░░░█████░    ░███ ░   █ ░███    ░███  ███    ░███ ░███ ░   █
 ░░████████   █████  ░░█████░░████████ █████    ░░███      ██████████ █████   █████░░█████████  ██████████
  ░░░░░░░░   ░░░░░    ░░░░░  ░░░░░░░░ ░░░░░      ░░░      ░░░░░░░░░░ ░░░░░   ░░░░░  ░░░░░░░░░  ░░░░░░░░░░
           A Collectionless AI Project (https://collectionless.ai)
           Registration/Login: https://unaiverse.io
           Code Repositories:  https://github.com/collectionlessai/
           Main Developers:    Stefano Melacci (Project Leader), Christian Di Maio, Tommaso Guidi
"""

import datetime
import os
import random

import numpy as np
import torch
from torch.utils.data import DataLoader, Subset
from torchvision import datasets, transforms
from unaiverse.agent import Agent
from unaiverse.clock import clock
from unaiverse.interaction import Interaction
from unaiverse.streams import Dataset, Stream
from unaiverse.utils.misc import prepare_app_dir


######### Helper functions for loading and preparing MNIST data — used by the teacher agent to serve lessons and exams. #########
def load_mnist(data_dir: str):
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,)),
    ])
    train = datasets.MNIST(
        root=os.path.join(data_dir, "mnist_data"),
        train=True,
        download=True,
        transform=transform,
    )
    test = datasets.MNIST(
        root=os.path.join(data_dir, "mnist_data"),
        train=False,
        download=True,
        transform=transform,
    )
    return train, test


def build_class_index(dataset) -> dict:
    class_to_indices: dict = {}
    for idx, label in enumerate(np.asarray(dataset.targets)):
        class_to_indices.setdefault(int(label), []).append(idx)
    return class_to_indices


def subsample_class(dataset, n_per_class: int, cls: int, offset: int = 0) -> Subset:
    cls_indices = np.where(dataset.targets.cpu().numpy() == cls)[0][
        offset : offset + n_per_class
    ].tolist()
    random.shuffle(cls_indices)
    return Subset(dataset, cls_indices)


def class_dataloader(
    dataset, class_to_indices: dict, classes, batch_size: int = 1, shuffle: bool = True
) -> DataLoader:
    if isinstance(classes, int):
        classes = [classes]
    indices = [i for cls in classes for i in class_to_indices.get(int(cls), [])]
    return DataLoader(Subset(dataset, indices), batch_size=batch_size, shuffle=shuffle)


##############################################################################################################################


class WAgent(Agent):
    """Teacher agent for task-incremental learning on MNIST.

    Sequence driven by teacher.json (HSM):
      1. Welcoming   — wait for students to connect.
      2. Teaching    — send one digit class at a time (0 → 9).
      3. Evaluating  — examine all students and score them.

    Each action returns True (HSM advances) or False (HSM retries next tick).
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # ── HSM state ─────────────────────────────────────────────────────
        # Actions are called across multiple ticks, so any value that must
        # survive between calls must live on self — not as a local variable.
        
        self._students = {}  # peer_id → {exams, lessons, evaluations, profile}
        self._timers = {
            "welcoming": {
                "start": None,
                "timeout": datetime.timedelta(seconds=90).total_seconds(),
            },
            "exam": {
                "start": None,
                "timeout": datetime.timedelta(seconds=20).total_seconds(),
            },
        }
        self._best_student = None # peer_id of the current top performer (used in building_evaluation)
        self._current_intent = None  # "teach" or "evaluate"
        self._current_lesson = -1  # -1 = no lesson taught yet; 0–9 = last class taught
        self._current_exam = None  # dict holding the active exam state

        # ── Dataset parameters ────────────────────────────────────────────
        self._eval_per_class = 20  # test images sent per class during exam
        self._teach_per_class = 50  # train images sent per class during lesson
        self._batch_size = 1  # one sample at a time → simplest interaction model

        # ── Load MNIST and build class→index maps ─────────────────────────
        data_dir = os.path.join(prepare_app_dir(), "incremental_learning")
        train_dataset, test_dataset = load_mnist(data_dir)
        self.train_dataset = train_dataset
        self.test_dataset = test_dataset

        # Fast O(1) lookup: given a class label, which dataset indices belong to it?
        self._train_class_to_indices = build_class_index(train_dataset)
        self._test_class_to_indices = build_class_index(test_dataset)

        # Pre-slice each class into a fixed subset so every student sees
        # exactly the same images in the same order each run.
        eval_sets = {
            cls: subsample_class(test_dataset, self._eval_per_class, cls)
            for cls in range(10)
        }
        teach_sets = {
            cls: subsample_class(train_dataset, self._teach_per_class, cls)
            for cls in range(10)
        }

        # Ground-truth labels per class — used later to score predictions without a manifest.
        self._eval_indices_by_class = {
            cls: list(s.indices) for cls, s in eval_sets.items()
        }
        self._eval_labels_by_class = {
            cls: [int(test_dataset.targets[i]) for i in s.indices]
            for cls, s in eval_sets.items()
        }

        # ── Register streams (platform API) ───────────────────────────────
        # A Stream is a named data pipe owned by this agent.
        # Students reference streams by name when the teacher sends them an interaction.
        #
        # Dataset(data, index=0) → extracts the image tensor (item 0 of each (image, label) tuple).
        # Dataset(data, index=1) → extracts the label.
        # shape=(None, 1, 28, 28) → batch of grayscale 28×28 images (None = variable batch size).
        # public=False → stream is visible only within this world, not to lone-wolf agents.
        #
        # Passing a dict {cls: Subset} as data → the stream cycles across all classes in one pipe.
        self._test_stream = self.add_streams([
            Stream.create(
                group="eval",
                name="images_eval",
                public=False,
                stream=Dataset(
                    eval_sets,
                    shape=(None, 1, 28, 28),
                    index=0,
                    batch_size=self._batch_size,
                ),
            )
        ])

        # One stream-group per class: images and labels in separate streams.
        # Keeping them separate lets the platform auto-route images → stdin and labels → stdtar
        # when we send a "learn" interaction (see init_lesson below).
        self._train_streams = []
        for cls in range(10):
            group = f"teach_class_{cls}"
            streams = self.add_streams([
                Stream.create(
                    group=group,
                    name=f"images_train_{cls}",
                    public=False,
                    stream=Dataset(
                        teach_sets[cls],
                        shape=(None, 1, 28, 28),
                        index=0,
                        batch_size=self._batch_size,
                    ),
                ),
                Stream.create(
                    group=group,
                    name=f"labels_train_{cls}",
                    public=False,
                    stream=Dataset(
                        teach_sets[cls],
                        shape=(None,),
                        index=1,
                        batch_size=self._batch_size,
                    ),
                ),
            ])
            self._train_streams += streams

    # ── Helpers ────────────────────────────────────────────────────────────

    def get_class_dataloader(
        self, classes, train: bool = True, batch_size: int = 1, shuffle: bool = True
    ):
        """Return a DataLoader for the requested class(es) — useful for local debugging."""
        dataset = self.train_dataset if train else self.test_dataset
        class_to_indices = (
            self._train_class_to_indices if train else self._test_class_to_indices
        )
        return class_dataloader(dataset, class_to_indices, classes, batch_size, shuffle)

    def set_active_classes(self, classes, batch_size: int = 1):
        """Convenience: set train/test loaders for a subset of classes."""
        self._train_loader = self.get_class_dataloader(
            classes, train=True, batch_size=batch_size, shuffle=True
        )
        self._test_loader = self.get_class_dataloader(
            classes, train=False, batch_size=batch_size, shuffle=False
        )

    # ── Utilities (hands-on helpers) ───────────────────────────────────────

    def compute_accuracy(self, predictions: list, ground_truth: list) -> dict:
        """Compare two flat lists and return correct / total / accuracy.

        Usage:
            result = self.compute_accuracy(predicted_labels, true_labels)
            print(result["accuracy"])   # 0.85
        """
        np_predictions = np.array(predictions)
        np_ground_truth = np.array(ground_truth)
        accuracy_per_class = {
            f"peer_acc_per_class_{cls}": np_predictions[np_ground_truth == cls] == cls / self._eval_per_class
            for cls in np.unique(np_ground_truth)
        }
        return {
            "accuracy": int(np.sum(np_predictions == np_ground_truth)) / len(predictions),
            **accuracy_per_class,
        }

    def ground_truth_for_classes(self, classes: list) -> list:
        """Return the ordered list of true labels for a set of classes.

        Useful when you need to score predictions manually:
            gt = self.ground_truth_for_classes([0, 1, 2])
        """
        return [label for cls in classes for label in self._eval_labels_by_class[cls]]

    def classes_taught_so_far(self) -> list:
        """Return the list of class indices taught so far (empty if no lesson yet)."""
        return (
            list(range(self._current_lesson + 1)) if self._current_lesson >= 0 else []
        )

    def all_students_finished(self) -> bool:
        """True once every student in the current exam has sent back their predictions."""
        if not self._current_exam:
            return False
        return (
            self._current_exam["finished_students"]
            >= self._current_exam["received_by_student"].keys()
        )

    def exam_scores(self) -> dict:
        """Return the scores dict from the last completed exam, keyed by student peer_id.

        Each value: {"correct": int, "total": int, "accuracy": float}
        Returns empty dict if no exam has been scored yet.
        """
        if not self._current_exam:
            return {}
        return self._current_exam.get("scores", {})

    async def on_tick(self):
        """Called every clock cycle. Keeps the student roster in sync even when no
        interaction is happening — disconnected peers are pruned automatically.

        handshake_completed=True → student has exchanged profiles with us,
        its processor signature is known, so it is safe to send data to it.
        """
        await super().on_tick()
        connected = set(self.get_agents_by_role("student", handshake_completed=True))
        for s in connected:
            if s not in self._students:
                self._students[s] = {"exams": [], "lessons": [], "evaluations": []}
        for s in list(self._students.keys()):
            if s not in connected:
                del self._students[s]
        return True

    # ── Actions ────────────────────────────────────────────────────────────

    async def welcoming(self):
        """Wait until ≥3 students have joined OR 90 s have elapsed — whichever comes first."""
        if self._timers["welcoming"]["start"] is None:
            self._timers["welcoming"]["start"] = (
                clock.get_time()
            )  # start timer on first call

        elapsed = clock.get_time() - self._timers["welcoming"]["start"]
        timeout = elapsed > self._timers["welcoming"]["timeout"]
        enough_students = len(self._students) >= 3

        if timeout or enough_students:
            self._timers["welcoming"]["start"] = None  # reset for potential next cycle
            return True
        return False

    async def should_teach_or_evaluate(self):
        """Set the intent flag used by building_lesson / building_evaluation.
        _current_lesson goes -1 → 0 → 1 → ... → 9 (10 classes total, 0–9).
        Once it reaches 9, we switch to evaluate."""
        self._current_intent = "teach" if self._current_lesson < 9 else "evaluate"
        return True  # always advances — just sets the flag

    async def building_lesson(self):
        """Guard: enter lesson branch only if intent is 'teach'.
        Increments _current_lesson so init_lesson sends the next class."""
        if self._current_intent != "teach":
            return False
        self._current_lesson += 1  # -1→0 on first call, then 0→1→...→9
        return True

    async def building_evaluation(self):
        """Guard: enter evaluation branch only if intent is 'evaluate'."""
        return self._current_intent == "evaluate"

    async def student_finished_exame(self, interaction: Interaction):
        """Callback invoked when a student completes its exam interaction.
        interaction.target is the peer_id of the student that just finished.
        We track finished students so evaulate_exam knows when all are done."""
        if not self._current_exam:
            return False
        student = interaction.target
        if student not in self._current_exam["received_by_student"]:
            return False
        self._current_exam["finished_students"].add(student)
        return True

    async def send_exam(self):
        """Send the evaluation stream to every connected student.

        _send() delivers an async interaction to a target agent:
          action_name → which action to run on the student ("process")
          streams     → which of our streams the student reads as input
                        "stdin"  = model input,  "stdtar" = supervisor signal (empty here)
          callback    → which of OUR methods fires when the student finishes
          num_steps   → how many samples the student consumes before the interaction ends

        Interaction returns a uuid that we store to match replies later.
        If any _send() fails we abort the whole exam (all-or-nothing).
        """
        students = list(self._students.keys())
        seen = self.classes_taught_so_far()
        if not students or not seen:
            return False

        exam_id = f"exam_{int(datetime.datetime.now().timestamp())}"
        self._current_exam = {
            "id": exam_id,
            "seen_classes": seen,
            "received_by_student": {s: [] for s in students},
            "finished_students": set(),
            "scores": {},
            "uuids": [],
        }
        self._timers["exam"]["start"] = clock.get_time()

        for student in students:
            interaction = await self._send(
                action_name="process",
                target=student,
                streams={"stdin": ["images_eval"], "stdtar": [], "stdext": []},
                callback="student_finished_exam",
                num_steps=self._eval_per_class * len(seen),
            )
            if not interaction:
                self._current_exam = None
                return False
            self._current_exam["uuids"].append(interaction.uuid)
        return True

    async def get_samples(self):
        """Poll for predictions from each student (non-blocking, max 20 s window).
        Students write argmax predictions into their output stream; we collect them here.
        get_stream(...).get(requester, uuid) returns None if data is not ready yet."""
        if (clock.get_time() - self._timers["exam"]["start"]) > self._timers["exam"][
            "timeout"
        ]:
            return False  # timeout — stop polling

        for student, uuid in zip(
            list(self._current_exam["received_by_student"]), self._current_exam["uuids"]
        ):
            sample = self.get_stream("processor", student, "tensor").get(
                "get_samples", uuid
            )
            if sample is None:
                continue
            self._current_exam["received_by_student"][student].append(
                torch.argmax(sample, dim=1)
            )
        return True

    async def evaulate_exam(self):
        """Score all students once everyone has finished.

        Ground truth comes directly from _eval_labels_by_class (built at init time),
        so no manifest lookup needed — just zip predictions against the ordered label list.
        We wait until all students have finished before scoring anyone.
        """
        if not self.all_students_finished() and (clock.get_time() - self._timers["exam"]["start"]) <= self._timers["exam"]["timeout"]:
            return False  # retry next tick

        ground_truth = self.ground_truth_for_classes(self._current_exam["seen_classes"])

        for student, predictions in self._current_exam["received_by_student"].items():
            result = self.compute_accuracy([int(p) for p in predictions], ground_truth)
            self._current_exam["scores"][student] = result
            self._students[student]["evaluations"].append({
                "exam_id": self._current_exam["id"],
                **result,
            })
            for stat_name, value in result.items():
                self.stats.store_stat(stat_name, value, student)
                
        return True

    async def init_lesson(self):
        """Send a training interaction to all students for the current class.

        send() is the public wrapper around _send():
          stdin  → images (the processor's input)
          stdtar → labels (the supervisor signal; the student uses this to learn)
          stdext → empty (no auxiliary data)
        num_steps tells the student how many samples to consume before finishing.
        """
        return await self.send(
            action_name="learn",
            target=list(self._students.keys()),
            streams={
                "stdin": [f"images_train_{self._current_lesson}"],
                "stdtar": [f"labels_train_{self._current_lesson}"],
                "stdext": [],
            },
            num_steps=self._teach_per_class,
        )
