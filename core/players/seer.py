from core.players.player import Player
from core.players.utils import get_target_from_response
from core.event import EventBook
import os
import re

class SeerPlayer(Player):
    def __init__(self, id, global_info, private_info, prompt_dir_path, common_prompt_dir_path = None, openai_client = None, reflex_note_path_belief = None, reflex_note_path_policy = None):
        super().__init__(id, global_info, private_info, prompt_dir_path, common_prompt_dir_path, openai_client, reflex_note_path_belief, reflex_note_path_policy)
        self.labels = ["all", "seer"]
        self.role = "seer"
        
    def get_replacements(self):
        replacements = super().get_replacements()
        replacements.update({
            "{known_roles}": self.get_known_roles(),
        })
        replacements.update({
            "{hidden_state}": str(self.hidden_state),
        })
        replacements.update({
            "{private}": f"These are your previous inquiry results, which should be the key information for you and other good players to win: \n {self.get_known_roles()}"
        })
        #! TEMPORARY
        replacements.update({"{events}": str(self.event_book)})
        return replacements
    
    def init_game(self, global_info, private_info):
        super().init_game(global_info, private_info)
        if "known_roles" not in self.private_info:
            self.private_info["known_roles"] = dict()
        
    def _act(self, available_actions = None):
        if "vote" in available_actions:
            res = self._vote()
            return ("vote", res[0], res[1])
        elif "see" in available_actions or "night" in available_actions:
            res = self._see()
            return ("see", res[0], res[1])
        elif "speak" in available_actions:
            res = self._speak()
            return ("speak", None, res)
        elif "speak_type" in available_actions:
            res = self._get_speak_type()
            return ("speak_type", res, None)
    
    
    def _see(self):
        response = self.get_response("see")
        see = get_target_from_response(response)
        return see, response
    
    def receive_inquiry_result(self, target, is_werewolf : bool):
        if target is not None:
            self.private_info["known_roles"][target] = 1 if is_werewolf else 0
        return
    
    def get_known_roles(self):
        if self.private_info["known_roles"] == {}:
            return "You have no previous inquiry."
        s = ""
        for player_id, role in self.private_info["known_roles"].items():
            s += f"Player {player_id}: {'werewolf' if role == 1 else 'not werewolf'}.\n"
        return s
    