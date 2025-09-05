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
from unaiverse.streams.streams import (AllHotLabelStream, SmoothHFHA, SmoothHFLA, SmoothLFHA, SmoothLFLA,
                                               SquareHFHA, SquareHFLA, SquareLFHA, SquareLFLA)


class SignalSchoolRoles:
    # Role bitmasks
    ROLE_TEACHER = 1 << 2
    ROLE_STUDENT = 1 << 3

    # Feasible roles
    ROLE_BITS_TO_STR = {
        # The base roles will be inherited from AgentBasics later
        ROLE_TEACHER: "teacher",
        ROLE_STUDENT: "student",
    }


class WAgent(Agent, SignalSchoolRoles):

    # feasible roles
    ROLE_BITS_TO_STR = {**Agent.ROLE_BITS_TO_STR, **SignalSchoolRoles.ROLE_BITS_TO_STR}
    ROLE_STR_TO_BITS = {v: k for k, v in ROLE_BITS_TO_STR.items()}

    def accept_new_role(self, role: int, default_behav: str | None):
        super().accept_new_role(role, default_behav)

        if ((role >> 2) << 2) == self.ROLE_TEACHER:
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
