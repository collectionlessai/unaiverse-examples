import time as tm
from unaiverse.modules.utils import ModuleWrapper
from unaiverse.streams.dataprops import StreamType
from unaiverse.utils.logger import log
from .brain import WAgent as Agent


class ScriptedModule(ModuleWrapper):

    def __init__(self, messages, log_on_finish=None):
        super().__init__(
            proc_inputs=[StreamType(data_type="text", pubsub=False, private_only=True)],
            proc_outputs=[StreamType(data_type="text", pubsub=False, private_only=True)]
        )
        self._messages = list(messages)
        self._index = 0
        self._log_on_finish = log_on_finish

    def has_next(self):
        return self._index < len(self._messages)

    def forward(self, msg: str, first: bool = False, last: bool = False):
        if self._index < len(self._messages):
            out = self._messages[self._index]
            self._index += 1
            if not self.has_next() and self._log_on_finish:
                log.user(self._log_on_finish)
            return out
        return ""


class DemoAgent(Agent):

    def __init__(self, *args, auto_start=False, respond_to_any=False,
                 silence_delay=30.0, **kwargs):
        super().__init__(*args, **kwargs)
        self._auto_start = auto_start
        self._respond_to_any = respond_to_any
        self._silence_delay = silence_delay
        self._fired_auto = False

    def hook_on_received_msgs(self, msg_tuples, history_len):
        if self.is_human():
            return
        for msg, _, _ in msg_tuples:
            if not isinstance(msg, str):
                continue
            self._last_msg_time = tm.time()
            self._last_turns.append(msg)
            self._last_turns = self._last_turns[-history_len:]
            if not self.proc.has_next():
                continue
            my_name = self.get_name().lower()
            if self._respond_to_any or (my_name in msg.lower()):
                self.stdin.set("proc_input_0", msg)
                break

    def hook_on_zero_received_msgs(self, max_silence_seconds):
        if self.is_human() or not self._auto_start or self._fired_auto:
            return
        if not self.proc.has_next():
            return
        if (tm.time() - self._last_msg_time) > self._silence_delay:
            self._fired_auto = True
            self.stdin.set("proc_input_0", "(auto)")
