from core.players.player import Player
from core.players.utils import get_prompt
from core.api import send_message_xsm
from core.event import EventBook
import os
import re

class WerewolfPlayer(Player):
    def __init__(self, id, global_info, private_info, prompt_dir_path):
        super().__init__(id, global_info, private_info)
        self.vote_model = None #TODO: implement vote model
        self.kill_model = None
        self.prompt_dir_path = prompt_dir_path
        self.labels = ["all", "werewolf"]
        '''
        The event book is temporarily used for debugging purposes.
        '''
        self.event_book = EventBook()
        
    def get_replacements(self):
        replacements = super().get_replacements()
        replacements.update({
            "{werewolf_ids}": str(self.private_info["werewolf_ids"])
        })
        #! TEMPORARY
        replacements.update({"{events}": str(self.event_book)})
        replacements.update({"{previous_advices}": self.show_previous_advices()})
        return replacements
    
    def init_game(self, global_info, private_info):
        super().init_game(global_info, private_info)
        for wid in range(self.private_info["werewolf_ids"]):
            self.hidden_state.set_role(wid, self.global_info["roles_mapping"]["werewolf"])
        
    def _act(self, event_book: EventBook, available_actions = None):
        self.update_hidden_state(event_book)
        if "vote" in available_actions:
            res = self._vote()
            return ("vote", res[0], res[1])
        elif "kill" in available_actions:
            res = self._kill()
            return ("kill", res[0], res[1])
    
    def _vote(self):
        #TODO
        prompt_path = os.path.join(self.prompt_dir_path, "vote.txt")
        prompt = get_prompt(prompt_path, self.get_replacements())
        response = send_message_xsm(prompt)
        #find the first number in the response
        vote = int(re.search(r"\d+", response).group())
        return vote, response
    
    def _kill(self):
        prompt_path = os.path.join(self.prompt_dir_path, "kill.txt")
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
        return
        def _extract_hiddenstate_from_response(response):
            #TODO
            return response
        
        event_des = ""
        for event in events:
            event_des += str(event)
            event_des += "\n"
            
        replacements = self.get_replacements()
        replacements.update({"{event_des}": event_des})
        prompt_path = os.path.join(self.prompt_dir_path, "update_hidden_state")
        prompt = get_prompt(prompt_path, replacements)
        response = send_message_xsm(prompt)
        self.hidden_state = _extract_hiddenstate_from_response(response)
        return
    
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