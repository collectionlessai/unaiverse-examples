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
from .stats import WStats
from unaiverse.world import World
from unaiverse.hsm import HybridStateMachine
from unaiverse.networking.node.profile import NodeProfile


class WWorld(World):

    def __init__(self, **kwargs):
        world_folder = os.path.dirname(os.path.abspath(__file__))
        stats = WStats(is_world=True, db_path=os.path.join(world_folder, "stats", "world_stats.db"))
        super().__init__(world_folder=world_folder, stats=stats, **kwargs)

    def assign_role(self, profile: NodeProfile, is_world_master: bool):
        if is_world_master:
            if len(self.world_masters) <= 1:
                return "manager"
            else:
                return "participant"
        else:
            return "participant"

    def create_behav_files(self):
        """Create role-behavior JSON files: if you manually create the JSON files, no need to implement this method."""

        # Creating a dummy agent to check actions
        import sys
        sys.path.append(self.world_folder)
        from agent import WAgent
        dummy_agent = WAgent(proc=None)

        # Custom parameters
        test_duration = WAgent.test_duration  # Seconds
        survey_reply_time = WAgent.survey_reply_time  # Seconds

        # ROLE 1/2: participant
        behav = HybridStateMachine(dummy_agent)
        behav.set_role("participant")

        behav.add_state("set_email", action="set_email", blocking=False)
        behav.add_state("init_message", blocking=False, msg=WAgent.init_message)
        behav.add_state("ready", blocking=False)
        behav.add_state("hall", blocking=False, action="hall",
                        msg="🏢 In the hall, waiting to be checked-in <eta_time>")
        behav.add_state("in_room", blocking=False,
                        msg=f"🚪 In your room, waiting until there are {WAgent.guests_per_room} "
                            f"participants (missing <eta_part>)")
        behav.add_state("ready_to_chat", action="ready_to_chat", blocking=False)
        behav.add_state("chatting", action="get_messages", blocking=True)
        behav.add_state("message_prepared", action="message_prepared", blocking=False)
        behav.add_state("ready_for_survey", blocking=False)
        behav.add_state("replied_to_survey", blocking=False)
        behav.add_transit("set_email", "init_message", action="nop")
        behav.add_transit("init_message", "ready",
                          action="do_gen", args={"u_hashes": ["<agent>:processor_in"], "samples": 1}, ready=True,
                          avoid_changing_ready=True)
        behav.add_transit("init_message", "ready", action="skip_confirmation")
        behav.add_transit("ready", "hall", action="connect_to_manager",
                          msg="🔗 Connecting to manager...")
        behav.add_transit("hall", "ready", action="manager_is_disconnected", args={"delay": 5.0})
        behav.add_transit("hall", "in_room", action="join_room",
                          args={"missing": "<eta_part>"}, ready=False,
                          msg=f"🚪 Joining room")
        behav.add_transit("in_room", "hall", action="leave_room", ready=False,
                          msg="🚪 Leaving room")
        behav.add_transit("in_room", "chatting", action="start", ready=False,
                          msg="🚪 Starting the chat (wait for the message from the manager)")
        behav.add_transit("chatting", "ready", action="lost",
                          args={"delay": test_duration + 20.},
                          msg="⏱️Lost sync with the room (disconnecting)")
        behav.add_transit("chatting", "chatting", action="wait_for_intro")
        behav.add_transit("chatting", "message_prepared",
                          action="do_gen", args={"u_hashes": ["<agent>:processor_in"], "samples": 1}, ready=True,
                          avoid_changing_ready=True)
        behav.add_transit("chatting", "ready_for_survey", action="stop", ready=False,
                          msg="📋 You will be able to provide your feedback to the final survey shortly "
                              "(wait for the request from the manager)")
        behav.add_transit("ready_for_survey", "hall", action="leave_room", ready=False,
                          msg="🚪 Leaving room")
        behav.add_transit("ready_for_survey", "ready",
                          action="lost", args={"delay": survey_reply_time + 10.},
                          msg="⏱️Lost sync with the room (disconnecting)")
        behav.add_transit("ready_for_survey", "replied_to_survey",
                          action="do_gen", args={"u_hashes": ["<agent>:processor_in"], "samples": 1}, ready=False)
        behav.add_transit("message_prepared", "ready_to_chat",
                          action="ask_gen", args={"u_hashes": ["<agent>:processor"], "samples": 1,
                                                  "from_state": "collect_messages", "ask_uuid": "s4m344ll"})
        behav.add_transit("ready_to_chat", "chatting", action="nop")
        behav.add_transit("replied_to_survey", "hall", action="leave_room", ready=False,
                          msg="🚪 Leaving room")
        behav.add_transit("replied_to_survey", "ready",
                          action="lost", args={"delay": survey_reply_time + 10.},
                          msg="⏱️Lost sync with the room (disconnecting)")
        behav.add_transit("chatting", "hall", action="leave_room", ready=False,
                          msg="🚪 Leaving room")
        behav.add_transit("hall", "hall", action="status", ready=False)

        # Saving to file
        behav.save(os.path.join(self.world_folder, 'participant.json'), only_if_changed=dummy_agent)

        # ROLE 2/2: manager
        behav = HybridStateMachine(dummy_agent)
        behav.set_welcome_message("Welcome to the Turing Hotel 🏨, we always need more managers, "
                                  "happy to have you here!")
        behav.set_role("manager")

        behav.add_state("sending_messages", blocking=True, msg="🚚 Sending collected messages and surveys")
        behav.add_state("rooms_assigned", blocking=False)
        behav.add_state("rooms_checked", blocking=False)
        behav.add_state("collect_messages", blocking=False, msg="📦 Collecting and preparing messages")
        behav.add_state("ready_to_send", action="ready_to_send", blocking=False,
                        msg="📋 Ready to send the collected messages and/or surveys (got feedbacks too, if any)")
        behav.add_state("survey_requests_sent", action="survey_requests_sent", blocking=False,
                        msg="📋 Survey requests sent")
        behav.add_transit("sending_messages", "rooms_assigned", action="assign_to_rooms",
                          msg="🚪 Assigning guests to rooms")
        behav.add_transit("rooms_assigned", "rooms_checked", action="check_rooms",
                          msg="🚪 Checking rooms")
        behav.add_transit("rooms_checked", "collect_messages", action="nop")
        behav.add_transit("collect_messages", "collect_messages",
                          action="do_gen", args={"samples": 1}, ready=False)
        behav.add_transit("collect_messages", "ready_to_send",
                          action="prepare_surveys_and_get_feedbacks",
                          msg="📋 Preparing surveys and taking notes of the received feedbacks (if any)")
        behav.add_transit("ready_to_send", "survey_requests_sent",
                          action="ask_gen",
                          args={"ask_uuid": "5urv3y", "samples": 1, "from_state": "ready_for_survey"},
                          msg="🚚 Sending requests for surveys (if any)")
        behav.add_transit("ready_to_send", "sending_messages", action="nop")
        behav.add_transit("survey_requests_sent", "sending_messages", action="nop")

        # Saving to file
        behav.save(os.path.join(self.world_folder, 'manager.json'), only_if_changed=dummy_agent)
