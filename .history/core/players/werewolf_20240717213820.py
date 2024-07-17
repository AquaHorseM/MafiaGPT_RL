from player import Player
from utils import get_prompt
import os

class WerewolfPlayer(Player):
    def __init__(self, id, player_num, roles_mapping, prompt_dir_path):
        super().__init__(id, player_num, roles_mapping)
        self.private_info["role"] = "werewolf"
        self.vote_model = None #TODO: implement vote model
        self.kill_model = None
        self.prompt_dir_path = prompt_dir_path
    
    def init_game(self, global_info, private_info):
        super().init_game(global_info, private_info)
        for wid in range(self.private_info["role_specific_info"]["werewolf_ids"]):
            self.hidden_state.set_role(wid, self.global_info["roles_mapping"]["werewolf"])
            
    def _vote(self):
        #TODO
        raise NotImplementedError
        
    def _act(self, available_actions = None):
        if "vote" in available_actions:
            return ("vote", self._vote(), None)
        elif "kill" in available_actions:
            return ("kill", self._kill(), None)
    
    def _speak(self):
        #TODO
        raise NotImplementedError
    
    def _kill(self):
        #TODO
        raise NotImplementedError
    
    def update_hidden_state(self, obs):
        event_des = ""
        for event in obs:
            event_des += str(event)
            event_des += "\n"
            
        replacements = self.get_replacements()
        replacements.update({"{event_des}": event_des})
        prompt_path = os.path.join(self.prompt_dir_path, "update_hidden_state")
        prompt = get_prompt(prompt_path, replacements)