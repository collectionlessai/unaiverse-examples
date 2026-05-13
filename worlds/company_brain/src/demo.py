import random
import time as tm
from unaiverse.modules.utils import ModuleWrapper
from unaiverse.streams.dataprops import StreamType
from unaiverse.utils.logger import log
from .brain import WAgent as Agent


# ── Shared index helpers ──────────────────────────────────────────

def read_index(path):
    """Read the current script index from disk."""
    try:
        with open(path, 'r') as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return 0


def write_index(path, value):
    """Write a new script index to disk (atomic enough for single-machine demo)."""
    with open(path, 'w') as f:
        f.write(str(value))


# ── ScriptedModule ────────────────────────────────────────────────

class ScriptedModule(ModuleWrapper):
    """Processor that returns the next scripted message for this agent,
    gated by a shared index file on disk."""

    def __init__(self, script, index_file, agent_name,
                 log_on_finish=None, delay=3.0, delay_variance=1.5):
        super().__init__(
            proc_inputs=[StreamType(data_type="text", pubsub=False, private_only=True)],
            proc_outputs=[StreamType(data_type="text", pubsub=False, private_only=True)]
        )
        self._script = script
        self._index_file = index_file
        self._agent_name = agent_name
        self._log_on_finish = log_on_finish
        self._delay = delay
        self._delay_variance = delay_variance
        self._sent_count = 0
        self._my_total = sum(1 for name, _ in script if name == agent_name)

    # ── accessors for DemoAgent ──
    @property
    def script(self):
        return self._script

    @property
    def index_file(self):
        return self._index_file

    @property
    def agent_name(self):
        return self._agent_name

    def has_next(self):
        return self._sent_count < self._my_total

    def forward(self, msg: str, first: bool = False, last: bool = False):
        idx = read_index(self._index_file)
        if idx < len(self._script):
            sender, text = self._script[idx]
            if sender == self._agent_name:
                # Realistic delay before speaking
                wait = self._delay + random.uniform(-self._delay_variance, self._delay_variance)
                tm.sleep(max(0.5, wait))
                # Advance index AFTER sleep → next agent sees its turn only
                # when this message is about to be dispatched
                write_index(self._index_file, idx + 1)
                self._sent_count += 1
                if not self.has_next() and self._log_on_finish:
                    log.user(self._log_on_finish)
                return text
        # Safety: should never reach here if hooks gate correctly.
        # Return a space to avoid broadcasting an empty string.
        return " "


# ── DemoAgent ─────────────────────────────────────────────────────

class DemoAgent(Agent):
    """Agent that follows a shared script via an index file on disk."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Cache scripted agent names for HUMAN-detection
        self._scripted_names = set(
            name for name, _ in self.proc.script if name != "HUMAN"
        )

    # ── hooks ──

    def hook_on_received_msgs(self, msg_tuples, history_len):
        if self.is_human():
            return
        for msg, _, _ in msg_tuples:
            if not isinstance(msg, str):
                continue
            self._last_msg_time = tm.time()
            self._last_turns.append(msg)
            self._last_turns = self._last_turns[-history_len:]

            # If this message is from the HUMAN player, advance past HUMAN entries
            sender = self.get_sender_name(msg)
            if sender and sender not in self._scripted_names:
                idx = read_index(self.proc.index_file)
                if 0 <= idx < len(self.proc.script) and self.proc.script[idx][0] == "HUMAN":
                    write_index(self.proc.index_file, idx + 1)

        self._check_and_trigger()

    def hook_on_zero_received_msgs(self, max_silence_seconds):
        if self.is_human():
            return
        self._check_and_trigger()

    def _check_and_trigger(self):
        """If it's this agent's turn in the script, trigger do_gen."""
        if not self.proc.has_next():
            return
        idx = read_index(self.proc.index_file)
        if 0 <= idx < len(self.proc.script):
            sender, _ = self.proc.script[idx]
            if sender == self.proc.agent_name:
                self.stdin.set("proc_input_0", "(scripted)")
