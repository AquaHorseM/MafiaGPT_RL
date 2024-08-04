from core.players.player import Player
from core.players.utils import get_prompt
from api import send_message_xsm
from core.event import EventBook
import os
import re

class WerewolfPlayer(Player):
    def __init__(self, id, player_num, roles_mapping, prompt_dir_path):
        super().__init__(id, player_num, roles_mapping)
        self.private_info["role"] = "werewolf"
        self.private_info["role_specific_info"]["previous_advices"] = []
        self.vote_model = None #TODO: implement vote model
        self.kill_model = None
        self.prompt_dir_path = prompt_dir_path
        
    def get_replacements(self):
        replacements = super().get_replacements()
        replacements.update({
            "werewolves": self.private_info["role_specific_info"]["werewolf_ids"]
        })
    
    def init_game(self, global_info, private_info):
        super().init_game(global_info, private_info)
        for wid in range(self.private_info["role_specific_info"]["werewolf_ids"]):
            self.hidden_state.set_role(wid, self.global_info["roles_mapping"]["werewolf"])
            
    def _vote(self):
        #TODO
        prompt_path = os.path.join(self.prompt_dir_path, "vote")
        prompt = get_prompt(prompt_path, self.get_replacements())
        response = send_message_xsm(prompt)
        #find the first number in the response
        vote = int(re.search(r"\d+", response).group())
        return vote, response
        
    def _act(self, event_book: EventBook, available_actions = None):
        self.update_hidden_state(event_book)
        if "vote" in available_actions:
            res = self._vote()
            return ("vote", res[0], res[1])
        elif "kill" in available_actions:
            res = self._kill()
            return ("kill", res[0], res[1])
    
    def _speak(self, event_book: EventBook):
        prompt_path = os.path.join(self.prompt_dir_path, "speak")
        prompt = get_prompt(prompt_path, self.get_replacements())
        response = send_message_xsm(prompt)
        return response
    
    def _kill(self):
        prompt_path = os.path.join(self.prompt_dir_path, "kill")
        prompt = get_prompt(prompt_path, self.get_replacements())
        response = send_message_xsm(prompt)
        #find the first number in the response
        kill = int(re.search(r"\d+", response).group())
        return kill, response
    
    def _extract_hiddenstate_from_response(self, response):
        #TODO
        return response
    
    def update_hidden_state(self, event_book: EventBook):
        if event_book.tick == self.last_update_tick:
            return
        else:
            obs = event_book.filter_by_time(self.last_update_tick)
            self.last_update_tick = event_book.tick
            event_des = ""
            for event in obs:
                event_des += str(event)
                event_des += "\n"
                
            replacements = self.get_replacements()
            replacements.update({"{event_des}": event_des})
            prompt_path = os.path.join(self.prompt_dir_path, "update_hidden_state")
            prompt = get_prompt(prompt_path, replacements)
            response = send_message_xsm(prompt)
            self.hidden_state = self._extract_hiddenstate_from_response(response)
            return
        
        