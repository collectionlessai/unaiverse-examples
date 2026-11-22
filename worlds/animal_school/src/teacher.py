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
from unaiverse.agent import Agent, action
from unaiverse.interaction import Interaction

# Seconds between two samples of the recorded streams, when the teacher plays them to the students (lectures and the
# exam). Slower than the clock of the nodes (1/100 s), so a student gets each sample in a tick of its own: a sample
# arriving in the same tick as the next one is replaced by it, and its answer would be missing in the exam.
RECORDED_DELTA = 1. / 25.


class WAgent(Agent):
    """The teacher: it records the streams of the world, then teaches and examines the students with them."""

    @action
    async def record(self, interaction: Interaction | None = None,
                     record_uuid: str | None = "see_interaction_uuid") -> bool:
        """The built-in record; once the recording is complete, the recorded streams get their own pace (async).

        The recorded streams are clones of the streams of the world, whose delta is cleared on this side (they are
        streams of another node), so the pace is set here, after the last step (not before: it would also slow
        down the recording).

        Args:
            interaction: The interaction of the step.
            record_uuid: As for the built-in record.

        Returns:
            True when the step was recorded.
        """
        ok = await super().record(interaction=interaction, record_uuid=record_uuid)
        if not (ok and interaction is not None and interaction.was_last_step_done()):
            return ok
        for streams in self.owned_streams.values():
            for stream in streams.values():
                if stream.props.get_group().startswith("recorded") and stream.props.delta <= 0.:
                    stream.props.set_delta(RECORDED_DELTA)
        return ok
