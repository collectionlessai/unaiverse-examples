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
from unaiverse.streams import DataStream
from unaiverse.streamlib.streamlib import (AllHotLabelStream, SmoothHFHA, SmoothHFLA, SmoothLFHA, SmoothLFLA,
                                           SquareHFHA, SquareHFLA, SquareLFHA, SquareLFLA)


class WAgent(Agent):

    def accept_new_role(self, role: int):
        super().accept_new_role(role)

        if self.get_current_role() == "teacher":
            self.add_streams([DataStream.create(group="smoHfHa", public=False, stream=SmoothHFHA()),
                              DataStream.create(group="smoHfHa", public=False,
                                                stream=AllHotLabelStream(SmoothHFHA.FEATURES))])
            self.add_streams([DataStream.create(group="smoHfLa", public=False, stream=SmoothHFLA()),
                              DataStream.create(group="smoHfLa", public=False,
                                                stream=AllHotLabelStream(SmoothHFLA.FEATURES))])
            self.add_streams([DataStream.create(group="smoLfHa", public=False, stream=SmoothLFHA()),
                              DataStream.create(group="smoLfHa", public=False,
                                                stream=AllHotLabelStream(SmoothLFHA.FEATURES))])
            self.add_streams([DataStream.create(group="smoLfLa", public=False, stream=SmoothLFLA()),
                              DataStream.create(group="smoLfLa", public=False,
                                                stream=AllHotLabelStream(SmoothLFLA.FEATURES))])
            self.add_streams([DataStream.create(group="squHfHa", public=False, stream=SquareHFHA()),
                              DataStream.create(group="squHfHa", public=False,
                                                stream=AllHotLabelStream(SquareHFHA.FEATURES))])
            self.add_streams([DataStream.create(group="squHfLa", public=False, stream=SquareHFLA()),
                              DataStream.create(group="squHfLa", public=False,
                                                stream=AllHotLabelStream(SquareHFLA.FEATURES))])
            self.add_streams([DataStream.create(group="squLfHa", public=False, stream=SquareLFHA()),
                              DataStream.create(group="squLfHa", public=False,
                                                stream=AllHotLabelStream(SquareLFHA.FEATURES))])
            self.add_streams([DataStream.create(group="squLfLa", public=False, stream=SquareLFLA()),
                              DataStream.create(group="squLfLa", public=False,
                                                stream=AllHotLabelStream(SquareLFLA.FEATURES))])

            self.update_streams_in_profile()
