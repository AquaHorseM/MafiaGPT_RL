from core.players.player import Player
from core.players.utils import get_prompt
from core.api import send_message_xsm
from core.event import EventBook
import os
import re

class VillagerPlayer(Player):
    def __init__(self, id, global_info, private_info, prompt_dir_path, reflex_note_path = None):
        super().__init__(id, global_info, private_info, prompt_dir_path, reflex_note_path)
        self.labels = ["all", "villager"]
        
        
    def get_replacements(self):
        replacements = super().get_replacements()
        replacements.update({
            "{hidden_state}": str(self.hidden_state),
        })
        #! TEMPORARY
        replacements.update({"{events}": str(self.event_book)})
        return replacements
    
    def init_game(self, global_info, private_info):
        super().init_game(global_info, private_info)

    def _act(self, event_book: EventBook, available_actions = None, update_hstate = True):
        if update_hstate:
            self.update_hidden_state(event_book)
        if "vote" in available_actions:
            res = self._vote()
            return ("vote", res[0], res[1])
        else:
            return (None, None, None)

    
    def _vote(self):
        #TODO
        prompt_path = os.path.join(self.prompt_dir_path, "vote.txt")
        prompt = get_prompt(prompt_path, self.get_replacements())
        response = send_message_xsm(prompt)
        #find the first number in the response
        vote = int(re.search(r"\d+", response).group())
        return vote, response
    
    def _speak(self, event_book: EventBook, update_hstate = True):
        if update_hstate:
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

    def show_prompt(self, file_name = 'vote.txt'):
        prompt_path = os.path.join(self.prompt_dir_path, file_name)
        prompt = get_prompt(prompt_path, self.get_replacements())
        return prompt
    