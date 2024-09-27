import random
from core.event import Event
from typing import List, Union
import numpy as np
from copy import deepcopy

class StateNode:
    def __init__(self, id: int, parent_id: int, state):
        self.id = id
        self.parent_id = parent_id
        self.state = deepcopy(state)
        self.edges: list[int] = []
    
    def add_edge(self, edge_id: int):
        self.edges.append(edge_id)
    
    def __repr__(self):
        return f"Node({self.id})" if self.id != 0 else "Root Node"

class EventsEdge:
    def __init__(self, id: int, node1_id: int, node2_id: int, events, actions: List[int]):
        self.id = id
        self.start_id = node1_id
        self.end_id = node2_id
        self.events = events
        self.actions = actions
    
    def __repr__(self):
        return f"Edge({self.start_id} --> {self.end_id})"

class DataTree:
    def __init__(self):
        self.nodes: list[StateNode] = []
        self.edges: list[EventsEdge] = []
        root_node = StateNode(0, -1, None)
        self.nodes.append(root_node)
        self.cur_id = 0
    
    def _add_node(self, parent_id, state):
        node_id = len(self.nodes)
        new_node = StateNode(node_id, parent_id, state)
        self.nodes.append(new_node)
        return node_id
    
    def _add_edge(self, node1_id: int, node2_id: int, events: Union[List[Event], Event], actions: List[int]):
        if isinstance(events, Event):
            events = [events]
        edge_id = len(self.edges)
        edge = EventsEdge(edge_id, node1_id, node2_id, events, actions)
        self.nodes[node1_id].add_edge(edge_id)
        self.edges.append(edge)
        return edge_id
        
    def add_edge_and_node(self, events, actions, state):
        start_id = self.cur_id
        node_id = self._add_node(start_id, state)
        self._add_edge(start_id, node_id, events, actions)
        self.cur_id = node_id
        
    def get_events(self, node_id: int):
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
            "events": self.get_events(node_id)
        }
        
    def filter_node(self, node_id: int, player_id: int):
        return any(self.filter_edge(e, player_id) for e in self.nodes[node_id].edges)
        
    def filter_edge(self, edge_id: int, player_id: int):
        return True if self.edges[edge_id].actions[player_id] != 0 else False
        
    def parse(self, node_id: int, player_id: int = None, filter_action = False):
        #RETURN state, events, [(action1, events1, state1), ...]
        return {
            "state": self.nodes[node_id].state,
            "prev_events": self.get_events(node_id),
            "outcomes": [
                (self.edges[e].actions, self.edges[e].events, self.nodes[self.edges[e].end_id].state) for e in self.nodes[node_id].edges if not filter_action or (player_id and self.filter_action(e, player_id))
            ]
        }
        
    def sample_single(self, player_id = None, filter_node = False, sampling_method = "sqrt"): #sampling method from 'uniform', 'log' and 'sqrt'
        #TODO find a better sampling method
        if filter_node:
            node_ids = [node_id for node_id in range(len(self.nodes)) if self.filter_node(node_id, player_id)]
            if len(node_ids) == 0:
                print(f"No action done by player {player_id} in the data.")
                return None
        else:
            node_ids = self.nodes
        if sampling_method == "sqrt":
            weights = [np.sqrt(len(self.nodes[node_id].edges)) for node_id in node_ids]
        elif sampling_method == "log":
            weights = [np.log2(len(self.nodes[node_id].edges)) for node_id in node_ids]
        elif sampling_method == "uniform":
            weights = [1] * len(self.nodes)
        else:
            raise ValueError(f"Sampling Method {sampling_method} not recognized")
        return random.choices(node_ids, weights=weights)[0]

    def sample(self, player_id = None, filter_node = False, sampling_method = "sqrt", sample_num = 1):
        if filter_node:
            node_ids = [node_id for node_id in range(len(self.nodes)) if self.filter_node(node_id, player_id)]
            if len(node_ids) == 0:
                print(f"No action done by player {player_id} in the data.")
                return []
            elif len(node_ids) <= sample_num:
                if len(node_ids < sample_num):
                    print(f"Warning: Only {len(node_ids)} valid samples in data, but {sample_num} is required.")
                return node_ids
        samples = []
        while len(samples) < sample_num:
            node_id = self.sample_single(player_id, filter_node, sampling_method)
            if node_id not in samples:
                samples.append(node_id)
        return samples
    
    def show_info(self, interactive = False):
        for i in range(len(self.nodes)):
            print(f"Node {i}'s parent: {self.nodes[i].parent_id}")
        if interactive:
            while True:
                command = input("Please input your command")
                if command == "view":
                    id = int(eval(input("Please input the node id you want to view; -1 for backward.")))
                    if id == -1:
                        continue
                    if id < 0 or id >= len(self.nodes):
                        print("Invalid id! Back to command input session.")
                        continue
                    print("*****************************")
                    print(f"State of node {id} is: ")
                    print("&&&&&&&&&&&&&&&&&&&&&&&&&")
                    print(self.nodes[id].state)
                    print("&&&&&&&&&&&&&&&&&&&&&&&&&")
                    print("*****************************")
                elif command == "events":
                    t = input("Do you want to see events of an edge or a node? Enter 'edge' or 'node' correspondingly.")
                    if t not in ["edge", "node"]:
                        print("Unrecognized! Back to command input session.")
                    else:
                        id = int(eval(input("Please input the node id you want to view; -1 for backward.")))
                        if id == -1:
                            continue
                        if id < 0 or (t == "node" and id >= len(self.nodes)) or (t == "edge" and id >= len(self.edges)):
                            print("Invalid id! Back to command input session.")
                            continue
                        if t == "node":
                            print("*****************************")
                            print(f"Events of node {id} are: ")
                            print("&&&&&&&&&&&&&&&&&&&&&&&&&")
                            print(self.get_events(id))
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
    
