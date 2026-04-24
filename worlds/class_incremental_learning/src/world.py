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
from unaiverse.utils.logger import log
from unaiverse.hsm import HybridStateMachine
from unaiverse.networking.node.profile import NodeProfile
from unaiverse.utils.misc import build_unaid

class WWorld(World):
    def __init__(self, **kwargs):
        world_folder = os.path.dirname(os.path.abspath(__file__))
        super().__init__(world_folder=world_folder, **kwargs)

    def assign_role(self, profile: NodeProfile, is_world_master: bool):
        if is_world_master:
            if len(self.world_masters) <= 1:
                return "teacher"
            else:
                return "student"
        else:
            if 'tmp_role_preference' in profile.get_dynamic_profile():
                role_preference = profile.get_dynamic_profile()['tmp_role_preference']
                if role_preference == "student":
                    return "student"
                else:
                    return "student"
            else:
                return "student"

    def create_behav_files(self):
        """Create role-behavior JSON files: if you manually create the JSON files, no need to implement this method."""

        # Creating a dummy agent to check actions
        import sys
        sys.path.append(self.world_folder)

        # Configuration

        # ROLE 1/3: teacher
        from .teacher import WAgent
        dummy_agent = WAgent(proc=None)
        behav = HybridStateMachine(dummy_agent)
        behav.load(os.path.join(self.world_folder, 'teacher.json'))  # Loading the state machine from file, to avoid having to re-implement it here

        # Saving to file
        behav.save_pdf(os.path.join(self.world_folder, 'src/teacher.pdf'))
        
        # ROLE 2/3: student
        from .student import WAgent
        dummy_agent = WAgent(proc=None)
        behav = HybridStateMachine(dummy_agent)
        behav.load(os.path.join(self.world_folder, 'student.json'))  # Loading the state machine from file, to avoid having to re-implement it here

        # Saving to file
        behav.save_pdf(os.path.join(self.world_folder, 'src/student.pdf'))
        
    def _process_custom_stat(self, stat_name, value, peer_id, timestamp):
        # handle the special case of best_exam_err_history
        if stat_name != 'accuracy':
            return False
        
        # the world will store this stat as an ungrouped one, substituting its own peer_id
        # store the new value (this stat will be ungrouped in the world)
        world_peer_id = self.get_peer_ids()[1]
        self.stats.store_stat('accuracy', value, group_key=world_peer_id, timestamp=timestamp)
        # retrieve peer role and node_id from the profile
        
        # check if this is the new overall best and update it
        overall_best_accuracy = self.stats.get_last_value('accuracy')
        if overall_best_accuracy == -1.0 or (value > overall_best_accuracy and peer_id in self.all_agents):
                
            unaid = build_unaid(self.all_agents[peer_id])
            self.stats.store_stat('overall_best_student', unaid, group_key=world_peer_id, timestamp=timestamp)
            log.info(f"[WStats] New overall best exam error: {value} by {peer_id}")
            
            # add the badge for the bast overall
            badge = {
                'peer_id': peer_id,
                'score': value,
                'badge_type': "completed",
                'badge_description': "LOT2.0 champion!",
                'agent_token': self._node_conn.get_last_token(peer_id)
                }
            self.add_badge(**badge)
        
        # the custom stat was successfully handled
        return True
        
