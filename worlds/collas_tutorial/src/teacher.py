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
import re
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
    LECTURE_SAMPLES = 1  # 6
    LECTURE_DELTA = 6.0
    LECTURE_MAX_DURATION = LECTURE_DELTA * LECTURE_SAMPLES + 10.
    EXAM_SAMPLES = 2
    EXAM_DELTA = 10.0
    EXAM_MAX_DURATION = EXAM_DELTA * EXAM_SAMPLES + 10.
    FEEDBACK_SAMPLES = 2  # Unlabeled samples
    FEEDBACK_DELTA = EXAM_DELTA
    FEEDBACK_MAX_DURATION = FEEDBACK_SAMPLES * FEEDBACK_DELTA + 10.
    MAX_WAIT_FOR_RESPONSE = 3.  # Student completes an interaction => sends its response => it takes time to travel

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
        self.last_data_sent_at = -1.  # The time at which the last data sample was sent

        # Estimated quality of every student, moving average in [0.0,1.0] (this will not be reset)
        self.student_quality: dict[str, float] = {}

        # Results of the last done exam in [0.0,1.0] (this will not be reset)
        self.student_last_exam_scores: dict[str, float] = {}

        # For every class involved in lectures, we have a stream of images and a stream of class names (labels)
        self.class_name_to_lecture_streams: dict[str, list[ImageFileStream | StringStream]] = \
            {}  # class_name: {stream_name: stream_object}

        # Printing/terminal facilities
        self.prev_print_time = 0
        self.prev_print_string = ""
        self.kb_ready = False
        self.paused = False

    def accept_new_role(self, role: int):
        """This is called when the agent accepts the role of teacher (it builds streams once the role is assigned)."""
        super().accept_new_role(role)

        data_path = os.environ.get("TEACHER_DATA_PATH", None)
        if data_path is None:
            log.critical("Environment variable TEACHER_DATA_PATH not set (without it, I cannot find my own data)!")

        # Utility: reading file names in folder "data/lectures" (and subfolders "1", "2", "3")
        def collect_file_names_and_class_names(_folder: str) -> tuple[list[str], list[str]]:
            _files_per_class = defaultdict(list)
            _file_names = []
            _class_names = []
            for _file_name in sorted(os.listdir(_folder)):  # File name is, e.g., 012_Empoleon.jpg, class "Empoleon"
                if not _file_name.lower().endswith(".jpg"):
                    continue
                if "_" in _file_name:
                    # "012_Empoleon.jpg" -> "Empoleon.jpg" -> "Empoleon"
                    _class_name = _file_name.rsplit("_", 1)[1].split('.')[0]
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
                               public=False,
                               delta=self.LECTURE_DELTA),
                 Stream.create(stream=StringStream(class_names, circular=True),
                               group="lecture" + str(i),
                               name="class_names",
                               pubsub=False,
                               public=False,
                               delta=self.LECTURE_DELTA)
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
                                        public=False,
                                        delta=self.EXAM_DELTA),
                          Stream.create(stream=StringStream(class_names, circular=True),
                                        group="exam",
                                        name="class_names",
                                        pubsub=False,
                                        public=False,
                                        delta=self.EXAM_DELTA)])

        # Reading feedback (unlabeled) files
        folder = os.path.join(str(data_path), "feedback")
        file_names, class_names = collect_file_names_and_class_names(folder)

        # Creating feedback (unlabeled) image stream and 'unknown' label stream
        self.add_streams([Stream.create(stream=ImageFileStream(folder, file_names, circular=True),
                                        group="feedback",
                                        name="images",
                                        pubsub=False,
                                        public=False,
                                        delta=self.FEEDBACK_DELTA),
                          Stream.create(stream=StringStream(class_names, circular=True),
                                        group="feedback",
                                        name="class_names",
                                        pubsub=False,
                                        public=False,
                                        delta=self.FEEDBACK_DELTA)])

        # Refresh streams in profile (this way, the agents connecting to this agent will 'see' these streams)
        self.update_streams_in_profile()

    async def on_tick(self):
        await super().on_tick()

        # If there are no students connected, be sure we go back to the initial state
        if len(self.get_agents_by_role("student")) == 0 and self.behav.get_state_name() != "init":
            await self.behav.act_ghost_transition("init")

        # If the terminal supports it, we check the space bar to pause/resume the teacher
        # Notice: one-time terminal setup (per process), no-enter key delivery, restored at exit
        if sys.stdin is not None and sys.stdin.isatty():

            # Activating the keyboard listener
            # Lazy imports (keep them lazy, otherwise they would block Windows students, since this is Linux only)
            if not self.kb_ready:
                import tty
                import atexit
                import termios
                fd = sys.stdin.fileno()
                old_tty = termios.tcgetattr(fd)
                atexit.register(lambda: termios.tcsetattr(fd, termios.TCSADRAIN, old_tty))
                tty.setcbreak(fd)  # Chars arrive without Enter; Ctrl+C still works; echo is off
                self.kb_ready = True

            # Non-blocking poll: drain whatever was typed since the last tick
            # Lazy import: keep it here (see the note above)
            import select
            while select.select([sys.stdin], [], [], 0)[0]:
                if sys.stdin.read(1) == ' ':
                    was_paused = self.paused
                    self.paused = not self.paused
                    if was_paused:
                        log.user("▶️ Resumed!")

        if self.paused:
            self.behav.enable(False)
            log.user("⏸️ Paused! (finishing the current activity first)")

        if not self.paused and self.prev_print_time > 0 and (self.clock.get_time() - self.prev_print_time) >= 3.:
            students = self.get_agents_by_role('student')
            scores = self.student_last_exam_scores
            quality = self.student_quality
            state = self.behav.get_state_name(consider_limbo=True)
            if "lecture" in state:
                s = f"   Activity: teaching lecture #{self.current_lecture_num}"
            elif "exam" in state:
                s = f"   Activity: running exam"
            elif "feedback" in state:
                s = f"   Activity: asking for feedback"
            else:
                s = f"   Activity: misc"
            s += f"\n   State:    {state}"
            s += f"\n   Students: {len(students)}"
            for student in students:
                s += f"\n             {build_unaid(self.world_agents[student])}, "
                s += f"last exam "
                s += f"{scores[student] if student in scores else '?'}, "
                s += f"quality "
                s += f"{quality[student] if student in quality else '?'}"
            if s != self.prev_print_string:
                log.user(s)
                self.prev_print_string = s
            self.prev_print_time = self.clock.get_time()

    @action
    async def reset_status(self):
        self.current_lecture_num = 1
        self.current_lecture_finished = False
        self.current_exam_finished = False
        self.current_feedback_provided = False
        self.current_students = set()
        self.sent_samples = {}
        self.received_samples = {}
        self.prev_print_time = self.clock.get_time()
        self.last_data_sent_at = -1.
        return True

    @action
    async def give_next_lecture(self):

        # If the teacher already streamed all the lectures, this action must fail
        if self.current_lecture_num > 3:
            return False

        # Resetting mark
        self.current_lecture_finished = False

        # Telling the students
        return await self.send(action_name="print",
                               action_kwargs={"msg": f"**Lecture {self.current_lecture_num}/{3}**\n\n"
                                                     "*Check the following pictures and learn!*\n\n"
                                                     "You are expected to learn to associate pictures with their "
                                                     "category name, provided right after the pictures."},
                               from_state="in_class",
                               target=self.get_agents_by_role("student"),
                               volatile=True)

    @action
    async def teach(self) -> bool:

        # If there are students, let's ask them to 'learn'!
        return await self.send(action_name="learn",
                               from_state="in_class",
                               forced_uuid=f"lecture{self.current_lecture_num}_uuid",
                               target=self.get_agents_by_role("student"),
                               streams={
                                   "stdin": [f"images@lecture{self.current_lecture_num}"],
                                   "stdtar": [f"class_names@lecture{self.current_lecture_num}"]
                               },
                               num_steps=self.LECTURE_SAMPLES,
                               timeout=self.LECTURE_MAX_DURATION,
                               callback="mark_lecture_as_finished")

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

        # Moving to the next lecture
        self.current_lecture_num += 1
        return True

    @action
    async def lecture_finished(self) -> bool:
        return self.current_lecture_finished

    @action
    async def start_exam_session(self) -> bool:

        # Avoid repeating multiple exams, unless the state is reset first
        if self.current_exam_finished:
            return False

        # Resetting marks
        self.sent_samples = {}
        self.received_samples = {}
        self.current_students = set()

        # Telling the students
        return await self.send(action_name="print",
                               action_kwargs={"msg": "**Exam time**\n\n*Let's see if you are good at "
                                                     "classifying the following pictures!*\n\nGood luck!"},
                               from_state="in_class",
                               target=self.get_agents_by_role("student"),
                               volatile=True)

    @action
    async def hand_out_exam(self) -> bool:

        # If there are students, let's ask them to 'process', in order to make predictions on the exam data!
        await self.send(action_name="process",
                        from_state="in_class",
                        forced_uuid=f"exam_uuid",
                        target=self.get_agents_by_role("student"),
                        streams={
                            "stdin": [f"images@exam"],
                            "stdext": [f"class_names@exam"]
                        },
                        num_steps=self.EXAM_SAMPLES,
                        timeout=self.EXAM_MAX_DURATION,
                        callback="mark_exam_as_finished")

        # Saving
        self.current_students = set(self.get_last_sent_interaction().target) \
            if self.get_last_sent_interaction() else set()

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
    async def ask_for_feedback(self) -> bool:

        # Resetting marks
        self.current_feedback_provided = False
        self.sent_samples = {}
        self.received_samples = {}
        self.current_students = set()

        # Telling the students
        return await self.send(action_name="print",
                               action_kwargs={"msg": "**Feedback time**\n\n*I need your support to categorize "
                                                     "some unlabeled pictures!*\n\nHelp me!"},
                               from_state="in_class",
                               target=self.get_agents_by_role("student"),
                               volatile=True)

    @action
    async def send_requests(self) -> bool:

        # If there are students, let's ask them to 'process', in order to make predictions on the feedback data!
        await self.send(action_name="process",
                        from_state="in_class",
                        forced_uuid=f"feedback_uuid",
                        target=self.get_agents_by_role("student"),
                        streams={
                            "stdin": [f"images@feedback", f"class_names@feedback"],
                        },
                        num_steps=self.FEEDBACK_SAMPLES,
                        timeout=self.FEEDBACK_MAX_DURATION,
                        callback="mark_feedback_as_provided")

        # Saving
        self.current_students = set(self.get_last_sent_interaction().target) \
            if self.get_last_sent_interaction() else set()

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
            data_path = os.environ.get("TEACHER_DATA_PATH")

            # Computing agreement of the feedbacks
            i = 1
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
                    log.user(f"**There was an agreement for image number {i}!**\n\n"
                             f"It was marked as belonging to category **{agreed_class_name}**")

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
                        log.user(f"Adding image to lecture {lecture_w_id}!")
                        self.class_name_to_lecture_streams[agreed_class_name][0].add(file_name)
                        self.class_name_to_lecture_streams[agreed_class_name][1].add(agreed_class_name)
                else:
                    log.user(f"*Unfortunately, feedbacks were not robust enough to decide on image number {i}*")
                i += 1

        return self.current_feedback_provided

    @action
    async def on_data(self, stream_group: str) -> bool:
        uuid = self.get_last_sent_interaction().uuid

        def on_sending() -> bool:
            stream = self.get_stream(stream_group, data_type="text")
            data = stream.get("on_sending", uuid=uuid)
            if data is None:
                return False

            tag = stream.get_tag(uuid=uuid)
            if tag not in self.sent_samples:
                self.sent_samples[tag] = [None, None]
            self.sent_samples[tag][1] = data

            stream = self.get_stream(stream_group, data_type="img")
            data = stream.get("on_sending", uuid=uuid)
            if data is None:
                return False

            if tag != stream.get_tag(uuid=uuid):
                log.error("Unexpected tag!")
                return False

            if tag not in self.sent_samples:
                self.sent_samples[tag] = [None, None]
            self.sent_samples[tag][0] = data

            log.user(f"   >>> Sent data with tag {tag}")
            return True

        def on_receiving():
            at_least_one_received = False
            for student in self.current_students:
                student_stream = self.get_stream("processor", student, data_type="text")
                msg = student_stream.get("on_receiving", uuid=uuid)
                class_name = None
                tag = -1
                if msg is not None:
                    at_least_one_received = True

                    # Parsing UAI response, getting the class name from the 'raw' field
                    if not msg.startswith("```"):
                        class_name = msg
                        tag = student_stream.get_tag(uuid=uuid)
                    else:
                        for line in msg.splitlines():
                            line = line.strip()
                            if not line.startswith("{"):
                                continue
                            try:
                                data = json.loads(line)
                            except json.JSONDecodeError:
                                continue
                            raw = data.get("raw") or []
                            text = " ".join(raw) if isinstance(raw, list) else str(raw)
                            class_name = re.sub(r"^[\s:\-–—]+", "", text).strip()
                            try:
                                tag = int((data.get("to") or "").split("-")[-1])
                            except Exception:
                                continue
                            break
                    if class_name is None:
                        continue
                else:
                    continue

                if tag not in self.received_samples:
                    self.received_samples[tag]: dict[str, str] = {}
                self.received_samples[tag][student] = class_name
                log.user(f"   <<< Received prediction '{class_name}' for data with tag {tag} "
                         f"from student {build_unaid(self.world_agents[student])}")
            return at_least_one_received

        sent = on_sending()
        recv = on_receiving()

        if sent:
            self.last_data_sent_at = self.clock.get_time()
        return sent or recv or (self.clock.get_time() - self.last_data_sent_at) < self.MAX_WAIT_FOR_RESPONSE

    def hook_before_sending_sample(self, data, data_tag: int, net_hash: str, stream_name: str, _: str | None):
        if data is None:
            return data

        stream_group = Stream.name_or_group_from_net_hash(net_hash)
        if stream_group in {"exam", "feedback"} and stream_name.split("@")[0] == "class_names":
            class_names = self.class_name_to_lecture_streams.keys()
            block = {
                "v": 1,
                "type": "form",
                "id": f"catform-{stream_group}-{data_tag}",
                "name": "What is the category of the picture above?",
                "lang": "en",
                "fields": [{
                    "name": "scelta",
                    "type": "select",
                    "required": True,
                    "label": "",
                    "options": [{"value": lab, "label": lab} for lab in class_names],
                    "ui": "buttons"
                }],
                "alt": f"Answer by only writing the class name ({', '.join(lab for lab in class_names)})"
            }
            title = "**Exercise**" if stream_group == "exam" else "**Feedback Request** (Help!)"
            return f"{title}\n\n```uai\n{json.dumps(block, ensure_ascii=False)}\n```"
        else:
            return data
