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
from unaiverse.agent import Agent
from unaiverse.streams import Stream
from unaiverse.streams.streamlib import (AllHotLabelStream, SmoothHFHA, SmoothHFLA, SmoothLFHA, SmoothLFLA,
                                         SquareHFHA, SquareHFLA, SquareLFHA, SquareLFLA)


# Seconds between two samples of the lecture streams: the stream sets its own pace, slower than the clock cycle
SIGNAL_DELTA = 1. / 25.


class WAgent(Agent):
    """Teacher-side override. The signal-generator streams are added on role acceptance (teacher only) so
    that the playlist `<agent>:smoHfHa`, `<agent>:smoHfLa`, ... resolves at runtime to the teacher's own
    owned streams."""

    def accept_new_role(self, role: int):
        super().accept_new_role(role)

        if self.get_current_role() == "teacher":
            self.add_streams([Stream.create(group="smoHfHa", public=False, delta=SIGNAL_DELTA, stream=SmoothHFHA()),
                              Stream.create(group="smoHfHa", public=False, delta=SIGNAL_DELTA,
                                            stream=AllHotLabelStream(SmoothHFHA.FEATURES))])
            self.add_streams([Stream.create(group="smoHfLa", public=False, delta=SIGNAL_DELTA, stream=SmoothHFLA()),
                              Stream.create(group="smoHfLa", public=False, delta=SIGNAL_DELTA,
                                            stream=AllHotLabelStream(SmoothHFLA.FEATURES))])
            self.add_streams([Stream.create(group="smoLfHa", public=False, delta=SIGNAL_DELTA, stream=SmoothLFHA()),
                              Stream.create(group="smoLfHa", public=False, delta=SIGNAL_DELTA,
                                            stream=AllHotLabelStream(SmoothLFHA.FEATURES))])
            self.add_streams([Stream.create(group="smoLfLa", public=False, delta=SIGNAL_DELTA, stream=SmoothLFLA()),
                              Stream.create(group="smoLfLa", public=False, delta=SIGNAL_DELTA,
                                            stream=AllHotLabelStream(SmoothLFLA.FEATURES))])
            self.add_streams([Stream.create(group="squHfHa", public=False, delta=SIGNAL_DELTA, stream=SquareHFHA()),
                              Stream.create(group="squHfHa", public=False, delta=SIGNAL_DELTA,
                                            stream=AllHotLabelStream(SquareHFHA.FEATURES))])
            self.add_streams([Stream.create(group="squHfLa", public=False, delta=SIGNAL_DELTA, stream=SquareHFLA()),
                              Stream.create(group="squHfLa", public=False, delta=SIGNAL_DELTA,
                                            stream=AllHotLabelStream(SquareHFLA.FEATURES))])
            self.add_streams([Stream.create(group="squLfHa", public=False, delta=SIGNAL_DELTA, stream=SquareLFHA()),
                              Stream.create(group="squLfHa", public=False, delta=SIGNAL_DELTA,
                                            stream=AllHotLabelStream(SquareLFHA.FEATURES))])
            self.add_streams([Stream.create(group="squLfLa", public=False, delta=SIGNAL_DELTA, stream=SquareLFLA()),
                              Stream.create(group="squLfLa", public=False, delta=SIGNAL_DELTA,
                                            stream=AllHotLabelStream(SquareLFLA.FEATURES))])

            self.update_streams_in_profile()
