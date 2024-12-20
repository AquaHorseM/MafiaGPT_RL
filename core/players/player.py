import logging
import os
import time
import random
from typing import Dict, List
import numpy as np
from copy import deepcopy
from core.data import DataTree
from core.event import Event, EventBook
from core.players.utils import get_response
import re, pickle
from core.players.utils import parse_reflex_note, parse_reflex_actions, get_target_from_response
        
class Player:
    class HiddenState:
        def __init__(self, player_num, id):
            self.beliefs = [{
                "role": "unknown", #role should be unknown/werewolf/medic/seer/villager
                "confidence": "high", #confidence should be high/medium/low
                "reason": "There is no information yet." #any reason supporting the above conclusions
            }] * player_num
            self.id = id
            
            self.player_num = player_num
            
        def __str__(self) -> str:
            s = ""
            for i in range(self.player_num):
                if i==self.id:
                    continue
                s += f"Player {i}'s role is {self.beliefs[i]['role']} with {self.beliefs[i]['confidence']} confidence.\n"
                s += f"Reason is: {self.beliefs[i]['reason']}\n"
            return s
        
        def update(self, update_string):
            def extract_info(string):
                pattern = r"Player (\d+)'s role is (\w+)(?: with (high|medium|low) confidence)?\.\s*My reason is: (.*)?"
                match = re.match(pattern, string)
                if match:
                    
                    id = match.group(1)
                    role = match.group(2)
                    confidence = match.group(3) if match.group(3) else None
                    reason = match.group(4) if match.group(4) else None
                    return {
                        "id": id,
                        "role": role,
                        "confidence": confidence,
                        "reason": reason
                    }
                else:
                    return None
            result = extract_info(update_string)
            if result is None:
                return
            else:
                self.beliefs[int(result["id"])] = {
                    "role": result["role"],
                    "confidence": result["confidence"] if result["confidence"] is not None else self.beliefs[int(result["id"])],
                    "reason": result["reason"]
                }
                return
        
        def set_role(self, id, role):
            self.beliefs[id] = {
                "role": role,
                "confidence": "high",
                "reason": "Fact."
            }

                
                        
    def __init__(self, id, game_id, player_config, global_info, private_info, openai_client = None):
        self.is_alive = True
        self.id = id
        self.game_id = game_id
        self.labels = ["all"]
        self.tick = 0
        self.event_book = EventBook()
        self.prompt_dir_path = player_config.get("prompt_dir_path")
        assert self.prompt_dir_path is not None and os.path.exists(self.prompt_dir_path), f"Prompt dir path {self.prompt_dir_path} invalid or does not exist!"
        self.common_prompt_dir = player_config.get("common_prompt_dir_path")
        assert self.common_prompt_dir is not None and os.path.exists(self.common_prompt_dir), f"Prompt dir path {self.common_prompt_dir} invalid or does not exist!"
        self.openai_client = openai_client
        self.reflex_note_path_belief = player_config.get("reflex_note_belief_path", os.path.join(self.prompt_dir_path, "reflex_note_belief.txt"))
        self.reflex_note_path_policy = player_config.get("reflex_note_policy_path", os.path.join(self.prompt_dir_path, "reflex_note_policy.txt"))
        self.global_info = deepcopy(global_info)
        self.private_info = deepcopy(private_info)
        self.player_num = global_info["player_num"]
        self.hstate = self.HiddenState(global_info["player_num"], self.id)
        self.hstate.set_role(self.id, self.get_role())
        self.proposal_num = player_config.get("proposal_num", 2)
        self.sample_num = player_config.get("sample_num", 10)
        self.sample_type = player_config.get("sample_type", "heuristic")
        self.reflexable = player_config.get("reflexable", True)
        self.player_tag = player_config.get("player_tag", "NoTag")
        self.draft_dict = dict()
        self.draft_dict["vote"] = list()
        self.draft_dict["speak"] = list()
        self.draft_dict["see"]=list()
        self.draft_dict["kill"]=list()
        self.draft_dict["heal"]=list()
        self.logger = self._configure_logger()
        
    def _configure_logger(self):
        logger = logging.getLogger(f"Game-{self.game_id}-Player-{self.id}-{self.get_role()}")
        if not logger.hasHandlers():
            logger.setLevel(logging.DEBUG)
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        return logger    
        
    def get_replacements(self):
        with open(self.reflex_note_path_belief, "r") as f:
            reflex_note_belief = f.read()
        with open(self.reflex_note_path_policy, "r") as f:
            reflex_note_policy = f.read()
        current_round = self.global_info["current_round"] if self.global_info.get("current_round") is not None else self.global_info["game_status"]["cur_round"]
        return {
            "{player_id}": str(self.id),
            "{player_num}": str(self.player_num),
            "{alive_players}": str(list(self.global_info["alive_players"])),
            "{dead_players}": str(self.global_info["dead_players"]) if len(self.global_info["dead_players"]) > 0 else "Nobody",
            "{current_round}": str(current_round + 1), #! notice the +1 here
            "{role}": str(self.private_info["role"]),
            "{previous_votes}": str(self.global_info["previous_votes"]),
            "{reflex_note_belief}": str(reflex_note_belief),
            "{reflex_note_policy}": str(reflex_note_policy),
            "{hstate}": str(self.hstate),
            "{proposal_num}": str(self.proposal_num), #!
            "{vis_events}": str(self.event_book)
        }
            

    def __str__(self):
        return f"Player {self.id}"
    
    def update_hstate(self, event_book: EventBook):
        if event_book.tick == self.tick:
            return
        self._update_hstate(self.filter_event_book(event_book))
        self.tick = event_book.tick
    
    def _act(self, available_actions = None): #return (action, target, reason, imagination)
        if len(available_actions) == 0:
            return (None, None, "No available actions.")
        else:
            action = random.choice(available_actions)
            target = random.choice(self.global_info["alive_players"])
            reason = "I am the baseline player and I do things randomly."
            return (action, target, reason)
        
    
    
    def _convert_proposals_and_reasons_to_vote_prompt(self, proposal_dicts: List[Dict]):
        s = ""
        for i, pd in enumerate(proposal_dicts):
            target = pd["target"]
            imagination = pd["imagination"]
            s += f"Case {i+1}: Vote for Player {target}. What could happen is: {imagination}\n"
        return s
    
    def _convert_proposals_to_speech_prompt(self, proposal_dicts: List[Dict]):
        s = ""
        for i, pd in enumerate(proposal_dicts):
            speech = pd["speech"]
            imagination = pd["imagination"]
            s += f"Case {i+1}: {speech}. What could happen is: {imagination}\n"
        return s
    
    
    def _get_proposals_from_response_VoteThreeStep(self, response):
        # Regular expression to match proposals and reasons more flexibly
        pattern = r"Proposal\s*(\d+)\s*:\s*(.*?)\s*\.?\s*Reason\s*:\s*(.*?)(?=\s*[.\n]?\s*Proposal|\Z)"
        # pattern = r"Proposal\s*(\d+)\s*:\s*(.*?)\s*\.?\s*Reason\s*:\s*(.*?)"
        matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)
        self.logger.debug(f"Altogether {len(matches)} matches!")
        
        result = []
        for i, match in enumerate(matches):
            try:
                proposal_text = match[1].strip()
                proposal_target = get_target_from_response(proposal_text)
                reason_text = match[2].strip()
                
                # Only add to result if both proposal and reason are non-empty
                if proposal_target and reason_text:
                    result.append({
                        "target": proposal_target, 
                        "reason": reason_text
                    })
            except ValueError:
                # Ignore this match if the proposal ID is not an integer
                return None
        
        return result
    
    
    def _get_imagination_from_response_VoteThreeStep(self, response):
        return response
    def _get_final_choice_from_response_VoteThreeStep(self, response):
        return get_target_from_response(response)
    
    def _vote(self, use_multiagent = True):
        vote, response = self._vote_org() if not use_multiagent else self._vote_multiagent()
        return vote, response
    
    def _vote_multiagent(self):
        self.draft_dict["vote"].append(dict())
        proposal_dicts = None
        count = 0
        while (proposal_dicts is None) and (count < 3):
            count += 1
            response = self.get_response("vote_threeStage_propose")
            proposal_dicts = self._get_proposals_from_response_VoteThreeStep(response)
        assert proposal_dicts is not None
        for proposal_dict in proposal_dicts:
            target = proposal_dict["target"]
            reason = proposal_dict["reason"]
            # self.logger.debug(f"Target: {target}. Reason: {reason}.")
        proposals = [elem["target"] for elem in proposal_dicts]
        
        self.draft_dict["vote"][-1]["vote_proposal"] = proposals
        self.draft_dict["vote"][-1]["proposal_and_imaginations"] = []
        for proposal_id in range(len(proposals)):
            replacements = self.get_replacements()
            replacements["{current_propose}"] = str(proposals[proposal_id])
            response = self.get_response("vote_threeStage_imagine", replacements)
            
            results = self._get_imagination_from_response_VoteThreeStep(response)
            proposal_dicts[proposal_id]["imagination"] = results
            self.draft_dict["vote"][-1]["proposal_and_imaginations"].append(response)
        
        replacements = self.get_replacements()
        replacements.update({
            "{proposal_infos}": self._convert_proposals_and_reasons_to_vote_prompt(proposal_dicts)
        })
        
        response_and_reason = self.get_response("vote_threeStage_choose", replacements)
        vote = self._get_final_choice_from_response_VoteThreeStep(response_and_reason)
        
        self.draft_dict["vote"][-1]["proposal_chosen_and_reasons"] = response_and_reason
        if vote in proposals:
            self.draft_dict["vote"][-1]["final_proposal"] = proposals.index(vote)
        else:
            self.logger.warning(f"Final vote {vote} not in proposals {proposals}!")
            self.draft_dict["vote"][-1]["final_proposal"] = 0
        return vote, response_and_reason

    def _vote_org(self):
        response = self.get_response("vote")
        vote = get_target_from_response(response)
        return vote, response

    def _get_speak_type(self): #aborted
        response = self.get_response("speak_type")
        assert isinstance(response, str), f"response is not a string: {response}"
        #Find the [type] in the response
        s_type = re.search(r"\[(.*?)\]", response).group(1).lower()
        s_type = s_type.strip().split(",") #split the types
        s_type = [s.strip() for s in s_type]
        return s_type
    
    def speak_with_type(self, s_type): #aborted
        replacements = self.get_replacements()
        replacements.update({
            "{speech_type}": str(s_type)
        })
        response = self.get_response("speak_with_type", replacements)
        return response
    
    
    
    def _get_proposals_from_response_SpeakThreeStep(self, response):
        # Regular expression to match proposals more flexibly
        pattern = r"Proposal\s*(\d+)\s*:\s*(.*?)(?=\s*\.?\s*Proposal|$)"
        matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)
        
        result = []
        for match in matches:
            try:
                proposal_id = int(match[0])  # Ensure the proposal ID is an integer
                proposal_text = match[1].strip()
                
                # Only add to result if proposal text is non-empty
                if proposal_text:
                    result.append(proposal_text)
            except ValueError:
                return None
        
        return result
        
    def _get_imagination_from_response_SpeakThreeStep(self, response):
        #format unifying; no need to do anything here
        return response
    
    def _get_final_choice_from_response_SpokeThreeStep(self, response):
        first_pattern = r"I choose Proposal (\d).*My final speech is:(.*)"
        first_match = re.search(first_pattern, response, re.DOTALL)
        
        proposal = first_match.group(1) if first_match else None
        speech = first_match.group(2).strip() if first_match else "Speech not recognized."
        return proposal, speech
    
    def _speak_multiagent(self):
        self.draft_dict["speak"].append(dict())
        proposals = None
        count = 0
        
        # Attempt to get proposals within the allowed attempts
        while (proposals is None) and (count < 3):
            count += 1
            response = self.get_response("speak_threeStage_propose")
            proposals = self._get_proposals_from_response_SpeakThreeStep(response)
        
        # Ensure proposals are retrieved
        assert proposals is not None
        
        self.draft_dict["speak"][-1]["speak_proposal"] = proposals
        self.draft_dict["speak"][-1]["proposal_and_imaginations"] = []
        result_list = []
        proposal_dicts = []

        # Get imaginations for each proposal
        for propose in proposals:
            replacements = self.get_replacements()
            replacements["{current_propose}"] = str(propose)
            response = self.get_response("speak_threeStage_imagine", replacements)
            
            results = self._get_imagination_from_response_SpeakThreeStep(response)
            result_list.append(results)
            self.draft_dict["speak"][-1]["proposal_and_imaginations"].append(response)
            proposal_dicts.append({
                "speech": propose,
                "imagination": results
            })

        # Prepare replacements for choosing the final proposal
        replacements = self.get_replacements()
        replacements.update({
            "{proposal_infos}": self._convert_proposals_to_speech_prompt(proposal_dicts)
        })

        response_and_reason = self.get_response("speak_threeStage_choose", replacements)
        proposal_id, speak = self._get_final_choice_from_response_SpokeThreeStep(response_and_reason)

        self.draft_dict["speak"][-1]["final_speech"] = speak
        self.draft_dict["speak"][-1]["final_proposal"] = int(proposal_id) - 1
        return speak

    def _speak(self, use_multiagent = True):
        returned = self._speak_org() if not use_multiagent else self._speak_multiagent()
        return returned

    def _speak_org(self):
        s_type = self._get_speak_type()
        response = self.speak_with_type(s_type)
        return response
    
    def previous_votes(self):
        return self.global_info["previous_votes"]

    def filter_event_book(self, event_book: EventBook):
        return event_book.filter(start_tick=self.tick, id=self.id, labels=self.labels)
    
    def get_role(self):
        return self.private_info["role"]
    
    def get_beliefs(self):
        return self.hstate.beliefs
    
    def _update_hstate(self, events):
        for _ in range(3):
            try:
                event_des = ""
                for event in events:
                    event_des += str(event)
                    event_des += "\n"
                replacements = self.get_replacements()
                replacements.update({
                    "{event_des}": event_des,
                    "{prev_events}": str(self.event_book)
                })
                response = self.get_response("update_hstate", replacements=replacements)
                for line in response.split("\n"):
                    self.hstate.update(line)
                self.event_book.add_event(events)
                return
            except Exception as e:
                print("Exception in _update_hstate, sleep for 5 seconds and try again. Exception:", e)
                time.sleep(5)
                continue
        raise Exception("update hidden state, error for three times.")

    '''
    The following functions are defined to be consistent with the baseline version.
    DO NOT use them in the future.
    '''
    
    def healing(self):
        return self._act(available_actions = ["heal"])
    
    def inquiry(self):
        return self._act(available_actions = ["see"])
    
    def kill(self):
        return self._act(available_actions = ["kill"])
    
    '''
    The following functions are defined for saving and loading checkpoints.
    '''
    
    def save_checkpoint(self, path):
        info = {
            "prompt_dir_path": self.prompt_dir_path,
            "private_info": self.private_info,
        }
        if path is not None:
            with open(path, 'wb') as file:
                pickle.dump(info, file)
        return info
    
    def filter_reflex_event(self, event):
        if isinstance(event.visible, str):
            if event.visible not in self.labels:
                return False
        elif isinstance(event.visible, list):
            if all(label not in event.visible for label in self.labels):
                return False
        return True
    
    def get_node_importance_for_policy(self, state, prev_events, trajs, sample_type: str = "heuristic"):
        if len(trajs) == 0:
            return 0.0001
        if sample_type == "uniform":
            return 1
        reflex_info = self.extract_reflex_info(state, prev_events, trajs)
        cur_score = self.evaluate_joint_hstate(reflex_info["hstate"], reflex_info["alive_players"])
        total_score = 0.5
        for traj in reflex_info["trajs"]:
            traj_score = self.evaluate_joint_hstate(traj["outcome_hstate"], traj["outcome_alive_players"])
            total_score += (cur_score - traj_score) ** 2
        total_score /= np.sqrt(len(reflex_info["trajs"]))
        return total_score
            
    def get_node_importance_for_belief(self, state, prev_events, trajs, sample_type: str = "heuristic"):
        if len(trajs) == 0:
            return 0.0001
        if sample_type == "uniform":
            return 1
        elif sample_type == "heuristic":
            reflex_info = self.extract_reflex_info(state, prev_events, trajs)
            cur_score = self.get_hstate_score_for_belief(reflex_info["hstate"])
            total_score = 0.5
            for traj in reflex_info["trajs"]:
                traj_score = self.get_hstate_score_for_belief(traj["outcome_hstate"])
                total_score += (cur_score - traj_score) ** 2
            total_score /= len(reflex_info["trajs"])
            return total_score

    
    def reflex(self, data : DataTree):
        sample_type = self.sample_type
        reflex_data_belief = data.sample(self.id, sample_num = 1000)
        reflex_data_policy = data.sample(self.id, filter_events = True, sample_num = 1000)
        sample_num = self.sample_num
        self.logger.info(f"reflex note path for belief is: {str(os.path.abspath(self.reflex_note_path_belief))}")
        self.logger.info(f"reflex note path for policy is: {str(os.path.abspath(self.reflex_note_path_policy))}")
        def get_elems(d):
            dat = data.parse(d)
            state, prev_events, trajs = dat["state"], dat["prev_events"], dat["trajs"]
            if state is None:
                return None
            return (state, prev_events, trajs)
        reflex_data_belief = [get_elems(d) for d in reflex_data_belief]
        reflex_data_belief = [i for i in reflex_data_belief if i is not None]
        if len(reflex_data_belief) > sample_num:
            weights_belief = [self.get_node_importance_for_belief(elem[0], elem[1], elem[2], sample_type) for elem in reflex_data_belief]
            reflex_data_belief = random.choices(reflex_data_belief, weights_belief, k=sample_num)
        reflex_data_policy = [get_elems(d) for d in reflex_data_policy]
        reflex_data_policy = [i for i in reflex_data_policy if i is not None]
        if len(reflex_data_policy) > sample_num:
            weights_policy = [self.get_node_importance_for_policy(elem[0], elem[1], elem[2], sample_type) for elem in reflex_data_policy]
            reflex_data_policy = random.choices(reflex_data_policy, weights_policy, k=sample_num)
        self.logger.info(f"Data ready for reflex!")
        for state, prev_events, trajs in reflex_data_belief:
            try:
                self.reflex_belief(state, prev_events, trajs)
            except Exception as e:
                self.logger.warning(f"Error encountered while reflexing belief: {e}")
        for state, prev_events, trajs in reflex_data_policy:
            try:
                self.reflex_policy(state, prev_events, trajs)
            except Exception as e:
                self.logger.warning(f"Error encountered while reflexing policy: {e}")
        self.logger.info("Finished reflex; now polish reflex notes.")
        self.polish_reflex_notes()
        return

    def extract_traj(self, traj):
        return {
            "actions": traj["actions"],
            "all_events": [str(event) for event in traj["events"]],
            "visible_events": [str(event) for event in traj["events"] if self.filter_reflex_event(event)],
            "outcome_hstate": traj["outcome"]["hstate"],
            "outcome_alive_players": traj["outcome"]["global_info"]["alive_players"],
            "after_events": traj["after_events"],
            "connect_to_end": traj["connect_to_end"] if traj.get("connect_to_end") is not None else False,
            "draft": traj["drafts"][self.id]
        }
        
    def get_hstate_score_for_belief(self, joint_hstate, roles = None):
        #naive approach
        #always non-negative
        own_belief = joint_hstate[self.id]
        def get_wrong(own_belief_role, true_role):
            if own_belief_role == "unknown":
                return 0.5
            else:
                return 0 if own_belief_role.lower() == true_role.lower() else 1
        if roles is None:
            roles = [joint_hstate[i][i]["role"] for i in range(self.player_num)]
        wrongs = [get_wrong(own_belief[i]["role"], roles[i]) for i in range(self.player_num)]
        confidences = [own_belief[i]["confidence"] for i in range(self.player_num)]
        def get_weight(confidence):
            if confidence == "high":
                return 1
            elif confidence == "medium":
                return 0.5
            elif confidence == "low":
                return 0
            else:
                raise ValueError("confidence not spotted")
        weights = [get_weight(i) for i in confidences]
        importance = sum([wrongs[i] * weights[i] for i in range(self.player_num)])
        return importance
    
    def evaluate_joint_hstate(self, joint_hstate, alive_players = None):
        #TODO make it more complete for other roles
        s = 0 #base weight
        def confidence_to_weight(confidence):
            if confidence == "high":
                return 3
            elif confidence == "medium":
                return 2
            elif confidence == "low":
                return 1
        if alive_players is not None:
            for i in range(self.player_num):
                if i in alive_players:
                    continue
                if joint_hstate[i][i]["role"] == "werewolf":
                    w = 3
                    sgn = 1 if (self.get_role() != "werewolf") else -1
                elif joint_hstate[i][i]["role"] == "villager":
                    w = 2
                    sgn = 1 if (self.get_role() == "werewolf") else -1
                elif joint_hstate[i][i]["role"] in ["medic", "seer"]:
                    w = 4
                    sgn = 1 if (self.get_role() == "werewolf") else -1
                else:
                    continue
                s += (w*sgn)
        for i in range(self.player_num):
            if alive_players is not None and i not in alive_players:
                continue
            if joint_hstate[i][i]["role"] == "werewolf":
                continue
            for j in range(self.player_num):
                if alive_players is not None and j not in alive_players:
                    continue
                if joint_hstate[i][j]["role"] == "werewolf":
                    confidence = joint_hstate[i][j]["confidence"]
                    w = confidence_to_weight(confidence)
                    sgn = 1 if (joint_hstate[j][j]["role"] == "werewolf") != (self.get_role() == "werewolf") else -1
                    s += (w * sgn)
                else:
                    confidence = joint_hstate[i][j]["confidence"]
                    w = confidence_to_weight(confidence)
                    sgn = 1 if (joint_hstate[j][j]["role"] == "werewolf") == (self.get_role() == "werewolf") else -1
                    s += (w * sgn)
        return s

    def get_traj_importance_for_policy(self, traj, init_jhstate, init_alive_players):
        #How to use it to sample more important nodes?
        if traj["actions"][self.id] is None or not traj["connect_to_end"]:
            return 0.001
        return 1 + (self.evaluate_joint_hstate(traj["outcome_hstate"], traj["outcome_alive_players"]) - \
            self.evaluate_joint_hstate(init_jhstate, init_alive_players))**2
    
    def summarize_events(self, events: List[Event]):
        replacements = self.get_replacements()
        event_txt = '\n'.join([str(event) for event in events])
        replacements.update({
            "{all_events}": event_txt
        })
        res = self.get_response("summarize_events", replacements)
        return res

    def extract_reflex_info(self, state, prev_events, trajs):
        return {
            "hstate": state["hstate"],
            "roles": [state["private_infos"][i]["role"] for i in range(self.player_num)],
            "alive_players": state["global_info"]["alive_players"],
            "all_prev_events": [str(event) for event in prev_events],
            "visible_prev_events": [str(event) for event in prev_events if self.filter_reflex_event(event)],
            "trajs": [self.extract_traj(traj) for traj in trajs],
        }
    
    def convert_draft_to_prompt(self, draft: Dict):
        if draft["cur_action"] not in ["vote", "speak"]:
            return ""
        else:
            s = "\nThe following is your proposals and your imagination of your action.\n\n"
            if draft["cur_action"] == "vote":
                for i in range(len(draft["vote_proposal"])):
                    s += f"Proposal: vote for player {draft['vote_proposal'][i]}\n"
                    s += f"Imagination: {draft['proposal_and_imaginations'][i]}\n\n"
                s += f"Your FINAL decision was to vote for player\n {draft['proposal_chosen_and_reasons']}\n"
            elif draft["cur_action"] == "speak":
                for i in range(len(draft["speak_proposal"])):
                    s += f"Speech proposal: {draft['speak_proposal'][i]}\n"
                    s += f"Imagination: {draft['proposal_and_imaginations'][i]}\n\n"
                s += f"You finally chose proposal {draft['final_proposal']}.\n\n"
                s += f"Your FINAL speech:\n \"{draft['final_speech']}\"\n"
        return s
    
    def _speak_with_other_proposal(self, draft: Dict):
        draft["final_proposal"] = int(draft["final_proposal"])
        if len(draft["speak_proposal"]) <= 1:
            return None
        else:
            ids = list(range(len(draft["speak_proposal"])))
            ids.pop(draft["final_proposal"])
            new_proposal_id = random.choice(ids)
        replacements = self.get_replacements()
        replacements["{current_propose}"] = str(draft['speak_proposal'][new_proposal_id])
        
        response = self.get_response("speak_other_proposal", replacements)
        speech_match = re.match(r"My final speech is:(.*)", response.strip())
        if speech_match is not None:
            final_speech = speech_match.group().strip()
        else:
            final_speech = "Unrecognized speech, skipped by system."
        self.draft_dict["speak"].append(deepcopy(draft))
        self.draft_dict["speak"][-1]["final_speech"] = final_speech
        self.draft_dict["speak"][-1]["final_proposal"] = new_proposal_id
        return {
            "action": "speak",
            "target": final_speech,
            "reason": None,
            "imagination": None        
        }
    
    def _vote_with_other_proposal(self, draft: Dict):
        if len(draft["vote_proposal"]) <= 1:
            new_proposal_id = draft["final_proposal"]
        else:
            ids = list(range(len(draft["vote_proposal"])))
            ids.pop(draft["final_proposal"])
            new_proposal_id = random.choice(ids)
        new_target = draft['vote_proposal'][new_proposal_id]
        self.draft_dict["vote"].append(deepcopy(draft))
        self.draft_dict["vote"][-1]["final_proposal"] = new_proposal_id
        return {
            "action": "vote",
            "target": new_target,
            "reason": None,
            "imagination": None        
        }

        
    def convert_reflex_info_to_policy_prompt(self, reflex_info: Dict, vis_prev_events = True) -> str:
        def show_all_other_beliefs():
            s = ""
            for i in range(self.player_num):
                if i == self.id:
                    continue
                s += f"Player {i} believes:\n"
                for j in range(self.player_num):
                    if j == i:
                        continue
                    s += f"Player {j} is {reflex_info['hstate'][i][j]['role']} with {reflex_info['hstate'][i][j]['confidence']} confidence.\n"
            return s
        if len(reflex_info["trajs"]) > 1:
            weights = [self.get_traj_importance_for_policy(traj, reflex_info["hstate"], reflex_info["alive_players"]) for traj in reflex_info["trajs"]]
            traj = random.choices(reflex_info["trajs"], weights=weights, k=1)[0]
        else:
            traj = reflex_info["trajs"][0]
        s = ""
        s += "\nThese are the ACTUAL ROLES of the players.\n\n"
        for i in range(self.player_num):
            s += f"Player {i} is {reflex_info['roles'][i]}\n"
        if vis_prev_events:
            s += "\nThese are ALL events happened previously that you observed (notice other players' night actions and system actions were not observable in your game, but only serve here as a reference):\n\n"
            for e in reflex_info["all_prev_events"]:
                s += e
                s += '\n'
        s += "\nThese are the beliefs of all other players.\n\n"
        s += show_all_other_beliefs()
        action_type = traj["actions"][self.id]["action"]
        s += f"\n Your next action should be {action_type}.\n"
        s += self.convert_draft_to_prompt(traj["draft"])
        s += "\nThese are the beliefs of all other players after your action.\n\n"
        s += show_all_other_beliefs()
        
        s += "\n This is a summary of what happens after your final decided action:\n\n" 
        s += self.summarize_events(traj["after_events"])
        s += "Think about the following questions: Among these events, what are the direct consequences of your action? Perhaps you would have reached a better outome with a different action?"
        
        if len(reflex_info["trajs"]) > 1:
            other_traj = random.choice([traj_cand for traj_cand in reflex_info["trajs"] if traj_cand != traj])
            other_draft = other_traj["draft"]
            if other_draft["cur_action"] not in ["vote", "speak"]:
                pass
            else:
                #TODO how to combine the other traj?
                if other_draft["cur_action"] == "speak":
                    if self.evaluate_joint_hstate(other_traj["outcome_hstate"], other_traj["outcome_alive_players"]) >= \
                        self.evaluate_joint_hstate(traj["outcome_hstate"], traj["outcome_alive_players"]):
                        s += f"\n\nThe system also simulated the game for your other proposal, which is proposal {other_draft['final_proposal']}."
                        s += f"\n\nYour speech, in this case, is: \"{other_draft['final_speech']}\""
                        s += "System automatically evaluates it as a potentially better speech than your previous speech."
                    else:
                        s += f"\n\nThe system also made an automatic evaluation for your other proposal, which is proposal {other_draft['final_proposal']}."
                        s += f"\n\nHowever, it might be less potential compared to your final chosen proposal. You've potentially made a correct choice."
                elif other_draft["cur_action"] == "vote":
                    # if self.evaluate_joint_hstate(other_traj["outcome_hstate"], other_traj["outcome_alive_players"]) >= \
                    #     self.evaluate_joint_hstate(traj["outcome_hstate"], traj["outcome_alive_players"]):
                    s += f"\n\nThe system also simulated the game for your other vote, which is to vote for {other_draft['final_proposal']}.\n"
                    s += "These are the beliefs of all other players after this action: \n\n"
                    s += show_all_other_beliefs()                        
        return s
        
    
    def convert_reflex_info_to_belief_prompt(self, reflex_info: Dict) -> str: #TEMP
        if len(reflex_info["trajs"]) > 1:
            weights = [self.get_hstate_score_for_belief(traj["outcome_hstate"], reflex_info["roles"]) for traj in reflex_info["trajs"]]
            traj = random.choices(reflex_info["trajs"], weights=weights, k=1)[0]
        else:
            traj = reflex_info["trajs"][0]
        s = ""
        s += "\nThese are the ACTUAL ROLES of the players.\n\n"
        for i in range(self.player_num):
            s += f"Player {i} is {reflex_info['roles'][i]}\n"
        s += "\nThese are ALL events happened previously that you observed:\n\n"
        for e in reflex_info["visible_prev_events"]:
            s += e
            s += '\n'
        s += "\nThe following is YOUR belief AFTER THESE EVENTS\n\n"
        s += str(reflex_info["hstate"][self.id])
        s += "\n\nThese are the new events happening.\n\n"
        for e in traj["visible_events"]:
            s += e
            s += '\n'
        s += "\nThese are YOUR updated belief AFTER THESE NEW EVENTS:\n\n"
        s += str(traj["outcome_hstate"][self.id])
        return s
    
    def reflex_policy(self, state, prev_events, trajs):
        if len(trajs) == 0:
            return
        reflex_info = self.extract_reflex_info(state, prev_events, trajs)
        replacements = self.get_replacements()
        replacements.update({
            "{reflex_info}": self.convert_reflex_info_to_policy_prompt(reflex_info)
        })
        res = self.get_response("reflex_policy", replacements)
        self.update_note_from_response(res, "policy")
        return
    
    def reflex_belief(self, state, prev_events, trajs):
        if len(trajs) == 0:
            return
        reflex_info = self.extract_reflex_info(state, prev_events, trajs)
        replacements = self.get_replacements()
        replacements.update({
            "{reflex_info}": self.convert_reflex_info_to_belief_prompt(reflex_info)
        })
        res = self.get_response("reflex_belief", replacements)
        self.update_note_from_response(res, "belief")
        return
    
    def polish_reflex_note(self, note_type = "belief"):
        if note_type == "belief":
            reflex_note_path = self.reflex_note_path_belief
        elif note_type == "policy":
            reflex_note_path = self.reflex_note_path_policy
        else:
            raise ValueError("Note type must be either 'belief' or 'policy'")
        replacements = self.get_replacements()
        replacements.update({
            "{reflex_note}": open(reflex_note_path, "r").read(),
            "{note_type}": note_type
        })
        response = self.get_response("polish_reflex_note", replacements = replacements)
        # original_note = parse_reflex_note(open(reflex_note_path, "r").read())
        with open(reflex_note_path, "w") as f:
            for line in response.split("\n"):
                self.logger.info(f"line: {line}")
                if len(line.strip()) <= 5:
                    continue
                try:
                    id, rule, vote = re.search(r"\[(\d+)\] \[(.*)\] \[(\d+)\]", line).groups()
                    id = int(id)
                    vote = int(vote)
                    f.write(f"[{id}] [{rule}] [{vote}]\n")
                except:
                    self.logger.info(f"Unable to process line {line}")
        return
        
    def polish_reflex_notes(self):
        self.polish_reflex_note("belief")
        self.polish_reflex_note("policy")
        return
    
    
    def update_note_from_response(self, response, note_type = "belief"): #note type: ["belief", "policy"]
        if note_type == "belief":
            reflex_note_path = self.reflex_note_path_belief
        elif note_type == "policy":
            reflex_note_path = self.reflex_note_path_policy
        else:
            raise ValueError("Note type must be either 'belief' or 'policy'")
        with open(reflex_note_path, "r") as f:
            reflex_note = f.read()
        # self.logger.debug(f"Updating reflex note with response {response}")
        operations = parse_reflex_actions(response)
        reflex_note = parse_reflex_note(reflex_note)
        max_id = max(reflex_note.keys()) if reflex_note.keys() else -1
        for action in operations:
            operation, value1, value2 = action
            self.logger.info(f"player {self.id} is updating the reflex note with operation {operation} {value1} {value2}")
            if operation == "UPVOTE": #value1 is the id, value2 should be None
                if reflex_note.get(value1) is None:
                    pass
                else:
                    reflex_note[value1][1] = min(10, reflex_note[value1][1] + 1)
            elif operation == "DOWNVOTE": #value1 is the id, value2 should be None
                if reflex_note.get(value1) is None:
                    pass
                else:
                    reflex_note[value1][1] -= 1
                    if reflex_note[value1][1] <= 1:
                        reflex_note.pop(value1)
            elif operation == "CREATE": #value1 is the new rule, value2 should be None
                reflex_note[max_id + 1] = [value1, 4]
                max_id += 1
            elif operation == "REPLACE": #value1 is the id, value2 is the new rule
                if reflex_note.get(value1) is None:
                    reflex_note[value1] = [value2, 4]
                else:
                    reflex_note[value1][0] = value2
        
        #Sort the rules by the votes and give them new ids
        
        reflex_note = dict(sorted(reflex_note.items(), key=lambda x: x[1][1], reverse=True))
        new_reflex_note = {}
        for i, key in enumerate(reflex_note.keys()):
            new_reflex_note[i] = reflex_note[key]
        reflex_note = deepcopy(new_reflex_note)
        with open("debug.out", "a") as f:
            f.write(f"new reflex note: {reflex_note}\n")
        
        with open(reflex_note_path, "w") as f:
            for key, value in reflex_note.items():
                f.write(f"[{key}] [{value[0]}] [{value[1]}]\n")
                
    def reflex_from_data_path(self, data_path):
        data = pickle.load(open(data_path, "rb"))
        self.reflex(data)
        return
    
    def reset(self):
        self.hstate = self.HiddenState(self.player_num, self.id)
        
    def backtrace(self, back_step = 1, hstate = None, global_info = None, private_info = None):
        self.event_book.backtrace(back_step)
        if hstate is not None:
            self.hstate = deepcopy(hstate)
        if global_info is not None:
            self.global_info = deepcopy(global_info)
        if private_info is not None:
            self.private_info = deepcopy(private_info)
    
    def get_response(self, prompt_name, replacements = None):
        if replacements is None:
            replacements = self.get_replacements()
        cnt = 0
        while cnt < 10:
            try:
                return get_response(self.prompt_dir_path, self.common_prompt_dir, prompt_name, replacements, client = self.openai_client)
            except Exception as e:
                cnt += 1
                self.logger.warning(f"Exception encountered: {e}")
        return "Failed to get response."