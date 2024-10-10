import shutil
import os
from argparse import ArgumentParser


def store_to_backup(role: str, note_type: str, version: int) -> None:
    """
    Stores the current note to a backup file.
    
    Parameters:
    role (str): The role of the note.
    note_type (str): The type of the note.
    """
    current_note_path = f"core/notes_v{str(version)}/{role}/{role}_reflex_note_{note_type}.txt"
    backup_note_path =  f"core/notes_fixed_version/notes_v{str(version)}/{role}/{role}_reflex_note_{note_type}.txt"
    
    # Ensure the current note exists before copying
    if os.path.exists(current_note_path):
        os.makedirs(os.path.dirname(backup_note_path), exist_ok=True)
        shutil.copyfile(current_note_path, backup_note_path)
        print(f"Backup created for {role}'s {note_type} note, version {version}.")
    else:
        print(f"Current note does not exist at {current_note_path}. No backup made.")
        
parser = ArgumentParser()
parser.add_argument("--version", type=int, default=1)


roles = ["werewolf", "medic", "seer", "villager"]
note_types = ["belief", "policy"]

if __name__ == "__main__":
    args = parser.parse_args()
    version = args.version
    for role in roles:
        for note_type in note_types:
            store_to_backup(role, note_type, version)
            