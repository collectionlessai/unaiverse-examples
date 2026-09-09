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
from collections import defaultdict
from unaiverse.streams import Stream
from unaiverse.utils.logger import log
from unaiverse.agent import Agent, action
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
    FEEDBACK_QUALITY_THRESHOLD = 0.8  # Feedback from students with a quality score lower than this will be discarded

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # For every class involved in lectures, we have a stream of images and a stream of class names (labels)
        self.class_name_to_lecture_streams: dict[str, list[ImageFileStream | StringStream]] = \
            {}  # class_name: {stream_name: stream_object}

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

    # ------------------------------------------------------------------
    # ACTIONS (empty for now: they will be implemented in the next step)
    # ------------------------------------------------------------------

    @action
    async def reset_status(self):
        """This action resets the status of the teacher."""
        return True

    @action
    async def give_next_lecture(self):
        """This action prepares the teacher and tells students that the next lecture is going to start."""
        return True

    @action
    async def teach(self) -> bool:
        """This action sends an interaction to the students, telling them to 'learn' from the lecture stream."""
        return True

    @action
    async def mark_lecture_as_finished(self, interaction: Interaction | None = None) -> bool:
        """Callback triggered when a student finished learning."""
        return True

    @action
    async def lecture_finished(self) -> bool:
        """Checks the flag that marks a lecture as finished, moving to the next lecture number."""
        return True

    @action
    async def start_exam_session(self) -> bool:
        """This action prepares the teacher and tells students that the exam is going to start."""
        return True

    @action
    async def hand_out_exam(self) -> bool:
        """This action sends an interaction to the students, telling them to 'process' the exam stream."""
        return True

    @action
    async def mark_exam_as_finished(self, interaction: Interaction | None = None) -> bool:
        """Callback triggered when a student finished the exam."""
        return True

    @action
    async def evaluate_results(self) -> bool:
        """Checks the flag that marks an exam as finished, computes the results, tells students their scores."""
        return True

    @action
    async def ask_for_feedback(self) -> bool:
        """This action prepares the teacher and tells students that the feedback stage is going to start."""
        return True

    @action
    async def send_requests(self) -> bool:
        """This action sends an interaction to the students, telling them to 'process' the feedback-data stream."""
        return True

    @action
    async def mark_feedback_as_provided(self, interaction: Interaction | None = None) -> bool:
        """Callback triggered when a student finished providing feedback."""
        return True

    @action
    async def augment_lectures(self) -> bool:
        """Checks the flag that marks the feedback stage as finished, aggregates feedbacks, augments lectures."""
        return True

    @action
    async def on_data(self, stream_group: str) -> bool:
        """This action is True whenever a new sample is found in our stream group or in one from a student."""
        return True
