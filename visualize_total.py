from visualize import visualize_one_pickle
from visualize_graph import visualize_game
import os
import json
if __name__ == "__main__":
    visualize_one_pickle(r'E:\wolfGPT\MafiaGPT_RL\data_v7\game_0_data.pkl', 'mid_0.json')
    visualize_one_pickle(r'E:\wolfGPT\MafiaGPT_RL\data_v7\game_2_data.pkl', 'mid_2.json')
    visualize_one_pickle(r'E:\wolfGPT\MafiaGPT_RL\data_v7\game_3_data.pkl', 'mid_3.json')
    visualize_one_pickle(r'E:\wolfGPT\MafiaGPT_RL\data_v7\game_4_data.pkl', 'mid_4.json')
    visualize_one_pickle(r'E:\wolfGPT\MafiaGPT_RL\data_v7\game_5_data.pkl', 'mid_5.json')
    visualize_one_pickle(r'E:\wolfGPT\MafiaGPT_RL\data_v7\game_6_data.pkl', 'mid_6.json')
    visualize_one_pickle(r'E:\wolfGPT\MafiaGPT_RL\data_v7\game_7_data.pkl', 'mid_7.json')
    visualize_game(json.load(open('mid_0.json', 'r')), 'sjz_0.mp4')
    visualize_game(json.load(open('mid_1.json', 'r')), 'sjz_1.mp4')
    visualize_game(json.load(open('mid_2.json', 'r')), 'sjz_2.mp4')