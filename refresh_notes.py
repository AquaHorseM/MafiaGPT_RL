import os
import re
import shutil

# Define source and destination directories
source_dir = 'core/players/prompts'
destination_dir = 'core/notes_v1'

# Regex pattern to match file paths
pattern = r"core/players/prompts/(?P<role>[\w]+)/reflex_note_(?P<type>[\w]+)_backup\.txt"

# Iterate over all files in the source directory and its subdirectories
for root, _, files in os.walk(source_dir):
    for file_name in files:
        file_path = os.path.join(root, file_name)
        
        # Check if the file path matches the regex pattern
        match = re.match(pattern, file_path)
        if match:
            role = match.group('role')
            type_ = match.group('type')
            
            # Construct the new destination path
            new_file_path = f"{destination_dir}/{role}/{role}_reflex_note_{type_}_backup.txt"
            
            # Create the destination directory if it doesn't exist
            os.makedirs(os.path.dirname(new_file_path), exist_ok=True)
            
            # Copy the file to the new destination
            shutil.copy(file_path, new_file_path)
            print(f"Copied {file_path} to {new_file_path}")
