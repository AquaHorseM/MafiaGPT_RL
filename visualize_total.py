import os
from visualize import visualize_one_pickle

def visualize_all_pickles(source_folder, target_folder):
    # Walk through all directories and files in source folder
    for dirpath, dirnames, filenames in os.walk(source_folder):
        for filename in filenames:
            if filename.endswith('.pkl'):
                try:
                    # Construct the full path to the source .pkl file
                    full_source_path = os.path.join(dirpath, filename)
                    # Replace the source folder path with the target folder path
                    relative_path = os.path.relpath(full_source_path, source_folder)
                    relative_path = relative_path.replace('.pkl', '.json')
                    full_target_path = os.path.join(target_folder, relative_path)
                    # Ensure the target directory exists
                    os.makedirs(os.path.dirname(full_target_path), exist_ok=True)
                    # Visualize the pickle file
                    visualize_one_pickle(full_source_path, full_target_path)
                except Exception as e:
                    pass

from argparse import ArgumentParser

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('--source_folder', type=str, default='./cocs_ablation_1')
    parser.add_argument('--target_folder', type=str, default='./cocs_ablation_1_visualized')
    args = parser.parse_args()

    visualize_all_pickles(args.source_folder, args.target_folder)