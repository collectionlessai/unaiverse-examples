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
from unaiverse.agent import Agent, action
from unaiverse.interaction import Interaction
from unaiverse.streams import ImageFileStream, StringStream


class WAgent(Agent):
    """Teacher agent."""

    LECTURE_SAMPLES = 6
    LECTURE_MAX_DURATION = 20.
    EXAM_SAMPLES = 6
    EXAM_MAX_DURATION = 30.
    FEEDBACK_SAMPLES = 2
    FEEDBACK_MAX_DURATION = 30.

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # Status
        self.current_lecture_num = 1
        self.current_lecture_finished = False
        self.current_exam_finished = False
        self.current_feedback_provided = False

    def accept_new_role(self, role: int):
        """Build streams once the role is assigned."""
        super().accept_new_role(role)

        # Reading file names in data/lectures
        def collect_file_names_and_class_names(path: str) -> tuple[list[str], list[str]]:
            _files_per_class = defaultdict(list)
            _folder = os.path.join(str(os.path.abspath(__file__)), path)
            _file_names = []
            _class_names = []
            for _file_name in sorted(os.listdir(_folder)):
                if not _file_name.lower().endswith(".jpg"):
                    continue
                if "_" in _file_name:
                    _class_name = _file_name.rsplit("_", 1)[0]  # "Empoleon_001.jpg" -> "Empoleon"
                else:
                    _class_name = "unknown"
                _file_names.append(_file_name)
                _class_names.append(_class_name)
            return _file_names, _class_names

        # Reading files of the three lectures
        for i in range(1, 4):
            folder = os.path.join("data", "lectures", str(i))
            file_names, class_names = collect_file_names_and_class_names(folder)

            # Creating one stream per lecture
            self.add_streams([Stream.create(stream=ImageFileStream(folder, file_names, circular=True),
                                            group="lecture" + str(i),
                                            name="images",
                                            pubsub=True,
                                            delta=2.0),
                              Stream.create(stream=StringStream(class_names, circular=True),
                                            group="lecture" + str(i),
                                            name="class_names",
                                            pubsub=True,
                                            delta=2.0)
                              ])

        # Reading exam files
        folder = os.path.join("data", "exam")
        file_names, class_names = collect_file_names_and_class_names(folder)

        # Creating exam stream
        self.add_streams([Stream.create(stream=ImageFileStream(folder, file_names, circular=True),
                                        group="exam",
                                        name="images",
                                        pubsub=True,
                                        delta=2.0),
                          Stream.create(stream=StringStream(class_names, circular=True),
                                        group="exam",
                                        name="class_names",
                                        pubsub=True,
                                        delta=2.0)])

        # Reading feedback (unlabeled) files
        folder = os.path.join("data", "feedback")
        file_names, _ = collect_file_names_and_class_names(folder)

        # Creating feedback (unlabeled) image stream
        self.add_stream(Stream.create(stream=ImageFileStream(folder, file_names, circular=True),
                                      group="feedback",
                                      name="images",
                                      pubsub=True,
                                      delta=2.0))

        # Refresh streams in profile
        self.update_streams_in_profile()

    async def on_tick(self):
        await super().on_tick()

    @action
    async def reset_status(self):
        self.current_lecture_num = 1
        self.current_lecture_finished = False
        self.current_exam_finished = False
        self.current_feedback_provided = False

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
                                              "stdin": [f"lecture{self.current_lecture_num}/images"],
                                              "stdtar": [f"lecture{self.current_lecture_num}/class_names"]
                                          },
                                          num_steps=self.LECTURE_SAMPLES,
                                          timeout=self.LECTURE_MAX_DURATION,
                                          callback=self.mark_lecture_as_finished)

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

        # Resetting mark
        self.current_exam_finished = False

        # If there are no students, well, nothing to do
        students = self.get_agents_by_role("student")
        if len(students) == 0:
            return False

        # If there are students, let's ask them to 'process', in order to make predictions on the exam data!
        return await self.send(action_name="process",
                               from_state="in_class",
                               target=students,
                               streams={
                                   "stdin": [f"exam/images"],
                                   "stdtar": [f"exam/class_names"]
                               },
                               num_steps=self.EXAM_SAMPLES,
                               timeout=self.EXAM_MAX_DURATION,
                               callback=self.mark_exam_as_finished)

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
        # TODO evaluate exam results here, and save them to an attribute, if self.current_exam_finished is True
        return self.current_exam_finished

    @action
    async def ask_feedback(self) -> bool:

        # Resetting mark
        self.current_feedback_provided = False

        # If there are no students, well, nothing to do
        students = self.get_agents_by_role("student")
        if len(students) == 0:
            return False

        # If there are students, let's ask them to 'process', in order to make predictions on the exam data!
        return await self.send(action_name="process",
                               from_state="feedback_time",
                               target=students,
                               streams={
                                   "stdin": [f"feedback/images"],
                               },
                               num_steps=self.FEEDBACK_SAMPLES,
                               timeout=self.FEEDBACK_MAX_DURATION,
                               callback=self.mark_exam_as_finished)

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
        # TODO check feedbacks, aggregate result, augment lecture streams, if self.current_feedback_provided is True
        return self.current_feedback_provided
