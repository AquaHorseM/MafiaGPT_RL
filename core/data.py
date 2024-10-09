import random
from core.event import Event
from typing import List, Union, Dict
import numpy as np
from copy import deepcopy

class StateNode:
    def __init__(self, id: int, parent_id: int, state, end_node: bool = False):
        self.id = id
        self.parent_id = parent_id
        self.state: dict = deepcopy(state)
        self.edges: list[int] = []
        self.end_node = end_node
        self.connect_to_end = end_node
    
    def add_edge(self, edge_id: int):
        if self.end_node:
            raise ValueError("Error: Adding edge to an end node!")
        self.edges.append(edge_id)
        
    def print_state(self, show_hstate_detail = False):
        for key, value in self.state.items():
            if key != "hstate" or show_hstate_detail:
                print(f"{key}: {value}")
                
    def is_alive(self, player_id):
        return player_id in self.state["global_info"]["alive_players"]
    
    def __repr__(self):
        return f"Node({self.id})" if self.id != 0 else "Root Node"

class EventsEdge:
    def __init__(self, id: int, node1_id: int, node2_id: int, events: List[Event], actions: List[Dict], drafts: List[Dict]):
        self.id = id
        self.start_id = node1_id
        self.end_id = node2_id
        self.events = deepcopy(events)
        self.actions = deepcopy(actions)
        self.drafts = deepcopy(drafts)
    
    def __repr__(self):
        return f"Edge({self.start_id} --> {self.end_id})"

