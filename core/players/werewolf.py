from core.players.player import Player
from core.players.utils import get_target_from_response
from core.event import EventBook
import os
import re

class WerewolfPlayer(Player):
    def __init__(self, id, game_id, global_info, private_info, prompt_dir_path, common_prompt_dir_path = None, openai_client = None, reflex_note_path_belief = None, reflex_note_path_policy = None):
        super().__init__(id, game_id, global_info, private_info, prompt_dir_path, common_prompt_dir_path, openai_client, reflex_note_path_belief, reflex_note_path_policy)
        self.labels = ["all", "werewolf"]
        self.role = "werewolf"
        for wid in self.private_info["werewolf_ids"]:
            if wid != self.id:
                self.hstate.set_role(wid, "werewolf")
        
    def get_replacements(self):
        replacements = super().get_replacements()
        werewolf_ids = str(self.private_info["werewolf_ids"])
        replacements.update({
            "{werewolf_ids}": werewolf_ids,
        })
        replacements.update({
            "{hstate}": str(self.hstate),
        })
        replacements.update({
            "{private}": f"All werewolves including you are {werewolf_ids}. Remember that you should work together to hide from other players and eliminate them."
        })
        #! TEMPORARY
        replacements.update({"{events}": str(self.event_book)})
        replacements.update({"{previous_advices}": self.show_previous_advices()})
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
        elif "kill" in available_actions or "night" in available_actions:
            res = self._kill()
            return {
                "action": "kill",
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
    
    def _kill(self, use_multiagent = False):
        if not use_multiagent:
            return self._kill_org()
        else:
            return self._kill_multiagent()
        
        
    def _get_proposals_from_response_KillThreeStep(self, response):
        # Regex to capture the first number after 'Firstly' and 'Secondly'
        first_number_pattern = r'Firstly.*?(\d+)'
        second_number_pattern = r'.*?Secondly.*?(\d+)'
        
        # Regex to capture the reason after 'the reason is'
        first_reason_pattern = r'Firstly.*?reason is:? (.*?)(?:\.|Secondly)'
        second_reason_pattern = r'.*?Secondly.*?reason is:? (.*)'
        
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
        print("baw;oiefnaw;oienaw;ioe", first_player, first_reason, second_player, second_reason)
        return first_player, first_reason, second_player, second_reason
    
    
    def _get_imagination_from_response_KillThreeStep(self, response):
        return response
    def _get_final_choice_from_response_KillThreeStep(self, response):
        return get_target_from_response(response)

    def _kill_multiagent(self):
        self.draft_dict["kill"].append(dict())
        first_player, first_reason, second_player, second_reason = None, None, None, None
        count = 0
        while ((first_player is None) or (second_player is None) or (first_reason is None) or (second_reason is None)) and (count < 3):
            count += 1
            response = self.get_response("kill_threeStage_propose")
            first_player, first_reason, second_player, second_reason = self._get_proposals_from_response_KillThreeStep(response)
        assert not ((first_player is None) or (second_player is None) or (first_reason is None) or (second_reason is None))
        
        proposals = [first_player, second_player]
        
        
        self.draft_dict["kill"][-1]["kill_proposal"] = proposals
        self.draft_dict["kill"][-1]["proposal_and_imaginations"] = list()
        result_list = list()
        for propose in proposals:
            replacements = self.get_replacements()
            replacements["{current_propose}"] = str(propose)
            response = self.get_response("kill_threeStage_imagine", replacements)
            
            results = self._get_imagination_from_response_KillThreeStep(response)
            result_list.append(results)
            self.draft_dict["kill"][-1]["proposal_and_imaginations"].append(response)
        
        replacements = self.get_replacements()
        replacements["{current_propose_0}"] = str(proposals[0])
        replacements["{current_propose_1}"] = str(proposals[1])
        replacements["{current_propose_0_imagination}"] = result_list[0]
        replacements["{current_propose_1_imagination}"] = result_list[1]
        
        
        
        response_and_reason = self.get_response("kill_threeStage_choose", replacements)
        kill = self._get_final_choice_from_response_KillThreeStep(response_and_reason)
        
        self.draft_dict["kill"][-1]["proposal_chosen_and_reasons"] = response_and_reason
        return kill, response

    def _kill_org(self):
        response = self.get_response("kill")
        kill = get_target_from_response(response)
        return kill, response

    def get_alive_werewolf_ids(self):
        return [wid for wid in self.private_info["werewolf_ids"] if wid in self.global_info["alive_players"]]
    
    def show_previous_advices(self):
        #! Aborted
        if self.private_info["previous_advices"] == []:
            s = "No previous advices."
        else:
            s = ""
            for id, target, reason in self.private_info["previous_advices"]:
                s += f"Player {id} advised to target Player {target} because {reason}\n"
        if len(self.private_info["previous_advices"]) == len(self.get_alive_werewolf_ids()) - 1:
            s += "Notice that you are the last werewolf, so your choice determines the final decision."
        return s
    