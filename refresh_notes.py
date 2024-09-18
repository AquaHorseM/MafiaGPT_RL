import shutil
import os

base_dir = "core/players/prompts"
backup_dir = "core/players/notes_backup"
os.makedirs(backup_dir, exist_ok=True)
roles = ["werewolf", "seer", "villager", "medic"]
reflex_types = ["belief", "policy"]
for role in roles:
    for reflex_type in reflex_types:
        role_dir = os.path.join(base_dir, role)
        if os.path.exists(os.path.join(role_dir, f"reflex_note_{reflex_type}.txt")):
            shutil.copy(os.path.join(role_dir, f"reflex_note_{reflex_type}.txt"), os.path.join(backup_dir, f"{role}_reflex_note_{reflex_type}.txt"))
        shutil.copy(os.path.join(role_dir, f"reflex_note_{reflex_type}_backup.txt"), os.path.join(role_dir, f"reflex_note_{reflex_type}.txt"))
    