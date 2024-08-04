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
        self, player_configs
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
            "previous_votes": [],
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
            
            if role == "werewolf":
                if player_type == "baseline":
                    self.alive_players.append(Werewolf(role="werewolf", id=i))
                elif player_type == "basereflex":
                    self.alive_players.append(WerewolfPlayer(

        
        

    def get_player(self, id):
        #debug 
        print(id, self.all_players[id])
        return self.all_players[id]

    def get_alive_werewolves(self):
        ls = list(filter(lambda player: player.type == "werewolf", self.alive_players))
        # to make sure that last werewolf will make the last decision
        ls[-1].rank = "leader"
        return ls

    def get_alive_medics(self):
        return list(filter(lambda player: player.type == "medic", self.alive_players))

    def get_alive_seers(self):
        return list(filter(lambda player: player.type == "seer", self.alive_players))

    def get_alive_villagers(self):
        return list(
            filter(lambda player: player.type == "villager", self.alive_players)
        )

    def kill(self, Player):
        if Player not in self.alive_players:
            self.logger.warning("Killing an already dead guy! Skipped!")
            return
        self.alive_players.remove(Player)
        self.dead_players.append(Player)
        self.log_submit({"event": "killed", "content": {"player": Player.id}})
        return

    def is_game_end(self):
        """
        Will check that the game is over or not.
        """
        werewolves, villagers = self.get_alive_werewolves(), self.get_alive_villagers()
        if len(werewolves) == len(villagers):
            self.log_submit({"event": "end", "winner": "Werewolves"})
            return True
        if werewolves == []:
            self.log_submit({"event": "end", "winner": "Villagers"})
            return True
        return False

    def check_votes(self):
        # [TODO] : debugging here
        votes = self.votes[-1]
        if max(votes) > 1:
            votes_sorted = dict(sorted(votes.items(), key=lambda x: x[1]))
            self.kill(self.get_player(list(votes_sorted.keys())[-1]))
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
            self.log_submit(
                {"event": "speech", "content": {"player": Player.id, "context": res}}
            )
        votes = [0] * 7
        self.log_submit({"event": "vote_start"})
        for Player in self.alive_players:
            target_voted, reason = Player.vote(self)
            if target_voted:
                self.log_submit(
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
        self.log_submit({"event": "vote_results", "content": votes})
        self.log_submit({"event": "vote_end"})
        self.votes.append(dict(enumerate(votes)))
        self.check_votes()
        for Player in self.alive_players:
            res = send_message(
                render.game_intro(Player),
                render.game_report(self, Player),
                render.notetaking_command(),
            )
            self.log_submit(
                {
                    "event": "notetaking",
                    "content": {"player": Player.id, "context": res},
                }
            )
            Player.notes = res
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
            self.log_submit({"event": "cycle", "content": "day"})
            self.run_day()
            if self.is_game_end():
                self.save_game()
                return
            self.log_submit({"event": "cycle", "content": "night"})
            self.run_night()
            if self.is_game_end():
                self.save_game()
                return

    def save_game(self):
        json.dump(self.log, open(f"records/game_{self.id}_log.json", "w"), indent=4)

    def add_player(self, player_num, role, player_type):
        
        
        for i, player in enumerate(shuffled_roles):
            if player in simple_villagers_roles:
                self.alive_players.append(Villager(role=player, id=i))
                self.alive_players[-1].init_game(init_global_info, init_villager_private_info)
            elif player in werewolves_roles:
                self.alive_players.append(Werewolf(role=player, id=i))
                self.alive_players[-1].init_game(init_global_info, init_werewolf_private_info)
            elif player in medics_roles:
                self.alive_players.append(Medic(role=player, id=i))
                self.alive_players[-1].init_game(init_global_info, init_medic_private_info)
            elif player in seers_roles:
                self.alive_players.append(Seer(role=player, id=i))
                self.alive_players[-1].init_game(init_global_info, init_seer_private_info)
            event = Event("set_role", {"player": i, "role": player})
            self.event_book.add_event(event)
            self.log_submit(event)
        werewolves = self.get_alive_werewolves()
        for werewolf in werewolves:
            werewolf.special_actions_log.append(
                f"you are werewolf and this is your team (they are all werewolf) : {werewolves}"
            )
        self.all_players = self.alive_players