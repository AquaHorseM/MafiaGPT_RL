from core.players.player import Player
from core.players.utils import get_prompt, get_target_from_response
from core.api import send_message_xsm
from core.event import EventBook
import os
import re

class WerewolfPlayer(Player):
    def __init__(self, id, global_info, private_info, prompt_dir_path, reflex_note_path = None):
        super().__init__(id, global_info, private_info)
        self.prompt_dir_path = prompt_dir_path
        if reflex_note_path is None:
            self.reflex_note_path = os.path.join(prompt_dir_path, "reflex_note.txt")
        else:
            self.reflex_note_path = reflex_note_path
        self.labels = ["all", "werewolf"]
        
    def get_replacements(self):
        replacements = super().get_replacements()
        replacements.update({
            "{werewolf_ids}": str(self.private_info["werewolf_ids"])
        })
        replacements.update({
            "{hidden_state}": str(self.hidden_state),
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
        vote = get_target_from_response(response)
        return vote, response
    
    def _kill(self):
        prompt_path = os.path.join(self.prompt_dir_path, "kill.txt")
        prompt = get_prompt(prompt_path, self.get_replacements())
        response = send_message_xsm(prompt)
        kill = get_target_from_response(response)
        return kill, response
    
    def _speak(self, event_book: EventBook):
        self.update_hidden_state(event_book)
        prompt_path = os.path.join(self.prompt_dir_path, "speak_type.txt")
        replacements = self.get_replacements()
        prompt = get_prompt(prompt_path, replacements)
        response = send_message_xsm(prompt)
        #Find the [type] in the response
        s_type = re.search(r"\[(.*?)\]", response).group(1)
        replacements.update({
            "{speech_type}": s_type
        })
        prompt_path = os.path.join(self.prompt_dir_path, f"speak.txt")
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
    
    def reflex(self, prev_hstate, next_hstate, pred_hstate):
        def update_note_from_response(response):
            #TODO, temporarily let the response be the new note
            with open(self.reflex_note_path, "w") as f:
                f.write(response)
            return
        replacements = self.get_replacements()
        replacements.update({
            "{prev_hstate}": prev_hstate,
            "{next_hstate}": next_hstate,
            "{pred_hstate}": pred_hstate,
        })
        with open(self.reflex_note_path, "r") as f:
            reflex_note = f.read()
        replacements.update({
            "{reflex_note}": reflex_note
        })
        prompt_path = os.path.join(self.prompt_dir_path, "reflex.txt")
        prompt = get_prompt(prompt_path, replacements)
        response = send_message_xsm(prompt)
        update_note_from_response(response)
        return response