from core.players.player import Player
from core.players.utils import get_target_from_response
from core.event import EventBook
import os
import re

class SeerPlayer(Player):
    def __init__(self, id, game_id, global_info, private_info, prompt_dir_path, common_prompt_dir_path = None, openai_client = None, reflex_note_path_belief = None, reflex_note_path_policy = None):
        super().__init__(id, game_id, global_info, private_info, prompt_dir_path, common_prompt_dir_path, openai_client, reflex_note_path_belief, reflex_note_path_policy)
        self.labels = ["all", "seer"]
        self.role = "seer"
        if "known_roles" not in self.private_info:
            self.private_info["known_roles"] = dict()
        
    def get_replacements(self):
        replacements = super().get_replacements()
        replacements.update({
            "{known_roles}": self.get_known_roles(),
        })
        replacements.update({
            "{hstate}": str(self.hstate),
        })
        replacements.update({
            "{private}": f"These are your previous inquiry results, which should be the key information for you and other good players to win: \n {self.get_known_roles()}"
        })
        #! TEMPORARY
        replacements.update({"{events}": str(self.event_book)})
        return replacements
    
    def _act(self, available_actions = None): #return (action, target, reason, imagination)
        if "vote" in available_actions:
            res = self._vote()
            return {
                "action": "vote",
                "target": res[0],
                "reason": res[1],
                "imagination": None
            }
        elif "see" in available_actions or "night" in available_actions:
            res = self._see()
            return {
                "action": "see",
                "target": res[0],
                "reason": res[1],
                "imagination": None
            }
        elif "speak" in available_actions:
            res = self._speak()
            return {
                "action": "speak",
                "target": res,
                "reason": None,
                "imagination": None
            }
        elif "speak_type" in available_actions:
            res = self._get_speak_type()
            return ("speak_type", res, None)
    
    def _get_proposals_from_response_SeeThreeStep(self, response):
        # Regex to capture the first number after 'Firstly' and 'Secondly'
        first_number_pattern = r'Firstly.*?(\d+)'
        second_number_pattern = r'Secondly.*?(\d+)'
        
        # Regex to capture the reason after 'the reason is'
        first_reason_pattern = r'Firstly.*?reason is:? (.*?)\n'
        second_reason_pattern = r'Secondly.*?reason is:? (.*)'
        
        # Find the first player number and reason
        first_player_match = re.search(first_number_pattern, response)
        first_reason_match = re.search(first_reason_pattern, response, re.DOTALL)
        
        # Find the second player number and reason
        second_player_match = re.search(second_number_pattern, response)
        second_reason_match = re.search(second_reason_pattern, response, re.DOTALL)
        
        # Extract data or set to None if not found
        first_player = int(first_player_match.group(1)) if first_player_match else None
        first_reason = first_reason_match.group(1).strip() if first_reason_match else None
        second_player = int(second_player_match.group(1)) if second_player_match else None
        second_reason = second_reason_match.group(1).strip() if second_reason_match else None
        
        return first_player, first_reason, second_player, second_reason
    
    
    def _get_imagination_from_response_SeeThreeStep(self, response):
        return response
    def _get_final_choice_from_response_SeeThreeStep(self, response):
        return get_target_from_response(response)
    
    
    
    
    def _see(self,use_multiagent=True):
        if not use_multiagent:
            return self._see_org()
        else:
            return self._see_multiagent()
    def _see_multiagent(self):
        self.draft_dict["see"].append(dict())
        first_player, first_reason, second_player, second_reason = None, None, None, None
        count = 0
        while ((first_player is None) or (second_player is None) or (first_reason is None) or (second_reason is None)) and (count < 3):
            count += 1
            response = self.get_response("see_threeStage_propose")
            first_player, first_reason, second_player, second_reason = self._get_proposals_from_response_SeeThreeStep(response)
        assert not ((first_player is None) or (second_player is None) or (first_reason is None) or (second_reason is None))
        
        proposals = [first_player, second_player]
        
        
        self.draft_dict["see"][-1]["see_proposal"] = proposals
        self.draft_dict["see"][-1]["proposal_and_imaginations"] = list()
        result_list = list()
        for propose in proposals:
            replacements = self.get_replacements()
            replacements["{current_propose}"] = str(propose)
            response = self.get_response("see_threeStage_imagine", replacements)
            
            results = self._get_imagination_from_response_SeeThreeStep(response)
            result_list.append(results)
            self.draft_dict["see"][-1]["proposal_and_imaginations"].append(response)
        
        replacements = self.get_replacements()
        replacements["{current_propose_0}"] = str(proposals[0])
        replacements["{current_propose_1}"] = str(proposals[1])
        replacements["{current_propose_0_imagination}"] = result_list[0]
        replacements["{current_propose_1_imagination}"] = result_list[1]
        
        
        
        response_and_reason = self.get_response("see_threeStage_choose", replacements)
        see = self._get_final_choice_from_response_SeeThreeStep(response_and_reason)
        
        self.draft_dict["see"][-1]["proposal_chosen_and_reasons"] = response_and_reason
        return see, response
    def _see_org(self):
        response = self.get_response("see")
        see = get_target_from_response(response)
        return see, response
    
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
    