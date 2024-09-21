from core.players.player import Player
from core.players.utils import get_prompt, get_target_from_response
from core.event import EventBook
import os
import re

class WerewolfPlayer(Player):
    def __init__(self, id, global_info, private_info, prompt_dir_path, common_prompt_dir_path = None, openai_client = None, reflex_note_path_belief = None, reflex_note_path_policy = None):
        super().__init__(id, global_info, private_info, prompt_dir_path, common_prompt_dir_path, openai_client, reflex_note_path_belief, reflex_note_path_policy)
        self.labels = ["all", "werewolf"]
        self.role = "werewolf"
        
    def get_replacements(self):
        replacements = super().get_replacements()
        werewolf_ids = str(self.private_info["werewolf_ids"])
        replacements.update({
            "{werewolf_ids}": werewolf_ids,
        })
        replacements.update({
            "{hidden_state}": str(self.hidden_state),
        })
        replacements.update({
            "{private}": f"All werewolves including you are {werewolf_ids}. Remember that you should work together to hide from other players and eliminate them."
        })
        #! TEMPORARY
        replacements.update({"{events}": str(self.event_book)})
        replacements.update({"{previous_advices}": self.show_previous_advices()})
        return replacements
    
    def init_game(self, global_info, private_info):
        super().init_game(global_info, private_info)
        for wid in self.private_info["werewolf_ids"]:
            self.hidden_state.set_role(wid, self.global_info["roles_mapping"]["werewolf"])
        
    def _act(self, event_book: EventBook, available_actions = None, update_hstate = True):
        if "vote" in available_actions:
            res = self._vote()
            return ("vote", res[0], res[1])
        elif "kill" in available_actions or "night" in available_actions:
            res = self._kill()
            return ("kill", res[0], res[1])
        elif "speak" in available_actions:
            res = self._speak(event_book, update_hstate)
            return ("speak", None, res)
        elif "speak_type" in available_actions:
            res = self._get_speak_type(event_book, update_hstate)
            return ("speak_type", res, None)
    
    def _kill(self):
        prompt_path = self.get_prompt_path("kill.txt")
        prompt = get_prompt(prompt_path, self.get_replacements())
        response = self.send_message_xsm(prompt)
        kill = get_target_from_response(response)
        return kill, response

    def get_alive_werewolf_ids(self):
        return [wid for wid in self.private_info["werewolf_ids"] if wid in self.global_info["alive_players"]]
    
    def show_previous_advices(self):
        #TODO
        if self.private_info["previous_advices"] == []:
            s = "No previous advices."
        else:
            s = ""
            for id, target, reason in self.private_info["previous_advices"]:
                s += f"Player {id} advised to target Player {target} because {reason}\n"
        if len(self.private_info["previous_advices"]) == len(self.get_alive_werewolf_ids()) - 1:
            s += "Notice that you are the last werewolf, so your choice determines the final decision."
        return s
    