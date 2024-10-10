import os
import subprocess
import time
import json
from copy import deepcopy
import re
import shutil

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
        
        
def get_largest_file_in_directory(directory):
    try:
        # Get the list of files in the directory
        files = os.listdir(directory)
        
        # Filter to include only files (not directories)
        files = [f for f in files if os.path.isfile(os.path.join(directory, f))]
        
        # Return the file with the largest dictionary order
        if files:
            largest_file = max(files)
            return os.path.join(directory, largest_file)
        else:
            return None  # No files in the directory
    except Exception as e:
        print(f"Error occurred: {e}")
        return None
    

def int_to_str(ver_int):
    if ver_int < 10:
        return '0'+str(ver_int)
    else:
        return str(ver_int)
    

def run_game(ver, config_dir = './configs'):
    try:
        result = subprocess.run(['python', 'run_new.py', '--config_path', os.path.join(config_dir,"game_config_v"+int_to_str(ver)+".json")], check=True)
    except subprocess.CalledProcessError as e:
        print("Error occurred while running version "+int_to_str(ver)+": {e}")

def create_game_config(ver,config_dir = './configs'):
    current_config = os.path.join(config_dir,"game_config_v"+int_to_str(ver)+".json")
    into_config = os.path.join(config_dir,"game_config_v"+int_to_str(ver+1)+".json")
    current_dict = json.load(open(current_config))
    new_dict = deepcopy(current_dict)
    new_dict['data_folder'] = 'data_'+'v'+str(ver+1)
    for i in range(len(new_dict["players"])):
        org_dict = new_dict["players"][i]
        new_dict["players"][i]["reflex_note_belief_path"] = re.sub('v'+str(ver)+r'\b', 'v'+str(ver+1), org_dict["reflex_note_belief_path"])
        new_dict["players"][i]["reflex_note_policy_path"] = re.sub('v'+str(ver)+r'\b', 'v'+str(ver+1), org_dict["reflex_note_policy_path"])
    
    json.dump(new_dict, open(into_config,'w'), indent=4)
    
def copy_files(ver, notes_dir = 'core'):
    current_dir = os.path.join(notes_dir, 'notes_v' + str(ver))
    target_dir = os.path.join(notes_dir, 'notes_v'+str(ver+1))
    copy_directory_with_prompt(current_dir, target_dir)

def run_reflex(ver, config_dir = './configs'):
    data_dir = './data_v'+str(ver)
    largest_ckpt_path = get_largest_file_in_directory(data_dir)
    
    
    
    
    new_config_path = os.path.join(config_dir,"game_config_v"+int_to_str(ver+1)+".json")
    try:
        result = subprocess.run(['python', 'reflex_from_data.py', '--config_path', new_config_path, '--data-path', largest_ckpt_path], check=True)
    except subprocess.CalledProcessError as e:
        print("Error occurred while reflexing version "+int_to_str(ver)+": {e}")

def one_iter(ver=1):
    run_game(ver)
    time.sleep(1)
    create_game_config(ver)
    copy_files(ver)
    time.sleep(1)
    run_reflex(ver)

def main_loop(MAX_ITER):
    for ver in range(1,MAX_ITER+1):
        one_iter(ver)
        




if __name__ == "__main__":
    main_loop(3)
