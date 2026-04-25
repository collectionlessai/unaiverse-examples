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
from torch.utils.data import ConcatDataset, DataLoader, Subset
from torchvision import datasets, transforms
from unaiverse.agent import Agent
from unaiverse.clock import clock
from unaiverse.interaction import Interaction
from unaiverse.streams import Dataset, Stream
from unaiverse.utils.misc import prepare_app_dir
from unaiverse.utils.logger import log
from unaiverse.agent import action

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
        self._students = {}  # peer_id → {exams, lessons, evaluations, profile}
        self._timers = {
            "welcoming": {
                "start": None,
                "timeout": datetime.timedelta(seconds=90).total_seconds(),
            },
            "exam": {
                "start": None,
                "timeout": datetime.timedelta(seconds=120).total_seconds(),
            },
        }
        self._best_student = None
        self._current_intent = None  # "teach" or "evaluate"
        self._current_lesson = -1  # -1 = no lesson taught yet; 0–9 = last class taught
        self._current_exam = None
        self._lesson_finished_students = set()

        # ── Dataset parameters ────────────────────────────────────────────
        self._eval_per_class = 20
        self._teach_per_class = 50
        self._batch_size = 1

        # ── Load MNIST and build class→index maps ─────────────────────────
        data_dir = os.path.join(prepare_app_dir(), "incremental_learning")
        train_dataset, test_dataset = load_mnist(data_dir)
        self.train_dataset = train_dataset
        self.test_dataset = test_dataset
        self._train_class_to_indices = build_class_index(train_dataset)
        self._test_class_to_indices = build_class_index(test_dataset)

    def accept_new_role(self, role: int):
        super().accept_new_role(role)
        self.im.agent = self

        eval_sets = {
            cls: subsample_class(self.test_dataset, self._eval_per_class, cls)
            for cls in range(10)
        }
        teach_sets = {
            cls: subsample_class(self.train_dataset, self._teach_per_class, cls)
            for cls in range(10)
        }

        self._eval_indices_by_class = {
            cls: list(s.indices) for cls, s in eval_sets.items()
        }
        self._eval_labels_by_class = {
            cls: [int(self.test_dataset.targets[i]) for i in s.indices]
            for cls, s in eval_sets.items()
        }

        # ── Register streams (following social_learning pattern) ──────────
        eval_combined = ConcatDataset([eval_sets[cls] for cls in range(10)])
        self._test_stream = self.add_streams([
            Stream.create(
                group="eval",
                name="images",
                public=False,
                stream=Dataset(
                    eval_combined,
                    shape=(None, 1, 28, 28),
                    index=0,
                    batch_size=self._batch_size,
                ),
            )
        ])

        self._train_streams = []
        for cls in range(10):
            group = f"teach_{cls}"
            streams = self.add_streams([
                Stream.create(
                    group=group,
                    name="images",
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
                    name="labels",
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

        self.update_streams_in_profile()

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
            f"peer_acc_per_class_{cls}": float(np.sum(np_predictions[np_ground_truth == cls] == cls)) / self._eval_per_class
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

    def _acc_icon(self, acc: float) -> str:
        if acc >= 0.9:
            return "🟢"
        if acc >= 0.7:
            return "🟡"
        if acc >= 0.5:
            return "🟠"
        return "🔴"

    def _short_id(self, peer_id: str) -> str:
        return peer_id[:12] if len(peer_id) > 12 else peer_id

    def _format_exam_table(self, exam: dict) -> str:
        seen = exam["seen_classes"]
        scores = exam["scores"]
        if not scores:
            return "  (no scores available)"

        ID_W = 16
        CLS_W = 12
        OVR_W = 14

        def dpad(s, w):
            extra = sum(1 for c in s if ord(c) > 0x1F000)
            return s + " " * max(0, w - len(s) - extra)

        lines = [
            "",
            f"  📊  EXAM RESULTS  —  {exam['id']}",
            f"  📋  Classes tested: {seen}",
            "",
        ]

        row = dpad("Student", ID_W)
        for c in seen:
            row += dpad(f"Cls {c}", CLS_W)
        row += dpad("Overall", OVR_W)
        lines.append("  " + row)

        sep = "─" * ID_W
        for _ in seen:
            sep += "─" * CLS_W
        sep += "─" * OVR_W
        lines.append("  " + sep)

        for student, result in scores.items():
            sid = self._short_id(student)
            row = dpad(sid, ID_W)
            for cls in seen:
                acc = result.get(f"peer_acc_per_class_{cls}", 0.0)
                cell = f"{self._acc_icon(acc)} {acc * 100:5.1f}%"
                row += dpad(cell, CLS_W)
            ov = result.get("accuracy", 0.0)
            cell = f"{self._acc_icon(ov)} {ov * 100:5.1f}%"
            row += dpad(cell, OVR_W)
            lines.append("  " + row)

        lines.append("")
        lines.append("  Legend: 🟢 >=90%  🟡 >=70%  🟠 >=50%  🔴 <50%")
        return "\n".join(lines)

    @action
    async def on_tick(self):
        """Called every clock cycle. Keeps the student roster in sync even when no
        interaction is happening — disconnected peers are pruned automatically.

        handshake_completed=True → student has exchanged profiles with us,
        its processor signature is known, so it is safe to send data to it.
        """
        await super().on_tick()
        connected = set(self.get_agents_by_role("student", handshake_completed=True))
        old_students = set(self._students.keys())
        new_joined = connected - old_students
        disconnected = old_students - connected
        for s in connected:
            if s not in self._students:
                self._students[s] = {"exams": [], "lessons": [], "evaluations": []}
        for s in list(self._students.keys()):
            if s not in connected:
                del self._students[s]
        if new_joined:
            for s in new_joined:
                log.user(f"👋 New student connected: {self._short_id(s)}")
        if disconnected:
            for s in disconnected:
                log.user(f"🚪 Student disconnected: {self._short_id(s)}")
        if new_joined or disconnected:
            log.user(f"📡 Connected students: {len(self._students)}")
        return True

    # ── Actions ────────────────────────────────────────────────────────────
    @action
    async def welcoming(self):
        """Wait until ≥3 students have joined OR 90 s have elapsed — whichever comes first."""
        if self._timers["welcoming"]["start"] is None:
            self._timers["welcoming"]["start"] = clock.get_time()
            log.user(f"⏱️  Welcoming timer started")

        elapsed = clock.get_time() - self._timers["welcoming"]["start"]
        timeout = elapsed > self._timers["welcoming"]["timeout"]
        enough_students = len(self._students) >= 1

        if int(elapsed) % 10 == 0:
            log.user(f"⏳ Welcoming: {elapsed:.0f}s / {self._timers['welcoming']['timeout']:.0f}s, {len(self._students)} student(s)")

        if timeout or enough_students:
            reason = "enough students" if enough_students else "timeout"
            log.user(f"✅ Welcoming complete ({reason}) — ready to teach!")
            self._timers["welcoming"]["start"] = None
            return True
        return False

    @action
    async def should_teach_or_evaluate(self):
        """Set the intent flag used by building_lesson / building_evaluation.
        _current_lesson goes -1 → 0 → 1 → ... → 9 (10 classes total, 0–9).
        Once it reaches 9, we switch to evaluate."""
        self._current_intent = "teach" if self._current_lesson < 9 else "evaluate"
        icon = "📖" if self._current_intent == "teach" else "📝"
        log.user(f"{icon} Decision: next action is '{self._current_intent}' (lessons completed: {self._current_lesson + 1}/10)")
        return True  # always advances — just sets the flag

    @action
    async def building_lesson(self):
        """Guard: enter lesson branch only if intent is 'teach'."""
        if self._current_intent != "teach":
            return False
        log.user(f"📚 Building a new lesson...")
        return True
    
    @action
    async def building_evaluation(self):
        """Guard: enter evaluation branch only if intent is 'evaluate'."""
        return self._current_intent == "evaluate"

    @action
    async def student_finished_exam(self, interaction: Interaction):
        """Callback invoked when a student completes its exam interaction.
        interaction.target is the peer_id of the student that just finished.
        We track finished students so evaulate_exam knows when all are done."""
        if not self._current_exam:
            return False
        student = interaction.target[0]
        if student not in self._current_exam["received_by_student"]:
            return False
        self._current_exam["finished_students"].add(student)
        return True

    @action
    async def student_finished_lesson(self, interaction: Interaction):
        student = interaction.target
        #assuming that is a list of 1 element
        self._lesson_finished_students.add(student[0])
        log.user(f"📗 Student {student[:12]}... finished lesson {self._current_lesson}")
        return True

    @action
    async def check_lesson_finished(self):
        if not self._students:
            return False
        all_done = all(s in self._lesson_finished_students for s in self._students)
        if all_done:
            log.user(f"✅ All students finished lesson {self._current_lesson}")
        return all_done

    @action
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
        if self._current_exam is not None:
            return True

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
        _, prv_id = self.get_peer_ids()

        for student in students:
            interaction = await self._send(
                action_name="process",
                target=student,
                streams={"stdin": [f"{prv_id}:images@eval"], "stdtar": [], "stdext": []},
                callback="student_finished_exam",
                num_steps=self._eval_per_class * len(seen),
            )
            if not interaction:
                self._current_exam = None
                return False
            self._current_exam["uuids"].append(interaction.uuid)
        return True

    @action
    async def get_samples(self):
        """Poll for predictions from each student (non-blocking, max 20 s window).
        Students write argmax predictions into their output stream; we collect them here.
        get_stream(...).get(requester, uuid) returns None if data is not ready yet."""
        if (clock.get_time() - self._timers["exam"]["start"]) > self._timers["exam"][
            "timeout"
        ] or not self._current_exam or self._current_exam["finished_students"] == self._current_exam["received_by_student"].keys():
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

    @action
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
            flat_preds = [int(p) for p in predictions]
            if not flat_preds:
                continue
            gt = ground_truth[:len(flat_preds)]
            result = self.compute_accuracy(flat_preds, gt)
            self._current_exam["scores"][student] = result
            self._students[student]["evaluations"].append({
                "exam_id": self._current_exam["id"],
                **result,
            })

        table = self._format_exam_table(self._current_exam)
        log.user(f"\n{table}")

        self._current_exam = None
        return True

    @action
    async def init_lesson(self):
        """Send a training interaction to all students for the current class.

        send() is the public wrapper around _send():
          stdin  → images (the processor's input)
          stdtar → labels (the supervisor signal; the student uses this to learn)
          stdext → empty (no auxiliary data)
        num_steps tells the student how many samples to consume before finishing.
        """
        if not self._students:
            return False
        self._lesson_finished_students = set()
        self._current_lesson += 1
        cls = self._current_lesson
        _, prv_id = self.get_peer_ids()
        for student in self._students:
            interaction = await self._send(
                action_name="learn",
                target=student,
                streams={
                    "stdin": [f"{prv_id}:images@teach_{cls}"],
                    "stdtar": [f"{prv_id}:labels@teach_{cls}"],
                    "stdext": [],
                },
                callback="student_finished_lesson",
                num_steps=self._teach_per_class,
            )
            if not interaction:
                self._current_lesson -= 1
                return False
        log.user(f"📖 Lesson {cls} sent to {len(self._students)} student(s)")
        return True