class DataTree:
    def __init__(self, init_state = None):
        self.nodes: list[StateNode] = []
        self.edges: list[EventsEdge] = []
        root_node = StateNode(0, -1, init_state)
        self.nodes.append(root_node)
        self.cur_id = 0
    
    def _add_node(self, parent_id, state, is_game_end = False):
        node_id = len(self.nodes)
        new_node = StateNode(node_id, parent_id, state, is_game_end)
        self.nodes.append(new_node)
        if is_game_end:
            cur_node = parent_id
            while cur_node != 0:
                self.nodes[cur_node].connect_to_end = True
                cur_node = self.nodes[cur_node].parent_id
        return node_id
    
    def _add_edge(self, node1_id: int, node2_id: int, events: Union[List[Event], Event], actions: List[Dict], drafts: List[Dict]):
        if isinstance(events, Event):
            events = [events]
        edge_id = len(self.edges)
        edge = EventsEdge(edge_id, node1_id, node2_id, events, actions, drafts)
        self.nodes[node1_id].add_edge(edge_id)
        self.edges.append(edge)
        return edge_id
        
    def add_edge_and_node(self, events, actions, drafts, state, is_game_end = False):
        start_id = self.cur_id
        node_id = self._add_node(start_id, state, is_game_end)
        print(f"debug: adding edge from {self.cur_id} to {node_id}")
        self._add_edge(start_id, node_id, events, actions, drafts)
        self.cur_id = node_id
        
    def get_events_before(self, node_id: int):
        edges: list[int] = []
        events: list[Event] = []
        cur_node = node_id
        while cur_node != 0:
            parent_node = self.nodes[cur_node].parent_id
            edge_id = [e for e in self.nodes[parent_node].edges if self.edges[e].end_id == cur_node][0]
            edges.append(edge_id)
            cur_node = parent_node
        for edge_id in reversed(edges):
            events.extend(self.edges[edge_id].events)
        return events
    
    def get_events_after(self, node_id: int):
        edges: list[int] = []
        events: list[Event] = []
        cur_node = node_id
        while len(self.nodes[cur_node].edges) != 0:
            avail_edges = [e for e in self.nodes[cur_node].edges if self.nodes[self.edges[e].end_id].connect_to_end]
            if len(avail_edges) == 0:
                return []
            edge_id = random.choice(avail_edges)
            events.extend(self.edges[edge_id].events)
            cur_node = self.edges[edge_id].end_id
        return events
    
    def get_item(self, node_id: int):
        outcomes = []
        node = self.nodes[node_id]
        for edge_id in node.edges:
            edge = self.edges[edge_id]
            outcomes.append((edge.events, self.nodes[edge.end_id].state))
        return (node, outcomes)
    
    def get_backtrace_id(self, backsteps: int, node_id = None):
        if node_id is None:
            node_id = self.cur_id
        for i in range(backsteps):
            if node_id == 0:
                break
            node_id = self.nodes[node_id].parent_id
        return node_id
    
    def get_game_status(self, node_id: int):
        return self.nodes[node_id].state["global_info"]["game_status"]
    
    def backtrace(self, node_id: int):
        # print("***************************")
        # print(f"data debug: cur id is {self.cur_id}, target id is {node_id}")
        # for i in range(1, len(self.nodes)):
        #     print(f"game status of {i} is {self.get_game_status(i)}")
        # print("***************************")
        self.cur_id = node_id
        return {
            "state": self.nodes[node_id].state,
            "events": self.get_events_before(node_id)
        }
        
    def go_to_latest(self):
        node_id = len(self.nodes) - 1
        self.cur_id = node_id
        return {
            "state": self.nodes[node_id].state,
            "events": self.get_events_before(node_id)
        }
        
    def filter_node(self, node_id: int, player_id: int, filter_events = False):
        return self.nodes[node_id].is_alive(player_id) and (not filter_events or any(self.filter_edge(e, player_id) for e in self.nodes[node_id].edges))
        
    def filter_edge(self, edge_id: int, player_id: int):
        return True if self.edges[edge_id].actions[player_id] is not None else False
        
    def parse(self, node_id: int, player_id: int = None, filter_action = False):
        #RETURN state, events, [(action1, events1, state1), ...]
        return {
            "state": self.nodes[node_id].state if node_id != 0 else None,
            "prev_events": self.get_events_before(node_id),
            "trajs": [
                {
                    "actions": self.edges[e].actions, 
                    "drafts": self.edges[e].drafts,
                    "events": self.edges[e].events,
                    "outcome": self.nodes[self.edges[e].end_id].state,
                    "after_events": self.get_events_after(self.edges[e].end_id),
                    "connect_to_end": self.nodes[self.edges[e].end_id].connect_to_end
                } for e in self.nodes[node_id].edges if not filter_action or (player_id and self.filter_action(e, player_id))
            ]
        }
        
    def sample_single(self, player_id = None, filter_events = False, sampling_method = "uniform"): #sampling method from 'uniform', 'log' and 'sqrt'
        node_ids = [node_id for node_id in range(len(self.nodes)) if self.filter_node(node_id, player_id, filter_events)]
        if len(node_ids) == 0:
            print(f"No action done by player {player_id} in the data.")
            return None
        if sampling_method == "sqrt":
            weights = [np.sqrt(len(self.nodes[node_id].edges)) for node_id in node_ids]
        elif sampling_method == "log":
            weights = [np.log2(len(self.nodes[node_id].edges)) for node_id in node_ids]
        elif sampling_method == "uniform":
            weights = [1] * len(self.nodes)
        else:
            raise ValueError(f"Sampling Method {sampling_method} not recognized")
        return random.choices(node_ids, weights=weights)[0]

    def sample(self, player_id = None, filter_events = False, sampling_method = "sqrt", sample_num = 1):
        node_ids = [node_id for node_id in range(len(self.nodes)) if self.filter_node(node_id, player_id, filter_events)]
        if len(node_ids) == 0:
            print(f"No action done by player {player_id} in the data.")
            return []
        elif len(node_ids) <= sample_num:
            if len(node_ids) < sample_num:
                print(f"Warning: Only {len(node_ids)} valid samples in data, but {sample_num} is required.")
            return node_ids
        samples = []
        while len(samples) < sample_num:
            node_id = self.sample_single(player_id, filter_events, sampling_method)
            if node_id not in samples:
                samples.append(node_id)
        return samples
    
    def get_next_drafts(self, node_id: int):
        if len(self.nodes[node_id].edges) != 1:
            return None
        print(f"node id: {node_id}, edge id: {self.nodes[node_id].edges[0]}")
        return self.edges[self.nodes[node_id].edges[0]].drafts
    
    def show_info(self, interactive = False):
        for i in range(len(self.nodes)):
            print(f"Node {i}'s parent: {self.nodes[i].parent_id}")
        if interactive:
            while True:
                command = input("Please input your command\n")
                if command == "view":
                    id = int(eval(input("Please input the node id you want to view; -1 for backward.\n")))
                    if id == -1:
                        continue
                    if id < 0 or id >= len(self.nodes):
                        print("Invalid id! Back to command input session.")
                        continue
                    print("*****************************")
                    print(f"State of node {id} is: ")
                    print("&&&&&&&&&&&&&&&&&&&&&&&&&")
                    self.nodes[id].print_state(show_hstate_detail = False)
                    print("&&&&&&&&&&&&&&&&&&&&&&&&&")
                    print("*****************************")
                elif command == "events":
                    t = input("Do you want to see events of an edge or a node? Enter 'edge' or 'node' correspondingly.\n")
                    if t not in ["edge", "node"]:
                        print("Unrecognized! Back to command input session.")
                    else:
                        id = int(eval(input("Please input the node id you want to view; -1 for backward.\n")))
                        if id == -1:
                            continue
                        if id < 0 or (t == "node" and id >= len(self.nodes)) or (t == "edge" and id >= len(self.edges)):
                            print("Invalid id! Back to command input session.")
                            continue
                        if t == "node":
                            print("*****************************")
                            print(f"Events of node {id} are: ")
                            print("&&&&&&&&&&&&&&&&&&&&&&&&&")
                            print(self.get_events_before(id))
                            print("&&&&&&&&&&&&&&&&&&&&&&&&&")
                            print("*****************************")
                        else:
                            print("*****************************")
                            print(f"Events of edge {id} are: ")
                            print("&&&&&&&&&&&&&&&&&&&&&&&&&")
                            print(self.edges[id].events)
                            print("&&&&&&&&&&&&&&&&&&&&&&&&&")
                            print("*****************************")
                else:
                    break
                        
    def __repr__(self):
        return f"Tree(Nodes: {self.nodes}, Edges: {self.edges})"
    