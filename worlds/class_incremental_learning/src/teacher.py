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
import os
import torch
import random
import datetime
import numpy as np
from unaiverse.clock import clock
from unaiverse.utils.logger import log
from unaiverse.agent import Agent, action
from torchvision import datasets, transforms
from unaiverse.streams import Dataset, Stream
from unaiverse.utils.misc import prepare_app_dir
from unaiverse.streams.dataprops import DataProps
from torch.utils.data import ConcatDataset, Subset


class WAgent(Agent):
    """Teacher for class-incremental learning on MNIST.

    HSM (see `teacher.json`):
      1. welcoming  — wait for at least one student (timer-bounded).
      2. brainstorm — pick the next action: teach a new class or evaluate.
      3. lesson     — fan-out `learn` to every student for one class, then wait for completion
                      via `all_sent_completed(action_name="learn")`.
      4. exam       — fan-out `process` to every student, collect predictions via
                      `received_some_asked_data(processing_fcn="collect_predictions")`,
                      then score once `all_sent_completed(action_name="process")` is true.
    """
    EVAL_PER_CLASS = 20
    TEACH_PER_CLASS = 50
    BATCH_SIZE = 1
    NUM_CLASSES = 10
    EXAM_TIMEOUT_SEC = 120.0
    WELCOMING_TIMEOUT_SEC = 90.0

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # Connected-student bookkeeping (peer_id -> per-student history)
        self._students = {}

        # Welcoming timer
        self._welcoming_started_at = None

        # State of the learning curriculum
        self._current_lesson = -1  # -1: nothing taught yet; 0..9: last class taught
        self._current_intent = None  # "teach" or "evaluate"

        # Per-exam state (None when no exam is running)
        self._current_exam = None

        # MNIST data
        data_dir = str(os.path.join(prepare_app_dir(), "incremental_learning"))
        self._train_dataset, self._test_dataset = WAgent._load_mnist(data_dir)
        self._eval_labels_by_class = {}

    def accept_new_role(self, role: int):
        """Build per-class teach streams and one combined eval stream once the role is assigned."""
        super().accept_new_role(role)

        eval_sets = {cls: WAgent._subsample_class(self._test_dataset, self.EVAL_PER_CLASS, cls)
                     for cls in range(self.NUM_CLASSES)}
        teach_sets = {cls: WAgent._subsample_class(self._train_dataset, self.TEACH_PER_CLASS, cls)
                      for cls in range(self.NUM_CLASSES)}
        self._eval_labels_by_class = {cls: [int(self._test_dataset.targets[i]) for i in s.indices]
                                      for cls, s in eval_sets.items()}

        # Combined eval stream (all 10 classes, in class order)
        eval_combined = ConcatDataset([eval_sets[cls] for cls in range(self.NUM_CLASSES)])
        self.add_streams([
            Stream.create(group="eval", name="images", public=False,
                          stream=Dataset(eval_combined, shape=(None, 1, 28, 28),
                                         index=0, batch_size=self.BATCH_SIZE))
        ])

        # One pair of (images, labels) streams per class for teaching
        for cls in range(self.NUM_CLASSES):
            group = f"teach_{cls}"
            self.add_streams([
                Stream.create(group=group, name="images", public=False,
                              stream=Dataset(teach_sets[cls], shape=(None, 1, 28, 28),
                                             index=0, batch_size=self.BATCH_SIZE)),
                Stream.create(group=group, name="labels", public=False,
                              stream=Dataset(teach_sets[cls], shape=(None,),
                                             index=1, batch_size=self.BATCH_SIZE)),
            ])
        self.update_streams_in_profile()

    @staticmethod
    def _load_mnist(data_dir: str):
        """Load MNIST train and test splits from `data_dir/mnist_data` (downloading if absent)."""
        transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize((0.1307,), (0.3081,)),
        ])
        train = datasets.MNIST(root=os.path.join(data_dir, "mnist_data"), train=True, download=True,
                               transform=transform)
        test = datasets.MNIST(root=os.path.join(data_dir, "mnist_data"), train=False, download=True,
                              transform=transform)
        return train, test

    @staticmethod
    def _subsample_class(dataset, n_per_class: int, cls: int, offset: int = 0) -> Subset:
        """Return a Subset holding `n_per_class` randomly-shuffled samples of class `cls`."""
        cls_indices = np.where(dataset.targets.cpu().numpy() == cls)[0][offset:offset + n_per_class].tolist()
        random.shuffle(cls_indices)
        return Subset(dataset, cls_indices)

    def _classes_taught_so_far(self) -> list:
        return list(range(self._current_lesson + 1)) if self._current_lesson >= 0 else []

    @staticmethod
    def _short(peer_id: str) -> str:
        return peer_id[:12] if len(peer_id) > 12 else peer_id

    @staticmethod
    def _acc_icon(acc: float) -> str:
        if acc >= 0.9:
            return "🟢"
        if acc >= 0.7:
            return "🟡"
        if acc >= 0.5:
            return "🟠"
        return "🔴"

    def _ground_truth_for(self, classes: list) -> list:
        return [label for cls in classes for label in self._eval_labels_by_class[cls]]

    def _compute_accuracy(self, predictions: list, ground_truth: list) -> dict:
        np_pred = np.array(predictions)
        np_gt = np.array(ground_truth)
        per_class = {f"peer_acc_per_class_{cls}": float(np.sum(np_pred[np_gt == cls] == cls)) / self.EVAL_PER_CLASS
                     for cls in np.unique(np_gt)}
        return {"accuracy": int(np.sum(np_pred == np_gt)) / len(predictions), **per_class}

    @staticmethod
    def _format_exam_table(exam: dict) -> str:
        seen = exam["seen_classes"]
        scores = exam["scores"]
        if not scores:
            return "  (no scores available)"
        id_w, cls_w, ov_w = 16, 12, 14

        def pad(s, w):
            extra = sum(1 for c in s if ord(c) > 0x1F000)
            return s + " " * max(0, w - len(s) - extra)

        lines = ["",
                 f"  📊  EXAM RESULTS  —  {exam['id']}",
                 f"  📋  Classes tested: {seen}",
                 ""]
        header = pad("Student", id_w) + "".join(pad(f"Cls {c}", cls_w) for c in seen) + pad("Overall", ov_w)
        lines.append("  " + header)
        lines.append("  " + "─" * (id_w + cls_w * len(seen) + ov_w))
        for student, result in scores.items():
            row = pad(WAgent._short(student), id_w)
            for cls in seen:
                acc = result.get(f"peer_acc_per_class_{cls}", 0.0)
                row += pad(f"{WAgent._acc_icon(acc)} {acc * 100:5.1f}%", cls_w)
            ov = result.get("accuracy", 0.0)
            row += pad(f"{WAgent._acc_icon(ov)} {ov * 100:5.1f}%", ov_w)
            lines.append("  " + row)
        lines.append("")
        lines.append("  Legend: 🟢 >=90%  🟡 >=70%  🟠 >=50%  🔴 <50%")
        return "\n".join(lines)

    @action
    async def on_tick(self):
        """Keep the connected-student roster fresh — handshake_completed=True ensures we can talk."""
        await super().on_tick()
        connected = set(self.get_agents_by_role("student", handshake_completed=True))
        joined = connected - set(self._students.keys())
        gone = set(self._students.keys()) - connected
        for s in joined:
            self._students[s] = {"exams": [], "lessons": [], "evaluations": []}
            log.user(f"👋 New student connected: {self._short(s)}")
        for s in gone:
            del self._students[s]
            log.user(f"🚪 Student disconnected: {self._short(s)}")
        if joined or gone:
            log.user(f"📡 Connected students: {len(self._students)}")
        return True

    @action
    async def welcoming(self):
        """Wait until at least one student has joined OR `WELCOMING_TIMEOUT_SEC` has elapsed."""
        if self._welcoming_started_at is None:
            self._welcoming_started_at = clock.get_time()
            log.user("⏱️  Welcoming timer started")

        elapsed = clock.get_time() - self._welcoming_started_at
        timed_out = elapsed > self.WELCOMING_TIMEOUT_SEC
        enough = len(self._students) >= 1

        if int(elapsed) % 10 == 0:
            log.debug(f"⏳ Welcoming: {elapsed:.0f}s / {self.WELCOMING_TIMEOUT_SEC:.0f}s, "
                      f"{len(self._students)} student(s)")

        if timed_out or enough:
            reason = "enough students" if enough else "timeout"
            log.user(f"✅ Welcoming complete ({reason}) — ready to teach!")
            self._welcoming_started_at = None
            return True
        return False

    @action
    async def should_teach_or_evaluate(self):
        """Set `_current_intent` based on how many classes have been taught so far."""
        self._current_intent = "teach" if self._current_lesson < self.NUM_CLASSES - 1 else "evaluate"
        icon = "📖" if self._current_intent == "teach" else "📝"
        log.user(f"{icon} Decision: '{self._current_intent}' "
                 f"(lessons completed: {self._current_lesson + 1}/{self.NUM_CLASSES})")
        return True

    @action
    async def building_lesson(self):
        """Guard transition: take the lesson branch only when intent is 'teach'."""
        return self._current_intent == "teach"

    @action
    async def building_evaluation(self):
        """Guard transition: take the exam branch only when intent is 'evaluate'."""
        return self._current_intent == "evaluate"

    @action
    async def init_lesson(self):
        """Fan-out `learn` to every connected student for the next class as a single multi-target
        interaction. After this returns True, the HSM exits via `all_sent_completed(action_name="learn")`.
        """
        if not self._students:
            return False
        self._current_lesson += 1
        cls = self._current_lesson
        _, prv_id = self.get_peer_ids()
        ok = await self.send(
            action_name="learn",
            target=list(self._students.keys()),
            from_state="wait",
            streams={"stdin": [f"{prv_id}:images@teach_{cls}"],
                     "stdtar": [f"{prv_id}:labels@teach_{cls}"],
                     "stdext": []},
            num_steps=self.TEACH_PER_CLASS,
        )
        if not ok:
            self._current_lesson -= 1
            return False
        log.user(f"📖 Lesson {cls} sent to {len(self._students)} student(s)")
        return True

    @action
    async def send_exam(self):
        """Fan-out `process` over the eval stream to every connected student.

        The exam tests every class taught so far. Each per-student interaction carries
        `timeout=EXAM_TIMEOUT_SEC`, so a non-responsive student auto-completes after
        `EXAM_TIMEOUT_SEC` and `all_sent_completed(action_name="process")` will eventually
        fire even with partial replies — `score_exam` then scores whatever was collected.
        """
        if self._current_exam is not None:
            return True
        students = list(self._students.keys())
        seen = self._classes_taught_so_far()
        if not students or not seen:
            return False

        self._current_exam = {
            "id": f"exam_{int(datetime.datetime.now().timestamp())}",
            "seen_classes": seen,
            "predictions_by_student": {s: [] for s in students},
            "scores": {},
        }

        # Clearing data received due to previous interactions
        for stud in students:
            stud_proc = self.get_stream("processor", stud)
            if stud_proc is not None:
                stud_proc.clear_all_data()

        _, prv_id = self.get_peer_ids()
        ok = await self.send(
            action_name="process",
            target=students,
            from_state="wait",
            streams={"stdin": [f"{prv_id}:images@eval"], "stdtar": [], "stdext": []},
            num_steps=self.EVAL_PER_CLASS * len(seen),
            timeout=self.EXAM_TIMEOUT_SEC,
        )
        if not ok:
            self._current_exam = None
            return False
        log.user(f"📋 Exam sent to {len(students)} student(s) over classes {seen}")
        return True

    def collect_predictions(self, agent: str, props: DataProps, data, data_tag: int):  # noqa
        """`received_some_asked_data` processing function: append each student's class prediction.

        The student's processor output declares `proc_to_stream_transforms=lambda x: argmax(x, dim=1)`
        (see run_2.py), so what arrives here is already a class index — a long tensor of shape
        `(batch_size,)`. We just unbox it.
        """
        if self._current_exam is None or agent not in self._current_exam["predictions_by_student"]:
            return
        prediction = int(data.item()) if isinstance(data, torch.Tensor) else int(data)
        self._current_exam["predictions_by_student"][agent].append(prediction)

    @action
    async def score_exam(self):
        """Score every student once the exam fan-out has completed, then clear the exam state."""
        if self._current_exam is None:
            return False
        ground_truth = self._ground_truth_for(self._current_exam["seen_classes"])
        for student, predictions in self._current_exam["predictions_by_student"].items():
            if not predictions:
                continue
            gt = ground_truth[:len(predictions)]
            result = self._compute_accuracy(predictions, gt)
            self._current_exam["scores"][student] = result
            self._students[student]["evaluations"].append({"exam_id": self._current_exam["id"], **result})

        log.user(f"\n{WAgent._format_exam_table(self._current_exam)}")
        self._current_exam = None
        self._current_lesson = -1
        return True
