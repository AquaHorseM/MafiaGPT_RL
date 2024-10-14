# def visualize_game(game_event_list):
#     import matplotlib.pyplot as plt
#     import matplotlib.animation as animation
#     from matplotlib.offsetbox import OffsetImage, AnnotationBbox
#     import networkx as nx
#     import re

#     # Define player roles and positions
#     player_roles = {}
#     player_positions = {}
#     num_players = 0

#     # Process the game event list to extract roles and player numbers
#     for event in game_event_list:
#         if "is set as" in event:
#             match = re.search(r"Player (\d+) is set as (\w+)", event)
#             if match:
#                 player_num = int(match.group(1))
#                 role = match.group(2)
#                 player_roles[player_num] = role
#                 num_players = max(num_players, player_num + 1)

#     # Assign positions for players in a circle
#     import numpy as np

#     angles = np.linspace(0, 2 * np.pi, num_players, endpoint=False)
#     positions = {i: (np.cos(angle), np.sin(angle)) for i, angle in enumerate(angles)}

#     # Initialize the plot
#     fig, ax = plt.subplots(figsize=(8, 8))
#     plt.axis('off')

#     # Create a NetworkX graph
#     G = nx.Graph()
#     G.add_nodes_from(range(num_players))

#     # Function to update the frame for animation
#     def update(frame):
#         ax.clear()
#         plt.axis('off')
#         current_event = game_event_list[frame]
#         ax.set_title(current_event, fontsize=12)

#         # Highlight players based on events
#         node_colors = []
#         for i in range(num_players):
#             if f"Player {i} died" in "\n".join(game_event_list[:frame + 1]):
#                 node_colors.append('black')
#             else:
#                 node_colors.append('skyblue')

#         nx.draw_networkx_nodes(G, positions, node_color=node_colors, ax=ax, node_size=500)

#         labels = {}
#         for i in range(num_players):
#             role = player_roles.get(i, 'Unknown')
#             labels[i] = f"Player {i}\n({role})"
#         nx.draw_networkx_labels(G, positions, labels=labels, ax=ax, font_size=8)

#     ani = animation.FuncAnimation(fig, update, frames=len(game_event_list), interval=1000, repeat=False)
#     plt.show()
# def visualize_game(game_event_list):
#     import matplotlib.pyplot as plt
#     import matplotlib.animation as animation
#     import networkx as nx
#     import re

#     # Define player roles and positions
#     player_roles = {}
#     num_players = 0

#     # Process the game event list to extract roles and player numbers
#     for event in game_event_list:
#         if "is set as" in event:
#             match = re.search(r"Player (\d+) is set as (\w+)", event)
#             if match:
#                 player_num = int(match.group(1))
#                 role = match.group(2)
#                 player_roles[player_num] = role
#                 num_players = max(num_players, player_num + 1)

#     # Assign positions for players in a circle
#     import numpy as np

#     angles = np.linspace(0, 2 * np.pi, num_players, endpoint=False)
#     positions = {i: (np.cos(angle), np.sin(angle)) for i, angle in enumerate(angles)}

#     # Initialize the plot
#     fig, ax = plt.subplots(figsize=(8, 8))
#     plt.axis('off')

#     # Create a NetworkX graph
#     G = nx.DiGraph()
#     G.add_nodes_from(range(num_players))

#     # Keep track of alive and dead players
#     alive_players = set(range(num_players))

#     # Initialize phase and edges_in_phase
#     current_phase = None  # "Night" or "Day"
#     edges_in_phase = []  # List of tuples: (source, target, edge_color)

#     # Function to update the frame for animation
#     def update(frame):
#         nonlocal current_phase, edges_in_phase
#         ax.clear()
#         plt.axis('off')
#         current_event = game_event_list[frame]
#         ax.set_title(current_event, fontsize=10)

