import shutil
import os

base_dir = "core/players/prompts"
roles = ["werewolf", "seer", "villager", "medic"]
for role in roles:
    role_dir = os.path.join(base_dir, role)
    if os.path.exists(role_dir):
        shutil.rmtree(role_dir)
    os.makedirs(role_dir)
    for i in range(1, 11):
        with open(os.path.join(role_dir, f"prompt_{i}.txt"), "w") as f:
            f.write(f"Prompt for {role} {i}")
    print(f"Created prompts for {role}")