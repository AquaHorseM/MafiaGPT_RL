import random, logging
from core.api import send_message
import json, re
from prompts import render_prompts as render
from core.baseline_players import Villager, Werewolf, Medic, Seer
from core.event import Event, EventBook
from core.players.werewolf import WerewolfPlayer


class Game:
    def __init__(self, id=1):
        self.id = id
        self.all_players = []
        self.alive_players = []
        self.dead_players = []
        self.report = []
        self.votes = []
        self.log = []
        self.player_types = []
        self.event_book = EventBook()
        self.logger = self._configure_logger()

    def _configure_logger(self):
        logger = logging.getLogger(f"Game-{self.id}")
        logger.setLevel(logging.DEBUG)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        return logger

    def log_submit(self, data):
        self.log.append(data)
        self.logger.info(str(data))

    def set_players(
        self, player_configs #a list of dicts
    ):
        player_num = len(player_configs)
        shuffled_nums = range(player_num)
        random.shuffle(shuffled_nums)
        
        werewolf_ids = [] 
        
        
        for num in shuffled_nums:
            if player_configs[num]["role"].lower() == "werewolf":
                werewolf_ids.append(num)
        
        init_global_info = {
            "player_num": player_num,
            "alive_players": range(player_num),
            "dead_players": [],
            "current_round": 0, #0 indicates the game hasn't started
            "roles_mapping": {
                "villager": 0,
                "werewolf": 1,
                "medic": 2,
                "seer": 3
            },
            "previous_votes": []
        }
                
        init_werewolf_private_info = {
            "role": "werewolf",
            "werewolf_ids": werewolf_ids,
            "kill_history": []
        }
        
        init_villager_private_info = {
            "role": "villager",
        }
        
        init_medic_private_info = {
            "role": "medic",
            "heal_history": []
        }
        
        init_seer_private_info = {
            "role": "seer",
            "inquire_history": []
        }
        
        for i, num in enumerate(shuffled_nums):
            role = player_configs[num]["role"].lower()
            player_type = player_configs[num]["player_type"].lower()
            self.player_types.append(player_type)
            
            if role == "werewolf":
                if player_type == "baseline":
                    self.all_players.append(Werewolf(role="werewolf", id=i))
                    self.all_players[-1].special_actions_log.append(
                        f"you are werewolf and this is your team (they are all werewolf) : {werewolf_ids}"
                    )
                elif player_type == "reflex":
                    self.all_players.append(WerewolfPlayer(i, init_global_info, init_werewolf_private_info, "core/players/prompts/werewolf"))
            elif role == "villager":
                if player_type == "baseline":
                    self.all_players.append(Villager(role="villager", id=i))
            elif role == "medic":
                if player_type == "baseline":
                    self.all_players.append(Medic(role="medic", id=i))
            elif role == "seer":
                if player_type == "baseline":
                    self.all_players.append(Villager(role="seer", id=i))

            self.add_event("set_player", {"id": i, "role": role, "player_type": player_type, "visible": "system"})

        self.alive_players = range(player_num)
        self.dead_players = []        
            
        

    def get_player(self, id):
        #debug 
        print(id, self.all_players[id])
        return self.all_players[id]

    def get_alive_werewolves(self):
        ls = list(filter(lambda player: self.all_players[player].get_role() == "werewolf", self.alive_players))
        # to make sure that last werewolf will make the last decision
        ls[-1].rank = "leader"
        return ls

    def get_alive_medics(self):
        return list(filter(lambda player: self.all_players[player].get_role() == "medic", self.alive_players))

    def get_alive_seers(self):
        return list(filter(lambda player: self.all_players[player].get_role() == "seer", self.alive_players))

    def get_alive_villagers(self):
        return list(
            filter(lambda player: self.all_players[player].get_role() == "villager", self.alive_players)
        )
        
    def vote_out(self, player_id):
        if player_id not in self.alive_players:
            self.logger.warning("Voting out an already dead guy! Skipped!")
            return
        self.alive_players.remove(player_id)
        self.dead_players.append(player_id)
        self.add_event("vote_out", {"player": player_id, "visible": "all"})

    def kill(self, player_id):
        if player_id not in self.alive_players:
            self.logger.warning("Killing an already dead guy! Skipped!")
            return
        self.alive_players.remove(player_id)
        self.dead_players.append(player_id)
        self.add_event("kill", {"player": player_id, "visible": "werewolf"})
        return

    def is_game_end(self):
        """
        Will check that the game is over or not.
        """
        werewolves = self.get_alive_werewolves()
        if len(werewolves) >= len(self.alive_players) / 2:
            self.add_event({"event": "end", "winner": "Werewolves"})
            return True
        if len(werewolves) == 0:
            self.add_event({"event": "end", "winner": "Villagers"})
            return True
        return False

    def check_votes(self):
        # [TODO] : debugging here
        votes = self.votes[-1]
        if max(votes) > 1:
            votes_sorted = dict(sorted(votes.items(), key=lambda x: x[1]))
            self.vote_out(self.get_player(list(votes_sorted.keys())[-1]))
        if self.is_game_end():  # to check if game is over by votes
            self.save_game()
        return
    
    def add_event(self, event):
        if isinstance(event, Event):
            self.event_book.add_event(event)
            self.log_submit(event)
        else:
            assert isinstance(event, dict), "event must be a dict or an instance of Event"
            if "visible" not in event:
                event["visible"] = "all"
            self.add_event(Event(event))

    def run_day(self):
        self.report = []
        for Player in self.alive_players:
            res = Player.speak(self, render.speech_command()).replace("\n", " ") #
            self.report.append(str(Player) + "opinion : " + res)
            self.add_event(
                {"event": "speech", "content": {"player": Player.id, "context": res}}
            )
        votes = [0] * 7
        self.add_event({"event": "vote_start"})
        for player_id in self.alive_players:
            target_voted, reason = self.all_players[player_id].vote(self)
            if target_voted:
                self.add_event(
                    {
                        "event": "voted",
                        "content": {
                            "player": Player.id,
                            "voted_to_player": target_voted,
                            "reason": reason,
                        },
                    }
                )
                votes[target_voted] += 1
                self.report.append(f"{Player} Voted to {target_voted}")
            else:
                self.logger.warning(f"{Player} skipped the voting")
        self.add_event({"event": "vote_results", "content": votes})
        self.add_event({"event": "vote_end"})
        self.votes.append(dict(enumerate(votes)))
        self.check_votes()
        for player_id in self.alive_players:
            player = self.all_players[player_id]
            if self.player_types[player_id] == "baseline":
                res = send_message(
                    render.game_intro(player),
                    render.game_report(self, player),
                    render.notetaking_command(),
                )
                self.add_event(
                    {
                        "event": "notetaking",
                        "content": {"player": player.id, "context": res},
                    }
                )
                player.notes = res
            elif self.player_types[player_id] == "reflex":
                res = player.act(self.event_book, ["vote"])
                self.add_event(
                    {
                        "event": "action",
                        "content": {"player": player.id, "context": res},
                    }
                )
                action, target, reason = res
                if action == "vote":
                    self.vote_out(target)
                elif action == "kill":
                    self.kill(target)
        return

    def run_night(self):
        self.healed_guy = None
        self.werewolves_talks = []
        medics, seers, werewolves = (
            self.get_alive_medics(),
            self.get_alive_seers(),
            self.get_alive_werewolves(),
        )
        for medic in medics:
            medic.healing(self)
        for seer in seers:
            seer.inquiry(self)
        for werewolf in werewolves:
            if werewolf.rank == "leader":
                werewolf.killing(self)
            else:
                werewolf.advicing(self)
        return

    def run_game(self):
        while True:
            self.add_event({"event": "cycle", "content": "day"})
            self.run_day()
            if self.is_game_end():
                self.save_game()
                return
            self.add_event({"event": "cycle", "content": "night"})
            self.run_night()
            if self.is_game_end():
                self.save_game()
                return

    def save_game(self):
        json.dump(self.log, open(f"records/game_{self.id}_log.json", "w"), indent=4)
        