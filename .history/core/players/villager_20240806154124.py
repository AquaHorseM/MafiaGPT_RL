from core.players.player import Player
from core.players.utils import get_prompt
from core.api import send_message_xsm
from core.event import EventBook
import os
import re

class VillagerPlayer(Player):
    def __init__(self, id, global_info, private_info, prompt_dir_path):
        super().__init__(id, global_info, private_info)
        self.prompt_dir_path = prompt_dir_path
        self.labels = ["all", "villager"]
        '''
        The event book is temporarily used for debugging purposes.
        '''
        self.event_book = EventBook()
        
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

    def _act(self, event_book: EventBook, available_actions = None):
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
    
    def show_prompt(self, file_name = 'vote.txt'):
        with open(file_name, 'r') as f:
            prompt_path = os.path.join(self.prompt_dir_path, file_name)
            prompt = get_prompt(prompt_path, self.get_replacements())
            return prompt
    