from core.players.player import Player
from core.players.utils import get_prompt, get_target_from_response
from core.api import send_message_xsm
from core.event import EventBook
import os
import re

class MedicPlayer(Player):
    def __init__(self, id, global_info, private_info, prompt_dir_path, reflex_note_path = None):
        super().__init__(id, global_info, private_info)
        self.prompt_dir_path = prompt_dir_path
        self.labels = ["all", "medic"]
        
    def get_replacements(self):
        replacements = super().get_replacements()
        replacements.update({
            "{last_heal}": self.private_info["last_heal"] if self.private_info["last_heal"] is not None else "Nobody",
        })
        replacements.update({
            "{hidden_state}": str(self.hidden_state),
        })
        #! TEMPORARY
        replacements.update({"{events}": str(self.event_book)})
        return replacements
    
    def init_game(self, global_info, private_info):
        super().init_game(global_info, private_info)
        self.private_info["last_heal"] = None
        
    def _act(self, event_book: EventBook, available_actions = None):
        self.update_hidden_state(event_book)
        if "vote" in available_actions:
            res = self._vote()
            return ("vote", res[0], res[1])
        elif "heal" in available_actions:
            res = self._heal()
            return ("heal", res[0], res[1])
    
    def _vote(self):
        #TODO
        prompt_path = os.path.join(self.prompt_dir_path, "vote.txt")
        prompt = get_prompt(prompt_path, self.get_replacements())
        response = send_message_xsm(prompt)
        vote = get_target_from_response(response)
        return vote, response
    
    def _heal(self):
        prompt_path = os.path.join(self.prompt_dir_path, "heal.txt")
        prompt = get_prompt(prompt_path, self.get_replacements())
        response = send_message_xsm(prompt)
        heal = get_target_from_response(response)
        return heal, response
    
    def _speak(self, event_book: EventBook):
        self.update_hidden_state(event_book)
        prompt_path = os.path.join(self.prompt_dir_path, "speak_type.txt")
        replacements = self.get_replacements()
        prompt = get_prompt(prompt_path, replacements)
        response = send_message_xsm(prompt)
        #Find the [type] in the response
        s_type = re.search(r"\[(.*?)\]", response).group(1).lower()
        s_type = s_type.strip().split(",") #split the types
        s_type = [s.strip() for s in s_type]
        replacements.update({
            "{speech_type}": str(s_type)
        })
        print(f"I am player {self.id}, I choose to speak {s_type}")
        prompt_path = os.path.join(self.prompt_dir_path, f"speak.txt")
        prompt = get_prompt(prompt_path, replacements)
        response = send_message_xsm(prompt)
        return response
    