#         # Check for phase change
#         if current_event.strip() == "Night starts.":
#             if current_phase != "Night":
#                 current_phase = "Night"
#                 edges_in_phase = []
#         elif current_event.strip() == "Day starts.":
#             if current_phase != "Day":
#                 current_phase = "Day"
#                 edges_in_phase = []
#         elif current_event.strip() == "Game starts.":
#             current_phase = "Game"
#             edges_in_phase = []
#         elif re.match(r"Round \d+ begins\.", current_event.strip()):
#             pass  # Optionally handle round changes
#         elif current_event.strip().startswith("Game ends."):
#             current_phase = "End"
#             edges_in_phase = []

#         # Update alive players
#         death_match = re.match(r"Player (\d+) died\.", current_event)
#         if death_match:
#             dead_player = int(death_match.group(1))
#             alive_players.discard(dead_player)

#         # Highlight players based on their alive status
#         node_colors = []
#         for i in range(num_players):
#             if i in alive_players:
#                 node_colors.append('skyblue')
#             else:
#                 node_colors.append('gray')

#         # Draw nodes
#         nx.draw_networkx_nodes(G, positions, node_color=node_colors, ax=ax, node_size=800)

#         # Draw player labels with roles
#         labels = {}
#         for i in range(num_players):
#             role = player_roles.get(i, 'Unknown')
#             labels[i] = f"P{i}\n({role[0].upper()})"  # Shorten role to first letter
#         nx.draw_networkx_labels(G, positions, labels=labels, ax=ax, font_size=8)

#         # Remove all edges before drawing new ones
#         G.remove_edges_from(list(G.edges()))

#         # Draw all edges in edges_in_phase
#         for edge in edges_in_phase:
#             source, target, edge_color = edge
#             if source in alive_players and target in alive_players:
#                 G.add_edge(source, target)
#                 nx.draw_networkx_edges(G, positions, edgelist=[(source, target)], edge_color=edge_color, ax=ax,
#                                        arrows=True, arrowstyle='-|>', arrowsize=20)

#         # Check for actions to add to edges_in_phase
#         # Night actions
#         night_action_match = re.match(r"Player (\d+) (heals|inquires about|advises targeting) player (\d+)", current_event)
#         if night_action_match:
#             source = int(night_action_match.group(1))
#             action = night_action_match.group(2)
#             target = int(night_action_match.group(3))
#             if action == 'heals':
#                 edge_color = 'green'
#             elif action == 'inquires about':
#                 edge_color = 'purple'
#             elif action == 'advises targeting':
#                 edge_color = 'red'
#             else:
#                 edge_color = 'black'
#             if source in alive_players and target in alive_players:
#                 # Add edge to edges_in_phase
#                 edges_in_phase.append((source, target, edge_color))

#         # Voting actions
#         vote_match = re.match(r"Player (\d+) votes for player (\d+)", current_event)
#         if vote_match:
#             voter = int(vote_match.group(1))
#             votee = int(vote_match.group(2))
#             if voter in alive_players and votee in alive_players:
#                 edge_color = 'orange'
#                 # Add edge to edges_in_phase
#                 edges_in_phase.append((voter, votee, edge_color))

#     ani = animation.FuncAnimation(fig, update, frames=len(game_event_list), interval=1000, repeat=False)
#     plt.savefig('game_visualization.svg')


