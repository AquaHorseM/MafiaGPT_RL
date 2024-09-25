from core.players.player import Player
from core.players.utils import get_target_from_response
from core.event import EventBook
import os
import re

class VillagerPlayer(Player):
    def __init__(self, id, global_info, private_info, prompt_dir_path, common_prompt_dir_path = None, openai_client = None, reflex_note_path_belief = None, reflex_note_path_policy = None):
        super().__init__(id, global_info, private_info, prompt_dir_path, common_prompt_dir_path, openai_client, reflex_note_path_belief, reflex_note_path_policy)
        self.labels = ["all", "villager"]
        self.role = "villager"
        
        
    def get_replacements(self):
        replacements = super().get_replacements()
        replacements.update({
            "{hidden_state}": str(self.hidden_state),
        })
        replacements.update({
            "{private}": " ",
        })
        #! TEMPORARY
        replacements.update({"{events}": str(self.event_book)})
        return replacements

    def _act(self, available_actions = None):
        if "vote" in available_actions:
            res = self._vote()
            return ("vote", res[0], res[1])
        elif "speak" in available_actions:
            res = self._speak()
            return ("speak", None, res)
        elif "speak_type" in available_actions:
            res = self._get_speak_type()
            return ("speak_type", res, None)
        else:
            return (None, None, None)


    