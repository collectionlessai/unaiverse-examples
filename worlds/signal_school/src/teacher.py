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


class WAgent(Agent):
    """Teacher-side override. The signal-generator streams are added on role acceptance (teacher only) so
    that the playlist `<agent>:smoHfHa`, `<agent>:smoHfLa`, ... resolves at runtime to the teacher's own
    owned streams."""

    def accept_new_role(self, role: int):
        super().accept_new_role(role)

        if self.get_current_role() == "teacher":
            self.add_streams([Stream.create(group="smoHfHa", public=False, stream=SmoothHFHA()),
                              Stream.create(group="smoHfHa", public=False,
                                            stream=AllHotLabelStream(SmoothHFHA.FEATURES))])
            self.add_streams([Stream.create(group="smoHfLa", public=False, stream=SmoothHFLA()),
                              Stream.create(group="smoHfLa", public=False,
                                            stream=AllHotLabelStream(SmoothHFLA.FEATURES))])
            self.add_streams([Stream.create(group="smoLfHa", public=False, stream=SmoothLFHA()),
                              Stream.create(group="smoLfHa", public=False,
                                            stream=AllHotLabelStream(SmoothLFHA.FEATURES))])
            self.add_streams([Stream.create(group="smoLfLa", public=False, stream=SmoothLFLA()),
                              Stream.create(group="smoLfLa", public=False,
                                            stream=AllHotLabelStream(SmoothLFLA.FEATURES))])
            self.add_streams([Stream.create(group="squHfHa", public=False, stream=SquareHFHA()),
                              Stream.create(group="squHfHa", public=False,
                                            stream=AllHotLabelStream(SquareHFHA.FEATURES))])
            self.add_streams([Stream.create(group="squHfLa", public=False, stream=SquareHFLA()),
                              Stream.create(group="squHfLa", public=False,
                                            stream=AllHotLabelStream(SquareHFLA.FEATURES))])
            self.add_streams([Stream.create(group="squLfHa", public=False, stream=SquareLFHA()),
                              Stream.create(group="squLfHa", public=False,
                                            stream=AllHotLabelStream(SquareLFHA.FEATURES))])
            self.add_streams([Stream.create(group="squLfLa", public=False, stream=SquareLFLA()),
                              Stream.create(group="squLfLa", public=False,
                                            stream=AllHotLabelStream(SquareLFLA.FEATURES))])

            self.update_streams_in_profile()