def visualize_game(game_event_list, to_path = 'werewolf_game_2.mp4'):
    import matplotlib.pyplot as plt
    import matplotlib.animation as animation
    import networkx as nx
    import re

    # Define player roles and positions
    player_roles = {}
    num_players = 0

    # Process the game event list to extract roles and player numbers
    for event in game_event_list:
        if "is set as" in event:
            match = re.search(r"Player (\d+) is set as (\w+)", event)
            if match:
                player_num = int(match.group(1))
                role = match.group(2)
                player_roles[player_num] = role
                num_players = max(num_players, player_num + 1)

    # Assign positions for players in a circle
    import numpy as np

    angles = np.linspace(0, 2 * np.pi, num_players, endpoint=False)
    positions = {i: (np.cos(angle), np.sin(angle)) for i, angle in enumerate(angles)}

    # Initialize the plot
    fig, ax = plt.subplots(figsize=(8, 8))
    plt.axis('off')

    # Create a NetworkX graph
    G = nx.DiGraph()
    G.add_nodes_from(range(num_players))

    # Keep track of alive and dead players
    alive_players = set(range(num_players))

    # Initialize phase and edges_in_phase
    current_phase = None  # "Night" or "Day"
    edges_in_phase = []  # List of tuples: (source, target, edge_color)

    # Function to update the frame for animation
    def update(frame):
        nonlocal current_phase, edges_in_phase
        ax.clear()
        plt.axis('off')
        current_event = game_event_list[frame]
        ax.set_title(current_event, fontsize=10)

        # Check for phase change
        if current_event.strip() == "Night starts.":
            if current_phase != "Night":
                current_phase = "Night"
                edges_in_phase = []
        elif current_event.strip() == "Day starts.":
            if current_phase != "Day":
                current_phase = "Day"
                edges_in_phase = []
        elif current_event.strip() == "Game starts.":
            current_phase = "Game"
            edges_in_phase = []
        elif re.match(r"Round \d+ begins\.", current_event.strip()):
            pass  # Optionally handle round changes
        elif current_event.strip().startswith("Game ends."):
            current_phase = "End"
            edges_in_phase = []

        # Update alive players
        death_match = re.match(r"Player (\d+) died\.", current_event)
        if death_match:
            dead_player = int(death_match.group(1))
            alive_players.discard(dead_player)

        # Highlight players based on their alive status
        node_colors = []
        for i in range(num_players):
            if i in alive_players:
                node_colors.append('skyblue')
            else:
                node_colors.append('gray')

        # Draw nodes
        nx.draw_networkx_nodes(G, positions, node_color=node_colors, ax=ax, node_size=800)

        # Draw player labels with roles
        labels = {}
        for i in range(num_players):
            role = player_roles.get(i, 'Unknown')
            labels[i] = f"P{i}\n({role[0].upper()})"  # Shorten role to first letter
        nx.draw_networkx_labels(G, positions, labels=labels, ax=ax, font_size=8)

        # Remove all edges before drawing new ones
        G.remove_edges_from(list(G.edges()))

        # Draw all edges in edges_in_phase
        for edge in edges_in_phase:
            source, target, edge_color = edge
            if 1:
                G.add_edge(source, target)
                nx.draw_networkx_edges(G, positions, edgelist=[(source, target)], edge_color=edge_color, ax=ax,
                                       arrows=True, arrowstyle='-|>', arrowsize=20)

        # Check for actions to add to edges_in_phase
        # Night actions
        night_action_match = re.match(r"Player (\d+) (heals|inquires about|advises targeting) player (\d+)", current_event)
        if night_action_match:
            source = int(night_action_match.group(1))
            action = night_action_match.group(2)
            target = int(night_action_match.group(3))
            if action == 'heals':
                edge_color = 'green'
            elif action == 'inquires about':
                edge_color = 'purple'
            elif action == 'advises targeting':
                edge_color = 'red'
            else:
                edge_color = 'black'
            if source in alive_players and target in alive_players:
                # Add edge to edges_in_phase
                edges_in_phase.append((source, target, edge_color))

        # Voting actions
        vote_match = re.match(r"Player (\d+) votes for player (\d+)", current_event)
        
        if vote_match:
            
            voter = int(vote_match.group(1))
            votee = int(vote_match.group(2))
            # print(f"Vote Match! {voter} votes for {votee}")
            if voter in alive_players:
                # print(f"        valid Vote Match! {voter} votes for {votee}")
                edge_color = 'orange'
                # Add edge to edges_in_phase
                edges_in_phase.append((voter, votee, edge_color))

    # Create the animation
    ani = animation.FuncAnimation(fig, update, frames=len(game_event_list), interval=1000, repeat=False)

    # Save the animation to an MP4 file
    ani.save(to_path, writer='ffmpeg', fps=1, dpi=100)

    # Optionally, display the animation
    # plt.show()

import json
if __name__ == "__main__":
    x = json.load(open('e.json'))
    visualize_game(x)