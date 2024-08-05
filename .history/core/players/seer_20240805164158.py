from core.players.player import Player
from core.players.utils import get_prompt
from core.api import send_message_xsm
from core.event import EventBook
import os
import re

class SeerPlayer(Player):
    def __init__(self, id, global_info, private_info, prompt_dir_path):
        super().__init__(id, global_info, private_info)
        self.prompt_dir_path = prompt_dir_path
        self.labels = ["all", "seer"]
        '''
        The event book is temporarily used for debugging purposes.
        '''
        self.event_book = EventBook()
        
    def get_replacements(self):
        replacements = super().get_replacements()
        replacements.update({
            "{known_roles}": str(self.private_info["known_roles"]),
        })
        #! TEMPORARY
        replacements.update({"{events}": str(self.event_book)})
        replacements.update({"{previous_advices}": self.show_previous_advices()})
        return replacements
    
    def init_game(self, global_info, private_info):
        super().init_game(global_info, private_info)
        self.private_info["known_roles"] = dict()
        
    def _act(self, event_book: EventBook, available_actions = None):
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
        response = send_message_xsm(prompt)
        #find the first number in the response
        vote = int(re.search(r"\d+", response).group())
        return vote, response
    
    def _see(self):
        prompt_path = os.path.join(self.prompt_dir_path, "see.txt")
        prompt = get_prompt(prompt_path, self.get_replacements())
        response = send_message_xsm(prompt)
        #find the first number in the response
        kill = int(re.search(r"\d+", response).group())
        return kill, response
    
    def _speak(self, event_book: EventBook):
        self.update_hidden_state(event_book)
        prompt_path = os.path.join(self.prompt_dir_path, "speak.txt")
        prompt = get_prompt(prompt_path, self.get_replacements())
        response = send_message_xsm(prompt)
        return response
    
    def _update_hidden_state(self, events):
        #TODO
        self.event_book.add_event(events)        
        event_des = ""
        for event in events:
            event_des += str(event)
            event_des += "\n"
            
        replacements = self.get_replacements()
        replacements.update({"{event_des}": event_des})
        prompt_path = os.path.join(self.prompt_dir_path, "update_hidden_state")
        prompt = get_prompt(prompt_path, replacements)
        response = send_message_xsm(prompt)
        self.hidden_state.update(response, confidence = 0.2)
        return
    
    def receive_inquiry_result(self, target, is_werewolf):
        self.private_info["known_roles"][target] = 1 if is_werewolf else 0
        return
    
    def get_known_roles(self):
        s = ""
        for player_id, role in self.private_info["known_roles"].items():
            s += f"Player {player_id} is a {'werewolf' if role == 1 else 'not werewolf'}.\n"
        return s