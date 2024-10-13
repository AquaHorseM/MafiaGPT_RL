import os
from argparse import ArgumentParser
import shutil
import json
import subprocess


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

def obtain_config_dict(to_data_folder, input_txt_path, output_txt_path,
                       villager_notes_folder, seer_notes_folder, medic_notes_folder,
                       werewolf_notes_folder,proposal_num = 3, sample_num = 10, sample_type = "heuristic", extra_sim_nodes = 5):
    
    current_config_dict = {
        "reflex_after_sim": False,
        "log_hstate_for_debug": False,
        "openai_client_path": "openai_config.yaml",
        "data_folder": to_data_folder,
        "input_txt_path": input_txt_path,
        "output_txt_path": output_txt_path,
        "players": [
            {
                "role": "werewolf",
                "player_type": "reflex",
                "reflex_note_belief_path": os.path.join(werewolf_notes_folder,"werewolf_reflex_note_belief.txt"),
                "reflex_note_policy_path": os.path.join(werewolf_notes_folder,"werewolf_reflex_note_policy.txt"),
                "common_prompt_dir_path": "core/players/prompts/common",
                "prompt_dir_path": "core/players/prompts/werewolf",
                "proposal_num": proposal_num,
                "sample_num": sample_num,
                "sample_type": sample_type
            },
            {
                "role": "werewolf",
                "player_type": "reflex",
                "reflex_note_belief_path": os.path.join(werewolf_notes_folder,"werewolf_reflex_note_belief.txt"),
                "reflex_note_policy_path": os.path.join(werewolf_notes_folder,"werewolf_reflex_note_policy.txt"),
                "common_prompt_dir_path": "core/players/prompts/common",
                "prompt_dir_path": "core/players/prompts/werewolf",
                "proposal_num": proposal_num,
                "sample_num": sample_num,
                "sample_type": sample_type
            },
            {
                "role": "villager",
                "player_type": "reflex",
                "reflex_note_belief_path": os.path.join(villager_notes_folder, "villager_reflex_note_belief.txt"),
                "reflex_note_policy_path": os.path.join(villager_notes_folder, "villager_reflex_note_policy.txt"),
                "common_prompt_dir_path": "core/players/prompts/common",
                "prompt_dir_path": "core/players/prompts/villager",
                "proposal_num": proposal_num,
                "sample_num": sample_num,
                "sample_type": sample_type
            },
            {
                "role": "villager",
                "player_type": "reflex",
                "reflex_note_belief_path": os.path.join(villager_notes_folder, "villager_reflex_note_belief.txt"),
                "reflex_note_policy_path": os.path.join(villager_notes_folder, "villager_reflex_note_policy.txt"),
                "common_prompt_dir_path": "core/players/prompts/common",
                "prompt_dir_path": "core/players/prompts/villager",
                "proposal_num": proposal_num,
                "sample_num": sample_num,
                "sample_type": sample_type
            },
            {
                "role": "villager",
                "player_type": "reflex",
                "reflex_note_belief_path": os.path.join(villager_notes_folder, "villager_reflex_note_belief.txt"),
                "reflex_note_policy_path": os.path.join(villager_notes_folder, "villager_reflex_note_policy.txt"),
                "common_prompt_dir_path": "core/players/prompts/common",
                "prompt_dir_path": "core/players/prompts/villager",
                "proposal_num": proposal_num,
                "sample_num": sample_num,
                "sample_type": sample_type
            },
            {
                "role": "medic",
                "player_type": "reflex",
                "reflex_note_belief_path": os.path.join(medic_notes_folder, "medic_reflex_note_belief.txt"),
                "reflex_note_policy_path": os.path.join(medic_notes_folder, "medic_reflex_note_policy.txt"),
                "common_prompt_dir_path": "core/players/prompts/common",
                "prompt_dir_path": "core/players/prompts/medic",
                "proposal_num": proposal_num,
                "sample_num": sample_num,
                "sample_type": sample_type
            },
            {
                "role": "seer",
                "player_type": "reflex",
                "reflex_note_belief_path": os.path.join(seer_notes_folder, "seer_reflex_note_belief.txt"),
                "reflex_note_policy_path": os.path.join(seer_notes_folder, "seer_reflex_note_policy.txt"),
                "common_prompt_dir_path": "core/players/prompts/common",
                "prompt_dir_path": "core/players/prompts/seer",
                "proposal_num": proposal_num,
                "sample_num": sample_num,
                "sample_type": sample_type
            }
        ],
        "extra_sim_nodes": extra_sim_nodes
    }
    
    return current_config_dict



def create_folder_for_one_battle(tag, current_clan_war_folder, villager_notes_folder, seer_notes_folder, medic_notes_folder, werewolf_notes_folder):
    if not os.path.exists(current_clan_war_folder):
        os.makedirs(current_clan_war_folder)
    data_folder = os.path.join(current_clan_war_folder, 'data_'+tag)
    prompt_logging_folder = os.path.join(current_clan_war_folder, 'prompt_logging_'+tag)
    
    if not os.path.exists(data_folder):
        os.makedirs(data_folder)
    else:
        x = input("The data folder already exists. Do you want to delete it and create a new one? (yes/no): ")
        if x.lower() == 'yes':
            shutil.rmtree(data_folder)
            os.makedirs(data_folder)
        else:
            raise Exception("Aborting the operation.")
    if not os.path.exists(prompt_logging_folder):
        os.makedirs(prompt_logging_folder)
    else:
        x = input("The prompt logging folder already exists. Do you want to delete it and create a new one? (yes/no): ")
        if x.lower() == 'yes':
            shutil.rmtree(prompt_logging_folder)
            os.makedirs(prompt_logging_folder)
        else:
            raise Exception("Aborting the operation.")
    
    
    
    input_txt_path = os.path.join(prompt_logging_folder, 'message_input_history_backup_'+tag+'.txt')
    output_txt_path = os.path.join(prompt_logging_folder, 'message_output_history_backup_'+tag+'.txt')
    config_dict = obtain_config_dict(data_folder, input_txt_path, output_txt_path,
                                     villager_notes_folder, seer_notes_folder, medic_notes_folder, werewolf_notes_folder)
    config_path = os.path.join(current_clan_war_folder, 'game_config_'+tag+'.json')
    json.dump(config_dict, open(config_path,'w'), indent=4)
    
    
    return dict(
        data_folder = data_folder,
        prompt_logging_folder = prompt_logging_folder,
        config_path = config_path,
        config = config_dict
    )

def run_one_battle(data_folder, config_path, num_games, num_process):
    config_path = config_path
    try:
        result = subprocess.run(['python', 'run_new.py', 
                                 '--num_games', num_games, 
                                 '--num_processes', num_process, 
                                 '--config_path', config_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while running battle: {e}")

def make_battle_dir_and_run_one_battle(tag, current_clan_war_folder,
                                       villager_notes_folder, seer_notes_folder, medic_notes_folder, werewolf_notes_folder,
                                       num_games, num_process):
    battle_config_dict = create_folder_for_one_battle(tag, current_clan_war_folder, villager_notes_folder, seer_notes_folder, medic_notes_folder, werewolf_notes_folder)
    run_one_battle(battle_config_dict['data_folder'], battle_config_dict['config_path'], num_games, num_process)
    return battle_config_dict