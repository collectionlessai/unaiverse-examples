"""
 █████  █████ ██████   █████           █████ █████   █████ ██████████ ███████████    █████████  ██████████
░░███  ░░███ ░░██████ ░░███           ░░███ ░░███   ░░███ ░░███░░░░░█░░███░░░░░███  ███░░░░░███░░███░░░░░█
 ░███   ░███  ░███░███ ░███   ██████   ░███  ░███    ░███  ░███  █ ░  ░███    ░███ ░███    ░░░  ░███  █ ░ 
 ░███   ░███  ░███░░███░███  ░░░░░███  ░███  ░███    ░███  ░██████    ░██████████  ░░█████████  ░██████   
 ░███   ░███  ░███ ░░██████   ███████  ░███  ░░███   ███   ░███░░█    ░███░░░░░███  ░░░░░░░░███ ░███░░█   
 ░███   ░███  ░███  ░░█████  ███░░███  ░███   ░░░█████░    ░███ ░   █ ░███    ░███  ███    ░███ ░███ ░   █
 ░░████████   █████  ░░█████░░████████ █████    ░░███      ██████████ █████   █████░░█████████  ██████████
  ░░░░░░░░   ░░░░░    ░░░░░  ░░░░░░░░ ░░░░░      ░░░      ░░░░░░░░░░ ░░░░░   ░░░░░  ░░░░░░░░░  ░░░░░░░░░░ 

~ Registration/Login: https://unaiverse.io
~ Code Repositories:  https://github.com/collectionlessai/
~ Main Developers:    Stefano Melacci (Project Leader), Christian Di Maio, Tommaso Guidi

A Collectionless AI Project (https://collectionless.ai)
"""
import os
from unaiverse.world import World
from agent import WAgent, IERoles
from unaiverse.dataprops import DataProps
from unaiverse.hsm import HybridStateMachine
from unaiverse.networking.node.profile import NodeProfile


class WWorld(World, IERoles):

    # feasible roles
    ROLE_BITS_TO_STR = {**World.ROLE_BITS_TO_STR, **IERoles.ROLE_BITS_TO_STR}
    ROLE_STR_TO_BITS = {v: k for k, v in ROLE_BITS_TO_STR.items()}

    def __init__(self, *args, **kwargs):

        # dynamically re-create the behaviour files (not formally needed, just for easier develop)
        WWorld.__create_behav_files()

        # guess the name of the folder containing this world
        world_folder_name = os.path.basename(os.path.dirname(__file__))

        # building world
        super().__init__(*args,
                         agent_actions=os.path.join(world_folder_name, 'agent.py'),
                         role_to_behav={self.ROLE_BITS_TO_STR[self.ROLE_USER]: os.path.join(world_folder_name, 'behav_user.json'),
                                        self.ROLE_BITS_TO_STR[self.ROLE_EXTRACTOR]: os.path.join(world_folder_name, 'behav_extractor.json')},
                         **kwargs)

    def assign_role(self, profile: NodeProfile, is_world_master: bool):
        dynamic_profile = profile.get_dynamic_profile()
        offers_img_stream = False
        if 'streams' in dynamic_profile and dynamic_profile['streams'] is not None:
            environmental_streams = dynamic_profile['streams']

            for environmental_stream in environmental_streams:
                environmental_stream_props = DataProps.from_dict(environmental_stream)
                if environmental_stream_props.is_img() and not environmental_stream_props.is_public():
                    offers_img_stream = True
                    break

        if offers_img_stream:
            return self.ROLE_USER
        else:
            out_text = False
            in_img = False

            proc_inputs = dynamic_profile['proc_inputs']
            proc_outputs = dynamic_profile['proc_outputs']

            if proc_inputs is not None:
                for proc_input in proc_inputs:
                    proc_input_props = DataProps.from_dict(proc_input)
                    if proc_input_props.is_img() and not proc_input_props.is_public():
                        in_img = True
                        break

            if proc_outputs is not None:
                for proc_output in proc_outputs:
                    proc_output_props = DataProps.from_dict(proc_output)
                    if not proc_output_props.is_public():
                        if (proc_output_props.is_text() or
                                (proc_output_props.is_tensor() and proc_output_props.has_tensor_labels())):
                            out_text = True
                            break

            if in_img and out_text:
                return self.ROLE_EXTRACTOR
        return -1  # no role

    @staticmethod
    def __create_behav_files():
        path_of_this_file = os.path.dirname(os.path.abspath(__file__))
        dummy_agent = WAgent(proc=None)

        # ROLE 1/2: user
        behav = HybridStateMachine(dummy_agent)
        behav.set_role(dummy_agent.ROLE_BITS_TO_STR[WAgent.ROLE_USER])

        # let's wait a little bit before moving from init to the ready state of the service_requester.json, so that,
        # meanwhile, this agent will become known to the others...
        behav.add_transit("init",
                          os.path.join(path_of_this_file, "..", "..", "behaviors", "service_requester.json"),
                          action="nop", args={})
        behav.add_state("ready", action="check_status")

        behav.add_wildcards({"<provider_role>": WWorld.ROLE_BITS_TO_STR[WWorld.ROLE_EXTRACTOR],
                             "<providers_filter_fcn>": "filter_addresses",
                             "<providers_data_processing_fcn>": "handle_received_data"})

        # messages
        behav.add_state("ready", msg="🔍 Looking for new agents for information exaction")
        behav.add_state("connected_to_providers", msg="🔗 Connected to new agents")
        behav.add_state("time_to_ask", msg="🙋 Asking new agents to handle my stream of data")
        behav.add_state("request_handled_by_a_provider",
                        msg="✅ An agent finished its job (good or bad), waiting others (if any)")

        # saving to file
        if behav.save(os.path.join(path_of_this_file, 'behav_user.json'), only_if_changed=dummy_agent):
            os.makedirs(os.path.join(path_of_this_file, 'pdf'), exist_ok=True)
            behav.save_pdf(os.path.join(path_of_this_file, 'pdf', 'behav_user.pdf'))

        # ROLE 2/2: extractor
        behav = HybridStateMachine(dummy_agent)
        behav.set_role(dummy_agent.ROLE_BITS_TO_STR[WAgent.ROLE_EXTRACTOR])

        behav.add_transit("init",
                          os.path.join(path_of_this_file, "..", "..", "behaviors", "service_provider.json"),
                          action="nop", args={})

        behav.add_wildcards({"<user_role>": WWorld.ROLE_BITS_TO_STR[WWorld.ROLE_USER]})

        # saving to file
        if behav.save(os.path.join(path_of_this_file, 'behav_extractor.json'), only_if_changed=dummy_agent):
            os.makedirs(os.path.join(path_of_this_file, 'pdf'), exist_ok=True)
            behav.save_pdf(os.path.join(path_of_this_file, 'pdf', 'behav_extractor.pdf'))
