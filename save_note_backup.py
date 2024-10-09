import shutil
import os

def store_to_backup(role: str, note_type: str) -> None:
    """
    Stores the current note to a backup file.
    
    Parameters:
    role (str): The role of the note.
    note_type (str): The type of the note.
    """
    current_note_path = f"core/notes_v1/{role}/{role}_reflex_note_{note_type}.txt"
    backup_note_path = f"core/notes_v1/{role}/{role}_reflex_note_{note_type}_backup.txt"
    
    # Ensure the current note exists before copying
    if os.path.exists(current_note_path):
        shutil.copyfile(current_note_path, backup_note_path)
        print(f"Backup created for {role}'s {note_type} note.")
    else:
        print(f"Current note does not exist at {current_note_path}. No backup made.")


roles = ["werewolf", "medic", "seer", "villager"]
note_types = ["belief", "policy"]

if __name__ == "__main__":
    for role in roles:
        for note_type in note_types:
            store_to_backup(role, note_type)