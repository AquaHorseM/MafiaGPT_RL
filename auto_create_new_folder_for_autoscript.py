import os
from argparse import ArgumentParser
import shutil
import json

def copy_directory_with_prompt(source_dir, destination_dir):
    try:
        # Check if the destination directory already exists
        if os.path.exists(destination_dir):
            user_input = input(f"The directory '{destination_dir}' already exists. Do you want to delete it and copy the new one? (yes/no): ")
            if user_input.lower() == 'yes':
                # Remove the existing destination directory
                shutil.rmtree(destination_dir)
                print(f"Deleted existing directory: {destination_dir}")
            else:
                print("Aborting the copy operation.")
                return

        # Copy the directory
        shutil.copytree(source_dir, destination_dir)
        print(f"Successfully copied {source_dir} to {destination_dir}")

    except Exception as e:
        print(f"Error occurred: {e}")

def main(args):

    folder_name = args.new_folder_name
    os.makedirs(folder_name, exist_ok=False)
    org_dir_name_without_path = os.path.basename(args.org_notes_dir)
    # copy the org_notes_dir into new_folder_name/notes/org_notes_dir.
    copy_directory_with_prompt(args.org_notes_dir, os.path.join(folder_name, 'notes', org_dir_name_without_path))
    
    os.makedirs(os.path.join(folder_name, 'data'), exist_ok=True)
    os.makedirs(os.path.join(folder_name, 'configs'), exist_ok=True)
    os.makedirs(os.path.join(folder_name, 'prompt_logging'), exist_ok=True)
    current_config_dict = {
        "reflex_after_sim": False,
        "log_hstate_for_debug": False,
        "openai_client_path": "openai_config.yaml",
        "data_folder": os.path.join(folder_name, 'data', "data_v0"),
        "input_txt_path": os.path.join(folder_name, 'prompt_logging', "message_input_history_backup_v0.txt"),
        "output_txt_path": os.path.join(folder_name, 'prompt_logging', "message_output_history_backup_v0.txt"),
        "players": [
            {
                "role": "werewolf",
                "player_type": "reflex",
                "reflex_note_belief_path": os.path.join(folder_name, 'notes', org_dir_name_without_path,"werewolf/werewolf_reflex_note_belief.txt"),
                "reflex_note_policy_path": os.path.join(folder_name, 'notes', org_dir_name_without_path,"werewolf/werewolf_reflex_note_policy.txt"),
                "common_prompt_dir_path": "core/players/reflex/prompts/common",
                "prompt_dir_path": "core/players/reflex/prompts/werewolf",
                "proposal_num": 2,
                "sample_num": 10,
                "sample_type": "heuristic",
                "player_tag": "v0"
            },
            {
                "role": "werewolf",
                "player_type": "reflex",
                "reflex_note_belief_path": os.path.join(folder_name, 'notes', org_dir_name_without_path,"werewolf/werewolf_reflex_note_belief.txt"),
                "reflex_note_policy_path": os.path.join(folder_name, 'notes', org_dir_name_without_path,"werewolf/werewolf_reflex_note_policy.txt"),
                "common_prompt_dir_path": "core/players/reflex/prompts/common",
                "prompt_dir_path": "core/players/reflex/prompts/werewolf",
                "proposal_num": 2,
                "sample_num": 10,
                "sample_type": "heuristic",
                "player_tag": "v0"
            },
            {
                "role": "villager",
                "player_type": "reflex",
                "reflex_note_belief_path": os.path.join(folder_name, 'notes', org_dir_name_without_path, "villager/villager_reflex_note_belief.txt"),
                "reflex_note_policy_path": os.path.join(folder_name, 'notes', org_dir_name_without_path, "villager/villager_reflex_note_policy.txt"),
                "common_prompt_dir_path": "core/players/reflex/prompts/common",
                "prompt_dir_path": "core/players/reflex/prompts/villager",
                "proposal_num": 2,
                "sample_num": 10,
                "sample_type": "heuristic",
                "player_tag": "v0"
            },
            {
                "role": "villager",
                "player_type": "reflex",
                "reflex_note_belief_path": os.path.join(folder_name, 'notes', org_dir_name_without_path, "villager/villager_reflex_note_belief.txt"),
                "reflex_note_policy_path": os.path.join(folder_name, 'notes', org_dir_name_without_path, "villager/villager_reflex_note_policy.txt"),
                "common_prompt_dir_path": "core/players/reflex/prompts/common",
                "prompt_dir_path": "core/players/reflex/prompts/villager",
                "proposal_num": 2,
                "sample_num": 10,
                "sample_type": "heuristic",
                "player_tag": "v0"
            },
            {
                "role": "villager",
                "player_type": "reflex",
                "reflex_note_belief_path": os.path.join(folder_name, 'notes', org_dir_name_without_path, "villager/villager_reflex_note_belief.txt"),
                "reflex_note_policy_path": os.path.join(folder_name, 'notes', org_dir_name_without_path, "villager/villager_reflex_note_policy.txt"),
                "common_prompt_dir_path": "core/players/reflex/prompts/common",
                "prompt_dir_path": "core/players/reflex/prompts/villager",
                "proposal_num": 2,
                "sample_num": 10,
                "sample_type": "heuristic",
                "player_tag": "v0"
            },
            {
                "role": "medic",
                "player_type": "reflex",
                "reflex_note_belief_path": os.path.join(folder_name, 'notes', org_dir_name_without_path, "medic/medic_reflex_note_belief.txt"),
                "reflex_note_policy_path": os.path.join(folder_name, 'notes', org_dir_name_without_path, "medic/medic_reflex_note_policy.txt"),
                "common_prompt_dir_path": "core/players/reflex/prompts/common",
                "prompt_dir_path": "core/players/reflex/prompts/medic",
                "proposal_num": 2,
                "sample_num": 10,
                "sample_type": "heuristic",
                "player_tag": "v0"
            },
            {
                "role": "seer",
                "player_type": "reflex",
                "reflex_note_belief_path": os.path.join(folder_name, 'notes', org_dir_name_without_path, "seer/seer_reflex_note_belief.txt"),
                "reflex_note_policy_path": os.path.join(folder_name, 'notes', org_dir_name_without_path, "seer/seer_reflex_note_policy.txt"),
                "common_prompt_dir_path": "core/players/reflex/prompts/common",
                "prompt_dir_path": "core/players/reflex/prompts/seer",
                "proposal_num": 2,
                "sample_num": 10,
                "sample_type": "heuristic",
                "player_tag": "v0"
            }
        ],
        "extra_sim_nodes": 5
    }
    json.dump(current_config_dict, open(os.path.join(folder_name, 'configs', "game_config_v00.json"), 'w'), indent=4)
    
    
    

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('--new_folder_name', type=str, default = './shijz_test_15')
    parser.add_argument('--org_notes_dir', type=str, default = './core/notes_fixed_version/notes_v0')
    args = parser.parse_args()
    main(args)
