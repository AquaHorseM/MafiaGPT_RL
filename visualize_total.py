from visualize import visualize_one_pickle
from visualize_graph import visualize_game
import os
import json
if __name__ == "__main__":
    folder_path = "transport/data_v6"
    for file_path in os.listdir(folder_path):
        if file_path.endswith(".pkl"):
            visualize_one_pickle(file_path, file_path.replace(".pkl", "_log.json"))