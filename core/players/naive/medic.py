from .player import Player
from core.players.utils import get_response, get_target_from_response
from core.event import EventBook
import os
import re

class MedicPlayer(Player):
    def __init__(self, id, game_id, player_config, global_info, private_info, openai_client = None):
        super().__init__(id, game_id, player_config, global_info, private_info, openai_client)
        self.labels = ["all", "medic"]
        self.role = "medic"
        self.private_info["last_heal"] = None
        
    def get_replacements(self):
        replacements = super().get_replacements()
        replacements.update({
            "{last_heal}": self.private_info["last_heal"] if self.private_info["last_heal"] is not None else "Nobody",
        })
        replacements.update({
            "{hstate}": str(self.hstate),
        })
        replacements.update({
            "{private}": f"You tried to heal player {self.private_info['last_heal']} last night." if self.private_info["last_heal"] is not None else "You haven't tried to heal anyone yet."
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
        elif "heal" in available_actions or "night" in available_actions:
            res = self._heal()
            return {
                "action": "heal",
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
    
    
    
    
    def _get_proposals_from_response_HealThreeStep(self, response):
        # Regex to capture the first number after 'Firstly' and 'Secondly'
        first_number_pattern = r'Firstly.*?(\d+)'
        second_number_pattern = r'.*?Secondly.*?(\d+)'
        
        # Regex to capture the reason after 'the reason is'
        first_reason_pattern = r'Firstly.*? reason is:? (.*?)(?:\.|Secondly)'
        second_reason_pattern = r'.*?Secondly.*? reason is:? (.*)'
        
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
    
    
    def _get_imagination_from_response_HealThreeStep(self, response):
        return response
    def _get_final_choice_from_response_HealThreeStep(self, response):
        return get_target_from_response(response)

    def _heal_multiagent(self):
        self.draft_dict["heal"].append(dict())
        
        first_player, first_reason, second_player, second_reason = None, None, None, None
        count = 0
        while ((first_player is None) or (second_player is None) or (first_reason is None) or (second_reason is None)) and (count < 3):
            count += 1
            response = self.get_response("heal_threeStage_propose")
            first_player, first_reason, second_player, second_reason = self._get_proposals_from_response_HealThreeStep(response)
        assert not ((first_player is None) or (second_player is None) or (first_reason is None) or (second_reason is None))
        
        proposals = [first_player, second_player]
        
        
        self.draft_dict["heal"][-1]["heal_proposal"] = proposals
        self.draft_dict["heal"][-1]["proposal_and_imaginations"] = list()
        result_list = list()
        for propose in proposals:
            replacements = self.get_replacements()
            replacements["{current_propose}"] = str(propose)
            response = self.get_response("heal_threeStage_imagine", replacements)
            results = self._get_imagination_from_response_HealThreeStep(response)
            result_list.append(results)
            self.draft_dict["heal"][-1]["proposal_and_imaginations"].append(response)
        
        replacements = self.get_replacements()
        replacements["{current_propose_0}"] = str(proposals[0])
        replacements["{current_propose_1}"] = str(proposals[1])
        replacements["{current_propose_0_imagination}"] = result_list[0]
        replacements["{current_propose_1_imagination}"] = result_list[1]
        
        
        
        response_and_reason = self.get_response("heal_threeStage_choose", replacements)
        heal = self._get_final_choice_from_response_HealThreeStep(response_and_reason)
        
        self.draft_dict["heal"][-1]["proposal_chosen_and_reasons"] = response_and_reason
        return heal, response_and_reason
        
    
    
    
    
    def _heal(self, use_multiagent = False):
        if not use_multiagent:
            return self._heal_org()
        else:
            return self._heal_multiagent()
    
    def _heal_org(self):
        response = self.get_response("heal")
        heal = get_target_from_response(response)
        return heal, response
    
    
    