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
from collections import defaultdict
from unaiverse.streams import Stream
from unaiverse.utils.logger import log
from unaiverse.agent import Agent, action
from unaiverse.utils.misc import build_unaid
from unaiverse.interaction import Interaction
from unaiverse.streams import ImageFileStream, StringStream


class WAgent(Agent):
    """Teacher agent (teacher.py is paired with teacher.json, that contains the Hybrid State Machine - HSM)."""

    # Configuration (current data has 6 classes in total, divided into lectures with data from 2 classes each)
    LECTURE_SAMPLES = 6  # Number of samples per lecture
    LECTURE_DELTA = 7.0  # Time between two consecutive samples
    LECTURE_MAX_DURATION = LECTURE_DELTA * LECTURE_SAMPLES + 10.  # Used to handle timeouts

    EXAM_SAMPLES = 6
    EXAM_DELTA = 10.0
    EXAM_MAX_DURATION = EXAM_DELTA * EXAM_SAMPLES + 10.

    FEEDBACK_SAMPLES = 2
    FEEDBACK_DELTA = EXAM_DELTA
    FEEDBACK_MAX_DURATION = FEEDBACK_SAMPLES * FEEDBACK_DELTA + 10.

    MAX_WAIT_FOR_RESPONSE = 3  # Student completes an interaction => sends its response => it takes time to travel
    FEEDBACK_QUALITY_THRESHOLD = 0.6  # Feedback from students with a quality score lower than this will be discarded

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

        # For every class involved in lectures, we have a stream of images and a stream of class names (labels)
        self.class_name_to_lecture_streams: dict[str, list[ImageFileStream | StringStream]] = \
            {}  # class_name: {stream_name: stream_object}

        # Printing/terminal facilities
        self.prev_print_string = ""
        self.kb_ready = False
        self.paused = False

    def accept_new_role(self, role: int):
        """This is called when the agent accepts the role of teacher (it builds streams once the role is assigned)."""
        super().accept_new_role(role)

        # Checking if the data that is the source for the teacher streams exist
        data_path = os.environ.get("TEACHER_DATA_PATH", None)
        if data_path is None:
            log.critical("Environment variable TEACHER_DATA_PATH not set (without it, I cannot find my own data)!")

        # Utility: reading file names in "data/lectures" (and subfolders "1", "2", "3"), "data/exam", "data/feedbacks"
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

        # Reading files of the three lectures, data/lectures/1, data/lectures/2, data/lectures/3
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

        # Reading exam files in data/exam
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
        """This method is automatically called at every clock cycle, right before asking the HSM to work."""
        await super().on_tick()

        # If there are no students connected, be sure we go back to the initial state
        if len(self.get_agents_by_role("student")) == 0 and self.behav.get_state_name() != "init":
            await self.behav.act_ghost_transition("init")  # A transition that is temporarily added -> used -> removed

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
            log.user("⏸️ Paused — will hold after the current activity (space to resume)")

        # Printing on screen
        if not self.paused:
            students = self.get_agents_by_role('student')
            quality = self.student_quality
            state = self.behav.get_state_name(consider_limbo=True)
            s = None
            if "lecture" in state:
                s = f"   [Activity] Teaching lecture #{self.current_lecture_num}"
            elif "exam" in state:
                s = f"   [Activity] Running exam"
            elif "feedback" in state:
                s = f"   [Activity] Asking for feedback"
            if s is not None:
                s += f"\n   [Students] "
                for i, student in enumerate(students):
                    if i > 0:
                        s += "\n              "
                    s += f"{build_unaid(self.world_agents[student])} "
                    if student in quality:
                        q = quality[student]
                        s += "★" * round(q * 5.) + "☆" * (5 - round(q * 5.)) + f" ({q:.0%})"
                if s != self.prev_print_string:
                    log.user(s)
                    self.prev_print_string = s

    @action
    async def reset_status(self):
        """This action resets the status of the teacher."""
        self.current_lecture_num = 1
        self.current_lecture_finished = False
        self.current_exam_finished = False
        self.current_feedback_provided = False
        self.current_students = set()
        self.sent_samples = {}
        self.received_samples = {}
        self.last_data_sent_at = -1.
        return True

    @action
    async def give_next_lecture(self):
        """This action prepares the teacher and tells students that the next lecture is going to start."""

        # If the teacher already streamed all the lectures, this action must fail
        if self.current_lecture_num > 3:
            return False

        # Resetting mark
        self.current_lecture_finished = False

        # Telling the students (sending an "interaction" that will trigger action "print" on the student side)
        return await self.send(action_name="print",
                               action_kwargs={"msg": f"📚 **Lecture {self.current_lecture_num}/{3}**\n\n"
                                                     "*Watch the following pictures and learn!*\n\n"
                                                     "You are expected to learn to associate pictures with their "
                                                     "category name."},
                               from_state="in_class",
                               target=self.get_agents_by_role("student"),
                               volatile=True)  # Volatile: no need for confirmations of completion from the students

    @action
    async def teach(self) -> bool:
        """This action sends an interaction to the students, telling them to 'learn' from the lecture stream."""

        return await self.send(action_name="learn",
                               from_state="in_class",
                               forced_uuid=f"lecture{self.current_lecture_num}_uuid",
                               target=self.get_agents_by_role("student"),
                               streams={
                                   "stdin": [f"images@lecture{self.current_lecture_num}"],
                                   "stdtar": [f"class_names@lecture{self.current_lecture_num}"]
                               },
                               num_steps=self.LECTURE_SAMPLES,  # We ask students to call 'learn' multiple times
                               num_samples_to_stream=self.LECTURE_SAMPLES,  # The number of samples we will stream
                               timeout=self.LECTURE_MAX_DURATION,
                               callback="mark_lecture_as_finished")  # Students done? => 'mark_lecture_as_finished' runs

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
        """Checks the flag that marks a lecture as finished, moving to the next lecture number."""

        if self.current_lecture_finished:
            if self.last_data_sent_at < 0:  # We wait a little bit for the last response to travel back
                self.last_data_sent_at = self.clock.get_time()
            ret = (self.clock.get_time() - self.last_data_sent_at) > self.MAX_WAIT_FOR_RESPONSE
            if ret:
                self.current_lecture_num += 1  # Moving to the next lecture
            return ret
        return self.current_lecture_finished

    @action
    async def start_exam_session(self) -> bool:
        """This action prepares the teacher and tells students that the exam is going to start."""

        # Avoid repeating multiple exams, unless the state is reset first
        if self.current_exam_finished:
            return False

        # Resetting marks
        self.sent_samples = {}
        self.received_samples = {}
        self.current_students = set()

        # Telling the students (sending an "interaction" that will trigger action "print" on the student side)
        return await self.send(action_name="print",
                               action_kwargs={"msg": "📝 **Exam time!**\n\n*Let's see if you are good at "
                                                     "classifying the following pictures!*\n\nGood luck! 🍀"},
                               from_state="in_class",
                               target=self.get_agents_by_role("student"),
                               volatile=True)

    @action
    async def hand_out_exam(self) -> bool:
        """This action sends an interaction to the students, telling them to 'process' the exam stream."""

        # Let's ask students to 'process', in order to make predictions on the exam data!
        await self.send(action_name="process",
                        from_state="in_class",
                        forced_uuid=f"exam_uuid",
                        target=self.get_agents_by_role("student"),
                        streams={
                            "stdin": [f"images@exam"],
                            "stdext": [f"class_names@exam"]
                        },
                        num_steps=self.EXAM_SAMPLES,
                        num_samples_to_stream=self.EXAM_SAMPLES,
                        timeout=self.EXAM_MAX_DURATION,
                        callback="mark_exam_as_finished")

        # Saving the involved students (the ones who actually got our interaction, stored in the 'target' attribute)
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
        """Checks the flag that marks an exam as finished, it computes the results, it tells students their scores."""

        if self.current_exam_finished:

            # Computing exam scores
            student_last_exam_scores = {student: 0. for student in self.current_students}
            student_last_exam_detailed_results = {student: ["·"] * len(self.sent_samples)
                                                  for student in self.current_students}
            for i, (tag, (_, ground_truth)) in enumerate(self.sent_samples.items()):
                if tag in self.received_samples:
                    for student, answer in self.received_samples[tag].items():
                        correct = answer.strip().lower() == ground_truth.strip().lower()
                        student_last_exam_detailed_results[student][i] = "✓" if correct else "✗"
                        student_last_exam_scores[student] += float(correct)
            for student, score in student_last_exam_scores.items():
                student_last_exam_scores[student] = float(score) / self.EXAM_SAMPLES

            # Estimating student average quality (moving average)
            # Initial value is biased by a first lucky shot, but it is fine for the tutorial
            for student, score in student_last_exam_scores.items():
                if student not in self.student_quality:
                    self.student_quality[student] = score  # We could initialize this in many ways (fine for tutorial)
                else:
                    self.student_quality[student] = self.student_quality[student] * 0.5 + score * 0.5

            # Printing on screen
            s = "   [Results]  "
            for i, (student, detailed_result) in enumerate(student_last_exam_detailed_results.items()):
                if student not in self.world_agents:  # Safety guard
                    continue
                if i > 0:
                    s += "\n              "
                s += f"{build_unaid(self.world_agents[student])} " + (" ".join(detailed_result)) + " "
                q = student_last_exam_scores[student]
                s += "★" * round(q * 5.) + "☆" * (5 - round(q * 5.)) + f" ({q:.0%})"
            log.user(s)

            # Communicating results to every student
            for student, score in student_last_exam_scores.items():
                if student not in self.world_agents:  # Safety guard
                    continue
                await self.send(action_name="print",
                                action_kwargs={"msg": f"🎯 Your exam result: **{score:.0%}**"},
                                from_state="in_class",
                                target=student,
                                volatile=True)

        return self.current_exam_finished

    @action
    async def ask_for_feedback(self) -> bool:
        """This action prepares the teacher and tells students that the feedback stage is going to start."""

        # Resetting marks
        self.current_feedback_provided = False
        self.sent_samples = {}
        self.received_samples = {}
        self.current_students = set()

        # Telling the students (sending an "interaction" that will trigger action "print" on the student side)
        return await self.send(action_name="print",
                               action_kwargs={"msg": "🙋 **Feedback time**\n\n*I need your support to categorize "
                                                     "some unlabeled pictures!*\n\nHelp me!"},
                               from_state="in_class",
                               target=self.get_agents_by_role("student"),
                               volatile=True)

    @action
    async def send_requests(self) -> bool:
        """This action sends an interaction to the students, telling them to 'process' the feedback-data stream."""

        # Let's ask student to 'process', in order to make predictions on the feedback data!
        await self.send(action_name="process",
                        from_state="in_class",
                        forced_uuid=f"feedback_uuid",
                        target=self.get_agents_by_role("student"),
                        streams={
                            "stdin": [f"images@feedback", f"class_names@feedback"],
                        },
                        num_steps=self.FEEDBACK_SAMPLES,
                        num_samples_to_stream=self.FEEDBACK_SAMPLES,
                        timeout=self.FEEDBACK_MAX_DURATION,
                        callback="mark_feedback_as_provided")

        # Saving the involved students (the ones who actually got our interaction, stored in the 'target' attribute)
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
        """Checks the flag that marks the feedback stage as finished, it aggregates feedbacks and augment lectures."""

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
                        if self.student_quality[student] >= self.FEEDBACK_QUALITY_THRESHOLD:  # Only good students :)
                            answer = answer.strip().capitalize()
                            if answer not in agreement:
                                agreement[answer] = 0
                            agreement[answer] += 1
                            if agreement[answer] > max_agreement_score:
                                max_agreement_score = agreement[answer]
                                agreed_class_name = answer

                # Augmenting lecture material
                if agreed_class_name is not None:
                    log.user(f"🤝 Agreement on picture {i}/{len(self.sent_samples)}: "
                             f"it belongs to category '{agreed_class_name}'")

                    if agreed_class_name in self.class_name_to_lecture_streams:

                        # Determining the name of the file to add to the lecture data
                        lecture_w_id = self.class_name_to_lecture_streams[agreed_class_name][0].props.group[-1] # noqa
                        folder = os.path.join(str(data_path), "lectures", lecture_w_id)
                        nums = [int(f.split("_")[0]) for f in os.listdir(folder)
                                if f.endswith(".jpg") and f.split("_")[0].isdigit()]
                        last = max(nums, default=0)
                        file_name_only = f"{last + 1:03d}_{agreed_class_name}.jpg"
                        file_name = os.path.join(folder, file_name_only)

                        # Saving file and adding to the stream source
                        img.save(file_name)
                        log.user(f"📈 Adding image {file_name_only} to lecture {lecture_w_id}!")
                        self.class_name_to_lecture_streams[agreed_class_name][0].add(file_name)
                        self.class_name_to_lecture_streams[agreed_class_name][1].add(agreed_class_name)
                else:
                    log.user(f"🤷 No robust agreement on picture {i}/{len(self.sent_samples)}")
                i += 1

        return self.current_feedback_provided

    @action
    async def on_data(self, stream_group: str) -> bool:
        """This action is True whenever a new sample is found in our stream group or in the stream from a student."""
        interaction = self.get_last_sent_interaction()
        if interaction is None:
            return False
        uuid = interaction.uuid

        def on_sending() -> bool:

            # We only care about the number of examples we planned to send
            if len(self.sent_samples) >= interaction.num_samples_to_stream:
                return False

            # Here we consider a stream group composed on an image stream and a text stream
            img_stream = self.get_stream(stream_group, data_type="img")
            img_tag = img_stream.get_tag(uuid=uuid)

            text_stream = self.get_stream(stream_group, data_type="text")
            text_tag = text_stream.get_tag(uuid=uuid)

            if img_tag is not None and text_tag is not None and img_tag == text_tag:
                img = img_stream.get("on_sending", uuid=uuid)  # Get from stream! (no repetitions: ask again, get None)
                text = text_stream.get("on_sending", uuid=uuid)  # Get from stream!

                if img is None or text is None:
                    return False

                self.sent_samples[img_tag] = [img, text]  # Saving
                return True
            else:
                return False

        def on_receiving():
            at_least_one_received = False

            for student in self.current_students:

                # The students process data and send them: the pipe connecting to use is their 'processor' stream
                student_stream = self.get_stream("processor", student, data_type="text")
                if student_stream is None:
                    continue
                msg = student_stream.get("on_receiving", uuid=uuid)
                class_name: str | None = None
                tag = -1

                # The response of an AI student is simply the class name
                if msg is not None:
                    at_least_one_received = True
                    class_name = msg
                    tag = student_stream.get_tag(uuid=uuid)
                else:
                    continue

                if tag in self.sent_samples and class_name is not None:
                    if tag not in self.received_samples:
                        self.received_samples[tag]: dict[str, str] = {}
                    self.received_samples[tag][student] = class_name  # Saving

                    # Printing on screen the received data
                    if student in self.world_agents:
                        img_num = list(self.sent_samples).index(tag) + 1
                        log.user(f"   📩 {build_unaid(self.world_agents[student])}: '{class_name}' "
                                 f"(picture {img_num}/{interaction.num_samples_to_stream})")

            return at_least_one_received

        sent = on_sending()
        recv = on_receiving()

        # After some 'sent' data, we wait a little bit before returning False, to allow the last reponse to travel back
        if sent:
            self.last_data_sent_at = self.clock.get_time()
        return sent or recv or (self.clock.get_time() - self.last_data_sent_at) < self.MAX_WAIT_FOR_RESPONSE

