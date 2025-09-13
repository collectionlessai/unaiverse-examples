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
from unaiverse.world import World
from unaiverse.dataprops import DataProps
from unaiverse.hsm import HybridStateMachine
from unaiverse.networking.node.profile import NodeProfile


class WWorld(World):

    def __init__(self, **kwargs):
        super().__init__(world_folder=os.path.dirname(os.path.abspath(__file__)), **kwargs)

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
            return "user"
        else:
            out_text = False
            in_img = False

            proc_inputs = dynamic_profile['proc_inputs']
            proc_outputs = dynamic_profile['proc_outputs']

            if proc_inputs is not None:
                for proc_input in proc_inputs:
                    proc_input_props = DataProps.from_dict(proc_input)
                    if (proc_input_props.is_img() or proc_input_props.is_all()) and not proc_input_props.is_public():
                        in_img = True
                        break

            if proc_outputs is not None:
                for proc_output in proc_outputs:
                    proc_output_props = DataProps.from_dict(proc_output)
                    if not proc_output_props.is_public():
                        if (proc_output_props.is_text() or proc_output_props.is_all() or
                                (proc_output_props.is_tensor() and proc_output_props.has_tensor_labels())):
                            out_text = True
                            break

            if in_img and out_text:
                return "extractor"
        return None  # No role

    def create_behav_files(self):
        """Create role-behavior JSON files: if you manually create the JSON files, no need to implement this method."""

        # Creating a dummy agent to check actions
        import sys
        sys.path.append(self.world_folder)
        from agent import WAgent
        dummy_agent = WAgent(proc=None)

        # ROLE 1/2: user
        behav = HybridStateMachine(dummy_agent)
        behav.set_role("user")

        # Let's wait a little bit before moving from init to the ready state of the service_requester.json, so that,
        # meanwhile, this agent will become known to the others...
        behav.add_transit("init",
                          os.path.join(self.world_folder, "..", "..", "..", "behaviors", "service_requester.json"),
                          action="nop", args={})
        behav.add_state("ready", action="check_status")

        behav.add_wildcards({"<provider_role>": "extractor",
                             "<providers_filter_fcn>": "filter_addresses",
                             "<providers_data_processing_fcn>": "handle_received_data"})

        # Messages
        behav.add_state("ready", msg="🔍 Looking for new agents for information exaction")
        behav.add_state("connected_to_providers", msg="🔗 Connected to new agents")
        behav.add_state("time_to_ask", msg="🙋 Asking new agents to handle my stream of data")
        behav.add_state("request_handled_by_a_provider",
                        msg="✅ An agent finished its job (good or bad), waiting others (if any)")

        # Saving to file
        behav.save(os.path.join(self.world_folder, 'user.json'), only_if_changed=dummy_agent)

        # ROLE 2/2: extractor
        behav = HybridStateMachine(dummy_agent)
        behav.set_role("extractor")

        behav.add_transit("init",
                          os.path.join(self.world_folder, "..", "..", "..", "behaviors", "service_provider.json"),
                          action="nop", args={})

        behav.add_wildcards({"<user_role>": "user"})

        # Saving to file
        behav.save(os.path.join(self.world_folder, 'extractor.json'), only_if_changed=dummy_agent)
