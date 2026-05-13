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
        log.error(f"[DEMO] read_index: failed to read index from {path}, defaulting to 0")
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
        log.error(f"[DEMO] ScriptedModule init: agent_name={agent_name}, my_total={self._my_total}")

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
        log.error(f"[DEMO] forward() called: agent={self._agent_name}, msg_in={msg[:30]}")
        idx = read_index(self._index_file)
        log.error(f"[DEMO] forward() called: agent={self._agent_name}, idx={idx}, msg_in={msg[:30]}")
        if idx < len(self._script):
            sender, text = self._script[idx]
            if sender == self._agent_name:
                # Realistic delay before speaking
                wait = self._delay + random.uniform(-self._delay_variance, self._delay_variance)
                log.error(f"[DEMO] {self._agent_name} sleeping {wait:.1f}s then sending msg #{idx}")
                tm.sleep(max(0.5, wait))
                # Advance index AFTER sleep → next agent sees its turn only
                # when this message is about to be dispatched
                write_index(self._index_file, idx + 1)
                self._sent_count += 1
                if not self.has_next() and self._log_on_finish:
                    log.user(self._log_on_finish)
                return text
            else:
                log.error(f"[DEMO] forward() MISMATCH: idx={idx} sender={sender} != {self._agent_name}")
        else:
            log.error(f"[DEMO] forward() idx={idx} OUT OF RANGE (script len={len(self._script)})")
        # Safety: should never reach here if hooks gate correctly.
        # Return a space to avoid broadcasting an empty string.
        return " "


# ── DemoAgent ─────────────────────────────────────────────────────

class DemoAgent(Agent):
    """Agent that follows a shared script via an index file on disk."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Cache scripted agent names for HUMAN-detection
        # Strip trailing colon+space from dispatcher-formatted names
        if hasattr(self.proc, "module") and hasattr(self.proc.module, "_script"):
            self._scripted_names = set(
                name for name, _ in self.proc.module._script if name != "HUMAN"
            )
        log.error(f"[DEMO] DemoAgent init: is_human={self.is_human()}, scripted_names={self._scripted_names}")

    # ── hooks ──

    def hook_on_received_msgs(self, msg_tuples, history_len):
        log.error(f"[DEMO] hook_on_received_msgs: {self.proc.agent_name}, is_human={self.is_human()}, n_msgs={len(msg_tuples)}")
        if self.is_human():
            return
        for msg, _, _ in msg_tuples:
            if not isinstance(msg, str):
                continue
            self._last_msg_time = tm.time()
            self._last_turns.append(msg)
            self._last_turns = self._last_turns[-history_len:]

            # If this message is from the HUMAN player, advance past HUMAN entries
            raw_sender = self.get_sender_name(msg)
            # get_sender_name returns "Name:" (with colon) — strip it
            sender = raw_sender.rstrip(":").strip() if raw_sender else None
            if sender and sender not in self._scripted_names:
                idx = read_index(self.proc.index_file)
                if 0 <= idx < len(self.proc.module.script) and self.proc.module.script[idx][0] == "HUMAN":
                    log.error(f"[DEMO] {self.proc.agent_name}: human msg from '{sender}', advancing idx {idx} → {idx+1}")
                    write_index(self.proc.index_file, idx + 1)

        self._check_and_trigger()

    def hook_on_zero_received_msgs(self, max_silence_seconds):
        log.error(f"[DEMO] hook_on_zero_received_msgs: {self.proc.agent_name}, is_human={self.is_human()}")
        if self.is_human():
            return
        self._check_and_trigger()

    def _check_and_trigger(self):
        """If it's this agent's turn in the script, trigger do_gen."""
        idx = read_index(self.proc.index_file)
        log.error(f"[DEMO] _check_and_trigger: {self.proc.agent_name}, has_next={self.proc.has_next()}, idx={idx}")
        if not self.proc.has_next():
            return
        idx = read_index(self.proc.index_file)
        if 0 <= idx < len(self.proc.module.script):
            sender, _ = self.proc.module.script[idx]
            if sender == self.proc.agent_name:
                log.error(f"[DEMO] _check_and_trigger: {self.proc.agent_name} triggering at idx={idx}")
                self.stdin.set("proc_input_0", "(scripted)")
