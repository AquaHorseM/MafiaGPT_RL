from core.event import Event
class StateNode:
    def __init__(self, id: int, parent_id: int, state):
        self.id = id
        self.parent_id = parent_id
        self.state = state
        self.edges: list[int] = []
    
    def add_edge(self, edge_id: int):
        self.edges.append(edge_id)
    
    def __repr__(self):
        return f"Node({self.id})" if self.id != 0 else "Root Node"

class EventsEdge:
    def __init__(self, id: int, node1_id: int, node2_id: int, events):
        self.id = id
        self.start_id = node1_id
        self.end_id = node2_id
        self.events = events
    
    def __repr__(self):
        return f"Edge({self.start_id} --> {self.end_id})"

class DataTree:
    def __init__(self):
        self.nodes: list[StateNode] = []
        self.edges: list[EventsEdge] = []
        root_node = StateNode(0, -1, None, None)
        self.nodes.append(root_node)
        self.cur_id = 0
    
    def _add_node(self, parent_id, state):
        node_id = len(self.nodes)
        new_node = StateNode(node_id, parent_id, state)
        self.nodes.append(new_node)
        return node_id
    
    def _add_edge(self, node1_id: int, node2_id: int, events: list[Event]|Event):
        if isinstance(events, Event):
            events = [events]
        edge_id = len(self.edges)
        edge = EventsEdge(edge_id, node1_id, node2_id, events)
        self.nodes[node1_id].add_edge(edge_id)
        self.nodes[node2_id].add_edge(edge_id)
        self.edges.append(edge)
        return edge_id
        
    def add_edge_and_node(self, events, state):
        start_id = self.cur_id
        node_id = self._add_node(start_id, state)
        self._add_edge(start_id, node_id, events)
        self.cur_id = node_id
        
    def get_events(self, node_id: int):
        edges: list[int] = []
        events: list[Event] = []
        cur_node = node_id
        while cur_node != 0:
            parent_node = self.nodes[cur_node].parent_id
            edge_id = [e for e in self.nodes[parent_node].edges if self.edges[e].end_id == cur_node][0]
            edges.append(edge_id)
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
    
    def backtrace(self, node_id: int):
        self.cur_id = node_id
        return {
            "state": self.nodes[node_id].state,
            "events": self.get_events(node_id)
        }
        
    def __repr__(self):
        return f"Tree(Nodes: {self.nodes}, Edges: {self.edges})"