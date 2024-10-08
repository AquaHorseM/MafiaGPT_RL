import os
import re
import shutil
import glob

# Define the source and destination patterns
source_pattern = r"core/notes_v1/([^/]+)/\1_reflex_note_([^/]+)_backup\.txt"
destination_pattern = r"core/notes_v1/{}/{}_reflex_note_{}.txt"

# Use glob to find all files matching the source pattern
for file_path in glob.glob("core/notes_v1/*/*_reflex_note_*_backup.txt"):
    match = re.match(source_pattern, file_path)
    if match:
        role = match.group(1)
        note_type = match.group(2)
        destination_path = destination_pattern.format(role, role, note_type)
        # Copy the file
        shutil.copy(file_path, destination_path)
        print(f"Copied: {file_path} -> {destination_path}")
