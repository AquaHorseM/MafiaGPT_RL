from core.players.player import Player
from core.players.utils import get_prompt, get_target_from_response
from core.event import EventBook
import os
import re

class MedicPlayer(Player):
    def __init__(self, id, global_info, private_info, prompt_dir_path, openai_client = None, reflex_note_path = None):
        super().__init__(id, global_info, private_info, prompt_dir_path, openai_client, reflex_note_path)
        self.labels = ["all", "medic"]
        self.role = "medic"
        
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
        
    def _act(self, event_book: EventBook, available_actions = None, update_hstate = True):
        if update_hstate:
            self.update_hidden_state(event_book)
        if "vote" in available_actions:
            res = self._vote()
            return ("vote", res[0], res[1])
        elif "heal" in available_actions or "night" in available_actions:
            res = self._heal()
            return ("heal", res[0], res[1])
        elif "speak" in available_actions:
            res = self._speak(event_book, update_hstate=False)
            return ("speak", None, res)
        elif "speak_type" in available_actions:
            res = self._get_speak_type(event_book, update_hstate=False)
            return ("speak_type", res, None)
    
    def _vote(self):
        #TODO
        prompt_path = os.path.join(self.prompt_dir_path, "vote.txt")
        prompt = get_prompt(prompt_path, self.get_replacements())
        response = self.send_message_xsm(prompt)
        vote = get_target_from_response(response)
        return vote, response
    
    def _heal(self):
        prompt_path = os.path.join(self.prompt_dir_path, "heal.txt")
        prompt = get_prompt(prompt_path, self.get_replacements())
        response = self.send_message_xsm(prompt)
        heal = get_target_from_response(response)
        return heal, response
    
    def _get_speak_type(self, event_book: EventBook, update_hstate = True):
        if update_hstate:
            self.update_hidden_state(event_book)
        prompt_path = os.path.join(self.prompt_dir_path, "speak_type.txt")
        replacements = self.get_replacements()
        prompt = get_prompt(prompt_path, replacements)
        response = self.send_message_xsm(prompt)
        assert isinstance(response, str), f"response is not a string: {response}"
        #Find the [type] in the response
        s_type = re.search(r"\[(.*?)\]", response).group(1).lower()
        s_type = s_type.strip().split(",") #split the types
        s_type = [s.strip() for s in s_type]
        return s_type
    
    def speak_with_type(self, s_type):
        prompt_path = os.path.join(self.prompt_dir_path, f"speak.txt")
        replacements = self.get_replacements()
        replacements.update({
            "{speech_type}": str(s_type)
        })
        prompt = get_prompt(prompt_path, replacements)
        response = self.send_message_xsm(prompt)
        return response
        
        
    
    def _speak(self, event_book: EventBook, update_hstate = True):
        s_type = self._get_speak_type(event_book, update_hstate)
        replacements = self.get_replacements()
        replacements.update({
            "{speech_type}": str(s_type)
        })
        print(f"I am player {self.id}, I choose to speak {s_type}")
        prompt_path = os.path.join(self.prompt_dir_path, f"speak.txt")
        prompt = get_prompt(prompt_path, replacements)
        response = self.send_message_xsm(prompt)
        return response
    