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
import sys
import json
from collections import defaultdict
from unaiverse.streams import Stream
from unaiverse.utils.logger import log
from unaiverse.agent import Agent, action
from unaiverse.utils.misc import build_unaid
from unaiverse.interaction import Interaction
from unaiverse.streams import ImageFileStream, StringStream


class WAgent(Agent):
    """Teacher agent."""

    # Configuration (current data has 6 classes in total, divided into folders with data from 2 classes in each of them)
    LECTURE_SAMPLES = 6
    LECTURE_MAX_DURATION = 20.
    EXAM_SAMPLES = 6
    EXAM_MAX_DURATION = 30.
    FEEDBACK_SAMPLES = 2  # Unlabeled samples
    FEEDBACK_MAX_DURATION = 30.

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # Status (it will be reset after lectures, exam, asking for feedback)
        self.current_lecture_num: int = 1  # This goes from 1 to 3 (included)
        self.current_lecture_finished: bool = False  # Tells all the students are done (or timed-out)
        self.current_exam_finished: bool = False  # Tells all the students are done (or timed-out)
        self.current_feedback_provided: bool = False  # Tells all students are done with feedback (or timed-out)
        self.current_students: set[str] = set()  # Students participating in the current exam or feedback
        self.sent_samples: dict[int, list] = {}  # Samples sent (tag: [image, class_name], where class_name can be None)
        self.received_samples: dict[int, dict[str, str]] = {}  # Samples received (tag: {student: class_name})

        # Estimated quality of every student, moving average in [0.0,1.0] (this will not be reset)
        self.student_quality: dict[str, float] = {}

        # Results of the last done exam in [0.0,1.0] (this will not be reset)
        self.student_last_exam_scores: dict[str, float] = {}

        # For every class involved in lectures, we have a stream of images and a stream of class names (labels)
        self.class_name_to_lecture_streams: dict[str, list[ImageFileStream | StringStream]] = \
            {}  # class_name: {stream_name: stream_object}

        # Printing facilities
        self.prev_printed_lines = 0

    def accept_new_role(self, role: int):
        """This is called when the agent accepts the role of teacher (it builds streams once the role is assigned)."""
        super().accept_new_role(role)
        data_path = os.environ.get("TEACHER_DATA_PATH", os.path.dirname(os.path.abspath(__file__)))

        # Utility: reading file names in folder "data/lectures" (and subfolders "1", "2", "3")
        def collect_file_names_and_class_names(_folder: str) -> tuple[list[str], list[str]]:
            _files_per_class = defaultdict(list)
            _file_names = []
            _class_names = []
            for _file_name in sorted(os.listdir(_folder)):  # File name is, e.g., 012_Empoleon.jpg, class "Empoleon"
                if not _file_name.lower().endswith(".jpg"):
                    continue
                if "_" in _file_name:
                    _class_name = _file_name.rsplit("_", 1)[1]  # "012_Empoleon.jpg" -> "Empoleon"
                else:
                    _class_name = "unknown"
                _file_names.append(_file_name)
                _class_names.append(_class_name)
            return _file_names, _class_names

        # Reading files of the three lectures
        self.class_name_to_lecture_streams = {}  # Clearing
        for i in range(1, 4):  # We have just 3 lectures (1, 2, 3)
            folder = os.path.join(str(data_path), "lectures", str(i))
            file_names, class_names = collect_file_names_and_class_names(folder)

            # Creating one stream of images (JPGs) and one stream of text (class names) per lecture
            streams = self.add_streams(
                [Stream.create(stream=ImageFileStream(folder, file_names, circular=True),
                               group="lecture" + str(i),
                               name="images",
                               pubsub=False,
                               delta=2.0),
                 Stream.create(stream=StringStream(class_names, circular=True),
                               group="lecture" + str(i),
                               name="class_names",
                               pubsub=False,
                               delta=2.0)
                 ])

            # Mapping class name to the associated streams (stream of images, stream of class names)
            self.class_name_to_lecture_streams.update({class_name: list(streams[0].values())
                                                       for class_name in list(set(class_names))})

        # Reading exam files
        folder = os.path.join(str(data_path), "exam")
        file_names, class_names = collect_file_names_and_class_names(folder)

        # Creating exam stream
        self.add_streams([Stream.create(stream=ImageFileStream(folder, file_names, circular=True),
                                        group="exam",
                                        name="images",
                                        pubsub=False,
                                        delta=2.0),
                          Stream.create(stream=StringStream(class_names, circular=True),
                                        group="exam",
                                        name="class_names",
                                        pubsub=False,
                                        delta=2.0)])

        # Reading feedback (unlabeled) files
        folder = os.path.join(str(data_path), "feedback")
        file_names, class_names = collect_file_names_and_class_names(folder)

        # Creating feedback (unlabeled) image stream and 'unknown' label stream
        self.add_streams([Stream.create(stream=ImageFileStream(folder, file_names, circular=True),
                                        group="feedback",
                                        name="images",
                                        pubsub=False,
                                        delta=2.0),
                          Stream.create(stream=StringStream(class_names, circular=True),
                                        group="feedback",
                                        name="class_names",
                                        pubsub=False,
                                        delta=2.0)])

        # Refresh streams in profile (this way, the agents connecting to this agent will 'see' these streams)
        self.update_streams_in_profile()

    async def on_tick(self):
        await super().on_tick()
        if self.prev_printed_lines > 0:
            sys.stdout.write(f"\x1b[{self.prev_printed_lines}A")
        students = self.get_agents_by_role('student')
        log.user(f"\r\x1b[2KState: {self.behav.get_state()}")
        log.user(f"\r\x1b[2KAction: {self.behav.get_action()}")
        log.user(f"\r\x1b[2KKnown students: {len(students)}")
        for student in students:
            log.user(f"\r\x1b[2K- {build_unaid(self.world_agents[student])}, "
                     f"last exam "
                     f"{self.student_last_exam_scores[student] if student in self.student_last_exam_scores else '?'}, "
                     f"quality "
                     f"{self.student_quality[student] if student in self.student_quality else '?'}")
        self.prev_printed_lines = 3 + len(students) + 1

    @action
    async def reset_status(self):
        self.current_lecture_num = 1
        self.current_lecture_finished = False
        self.current_exam_finished = False
        self.current_feedback_provided = False
        self.current_students = set()
        self.sent_samples = {}
        self.received_samples = {}
        return True

    @action
    async def no_students(self) -> bool:
        return len(self.get_agents_by_role("student")) == 0

    @action
    async def teach_next_lecture(self) -> bool:

        # If the teacher already streamed all the lectures, this action must fail
        if self.current_lecture_num > 3:
            return False

        # Resetting mark
        self.current_lecture_finished = False

        # If there are no students, well, nothing to do
        students = self.get_agents_by_role("student")
        if len(students) == 0:
            return False

        # If there are students, let's ask them to 'learn'!
        sending_went_ok = await self.send(action_name="learn",
                                          from_state="in_class",
                                          target=students,
                                          streams={
                                              "stdin": [f"images@lecture{self.current_lecture_num}"],
                                              "stdtar": [f"class_names@lecture{self.current_lecture_num}"]
                                          },
                                          num_steps=self.LECTURE_SAMPLES,
                                          timeout=self.LECTURE_MAX_DURATION,
                                          callback="mark_lecture_as_finished")

        # If the request was fine, we move the index to the next lecture
        if sending_went_ok:
            self.current_lecture_num += 1  # Moving to the next lecture
            return True
        else:
            return False

    @action
    async def mark_lecture_as_finished(self, interaction: Interaction | None = None) -> bool:
        """Callback triggered when a student finished learning, returning True only if all students finished."""

        # Safety check
        if interaction is None:
            return False

        # The callback will fire for each involved student, but will be 'completed' only when ALL students finished
        if not interaction.is_completed():
            return False

        # Marking
        self.current_lecture_finished = True
        return True

    @action
    async def lecture_finished(self) -> bool:
        return self.current_lecture_finished

    @action
    async def start_exam(self) -> bool:

        # Avoid repeating multiple exams, unless the state is reset first
        if self.current_exam_finished:
            return False

        # Resetting marks
        self.sent_samples = {}
        self.received_samples = {}

        # If there are no students, well, nothing to do
        students = self.get_agents_by_role("student")
        if len(students) == 0:
            return False

        # If there are students, let's ask them to 'process', in order to make predictions on the exam data!
        await self.send(action_name="process",
                        from_state="in_class",
                        target=students,
                        streams={
                            "stdin": [f"images@exam"],
                            "stdtar": [f"class_names@exam"]
                        },
                        num_steps=self.EXAM_SAMPLES,
                        timeout=self.EXAM_MAX_DURATION,
                        callback="mark_exam_as_finished")

        # Saving
        self.current_students = set(self.get_last_sent_interaction().target)

        return len(self.current_students) > 0

    @action
    async def mark_exam_as_finished(self, interaction: Interaction | None = None) -> bool:
        """Callback triggered when a student finished learning, returning True only if all students finished."""

        # Safety check
        if interaction is None:
            return False

        # The callback will fire for each involved student, but will be 'completed' only when ALL students finished
        if not interaction.is_completed():
            return False

        # Marking
        self.current_exam_finished = True
        return True

    @action
    async def evaluate_results(self) -> bool:
        if self.current_exam_finished:

            # Computing exam scores
            self.student_last_exam_scores = {student: 0. for student in self.current_students}
            for tag, (_, ground_truth) in self.sent_samples.items():
                if tag in self.received_samples:
                    for student, answer in self.received_samples[tag].items():
                        self.student_last_exam_scores[student] += (
                            float(answer.strip().lower() == ground_truth.strip().lower()))
            for student, score in self.student_last_exam_scores.items():
                self.student_last_exam_scores[student] = float(score) / max(len(self.sent_samples), 1)

            # Estimating student average quality (moving average)
            # Initial value, assumed to be max 0.5, to avoid having had a first lucky shot
            for student, score in self.student_last_exam_scores.items():
                if student not in self.student_quality:
                    self.student_quality[student] = min(score, 0.5)
                else:
                    self.student_quality[student] = self.student_quality[student] * 0.5 + score * 0.5

        return self.current_exam_finished

    @action
    async def on_data(self, stream_group: str, data_type: str = "both") -> bool:
        uuid = self.get_last_sent_interaction().uuid

        def on_sending() -> bool:
            if data_type == "both" or data_type == "text":
                stream = self.get_stream(stream_group, data_type="text")
                data = stream.get("on_sending", uuid=uuid)
                if data is None:
                    return False

                tag = stream.get_tag(uuid=uuid)
                if tag not in self.sent_samples:
                    self.sent_samples[tag] = [None, None]
                self.sent_samples[tag][1] = data

            if data_type == "both" or data_type == "img":
                stream = self.get_stream(stream_group, data_type="img")
                data = stream.get("on_sending", uuid=uuid)
                if data is None:
                    return False

                tag = stream.get_tag(uuid=uuid)
                if tag not in self.sent_samples:
                    self.sent_samples[tag] = [None, None]
                self.sent_samples[tag][0] = data
            return True

        def on_receiving():
            at_least_one_received = False
            for student in self.current_students:
                student_stream = self.get_stream("processor", student, data_type="text")
                class_name = student_stream.get("on_receiving", uuid=uuid)
                if class_name is not None:
                    at_least_one_received = True
                else:
                    continue

                tag = student_stream.get_tag(uuid=uuid)
                if tag not in self.received_samples:
                    self.received_samples[tag]: dict[str, str] = {}
                self.received_samples[tag][student] = class_name
            return at_least_one_received

        sent = on_sending()
        recv = on_receiving()
        return sent or recv

    @action
    async def ask_feedback(self) -> bool:

        # Resetting marks
        self.current_feedback_provided = False
        self.sent_samples = {}
        self.received_samples = {}

        # If there are no students, well, nothing to do
        students = self.get_agents_by_role("student")
        if len(students) == 0:
            return False

        # If there are students, let's ask them to 'process', in order to make predictions on the exam data!
        await self.send(action_name="process",
                        from_state="in_class",
                        target=students,
                        streams={
                            "stdin": [f"images@feedback", f"class_names@feedback"],
                        },
                        num_steps=self.FEEDBACK_SAMPLES,
                        timeout=self.FEEDBACK_MAX_DURATION,
                        callback="mark_feedback_as_provided")

        # Saving
        self.current_students = set(self.get_last_sent_interaction().target)
        return len(self.current_students) > 0

    @action
    async def mark_feedback_as_provided(self, interaction: Interaction | None = None) -> bool:
        """Callback triggered when a student finished learning, returning True only if all students finished."""

        # Safety check
        if interaction is None:
            return False

        # The callback will fire for each involved student, but will be 'completed' only when ALL students finished
        if not interaction.is_completed():
            return False

        # Marking
        self.current_feedback_provided = True
        return True

    @action
    async def augment_lectures(self) -> bool:
        if self.current_feedback_provided:
            data_path = os.environ.get("TEACHER_DATA_PATH", os.path.dirname(os.path.abspath(__file__)))

            # Computing agreement of the feedbacks
            for tag, (img, _) in self.sent_samples.items():
                agreement: dict[str, int] = {}
                max_agreement_score = 0
                agreed_class_name = None

                if tag in self.received_samples:
                    for student, answer in self.received_samples[tag].items():
                        if self.student_quality[student] > 0.8:
                            answer = answer.strip().capitalize()
                            if answer not in agreement:
                                agreement[answer] = 0
                            agreement[answer] += 1
                            if agreement[answer] > max_agreement_score:
                                max_agreement_score = agreement[answer]
                                agreed_class_name = answer

                # Augmenting lecture material
                if agreed_class_name is not None:
                    if agreed_class_name in self.class_name_to_lecture_streams:

                        # Determining the name of the file to add to the lecture data
                        lecture_w_id = self.class_name_to_lecture_streams[agreed_class_name][0].props.group[-1] # noqa
                        folder = os.path.join(str(data_path), "lectures", lecture_w_id)
                        nums = [int(f.split("_")[0]) for f in os.listdir(folder)
                                if f.endswith(".jpg") and f.split("_")[0].isdigit()]
                        last = max(nums, default=0)
                        file_name = os.path.join(folder, f"{last + 1:03d}_{agreed_class_name}.jpg")

                        # Saving file and adding to the stream source
                        img.save(file_name)
                        self.class_name_to_lecture_streams[agreed_class_name][0].add(file_name)
                        self.class_name_to_lecture_streams[agreed_class_name][1].add(agreed_class_name)

        return self.current_feedback_provided

    def hook_before_sending_sample(self, data, data_tag: int, net_hash: str, stream_name: str, _: str | None):
        stream_group = Stream.name_or_group_from_net_hash(net_hash)
        if stream_group in {"exam", "feedback"} and stream_name == "class_names":
            class_names = self.class_name_to_lecture_streams.keys()
            block = {
                "v": 1,
                "type": "form",
                "id": f"catform-{stream_name}-{data_tag}",
                "name": "categorization",
                "lang": "en",
                "fields": [{
                    "name": "scelta",
                    "type": "select",
                    "label": "class",
                    "required": True,
                    "options": [{"value": f"opt{i}", "label": lab[:120]} for i, lab in enumerate(class_names)],
                    "ui": "buttons"
                }],
                "alt": f"Answer by only writing the class name ({', '.join(lab[:120] for lab in class_names)})"
            }
            return f"What is the category of this picture?\n\n```uai\n{json.dumps(block, ensure_ascii=False)}\n```"
        else:
            return data
