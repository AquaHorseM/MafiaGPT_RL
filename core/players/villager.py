from core.players.player import Player
from core.players.utils import get_target_from_response
from core.event import EventBook
import os
import re

class VillagerPlayer(Player):
    def __init__(self, id, game_id, proposal_num, global_info, private_info, prompt_dir_path, common_prompt_dir_path = None, openai_client = None, reflex_note_path_belief = None, reflex_note_path_policy = None):
        super().__init__(id, game_id, proposal_num, global_info, private_info, prompt_dir_path, common_prompt_dir_path, openai_client, reflex_note_path_belief, reflex_note_path_policy)
        self.labels = ["all", "villager"]
        self.role = "villager"
        
        
    def get_replacements(self):
        replacements = super().get_replacements()
        replacements.update({
            "{hstate}": str(self.hstate),
        })
        replacements.update({
            "{private}": " ",
        })
        #! TEMPORARY
        replacements.update({"{events}": str(self.event_book)})
        return replacements

    def _act(self, available_actions = None): #return (action, target, reason, imagination)
        if "vote" in available_actions:
            res = self._vote()
            return {
                "action": "vote",
                "target": res[0],
                "reason": res[1],
                "imagination": None
            }
        elif "speak" in available_actions:
            res = self._speak()
            return {
                "action": "speak",
                "target": res,
                "reason": None,
                "imagination": None
            }
        elif "speak_type" in available_actions:
            res = self._get_speak_type()
            return ("speak_type", res, None)
        else:
            return {
                "action": None,
                "target": None,
                "reason": None,
                "imagination": None
            }

    