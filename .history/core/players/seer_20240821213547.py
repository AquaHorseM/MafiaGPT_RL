from core.players.player import Player
from core.players.utils import get_prompt, get_target_from_response
from core.event import EventBook
import os
import re

class SeerPlayer(Player):
    def __init__(self, id, global_info, private_info, prompt_dir_path, openai_client = None, reflex_note_path = None):
        super().__init__(id, global_info, private_info, prompt_dir_path, openai_client, reflex_note_path)
        self.labels = ["all", "seer"]
        
    def get_replacements(self):
        replacements = super().get_replacements()
        replacements.update({
            "{known_roles}": self.get_known_roles(),
        })
        replacements.update({
            "{hidden_state}": str(self.hidden_state),
        })
        #! TEMPORARY
        replacements.update({"{events}": str(self.event_book)})
        return replacements
    
    def init_game(self, global_info, private_info):
        super().init_game(global_info, private_info)
        self.private_info["known_roles"] = dict()
        
    def _act(self, event_book: EventBook, available_actions = None, update_hstate = True):
        if update_hstate:
            self.update_hidden_state(event_book)
        if "vote" in available_actions:
            res = self._vote()
            return ("vote", res[0], res[1])
        elif "see" in available_actions:
            res = self._see()
            return ("see", res[0], res[1])
    
    def _vote(self):
        #TODO
        prompt_path = os.path.join(self.prompt_dir_path, "vote.txt")
        prompt = get_prompt(prompt_path, self.get_replacements())
        response = self.send_message_xsm(prompt)
        vote = get_target_from_response(response)
        return vote, response
    
    def _see(self):
        prompt_path = os.path.join(self.prompt_dir_path, "see.txt")
        prompt = get_prompt(prompt_path, self.get_replacements())
        response = self.send_message_xsm(prompt)
        see = get_target_from_response(response)
        return see, response
    
    def _speak(self, event_book: EventBook, update_hstate = True):
        if update_hstate:
            self.update_hidden_state(event_book)
        prompt_path = os.path.join(self.prompt_dir_path, "speak_type.txt")
        replacements = self.get_replacements()
        prompt = get_prompt(prompt_path, replacements)
        response = self.send_message_xsm(prompt)
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
        response = self.send_message_xsm(prompt)
        return response
    
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
    