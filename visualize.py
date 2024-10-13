import pickle
import json
def unimportant_level(input_str):
    if input_str.startswith("Game starts."):
        return 0
    elif input_str.startswith("Round"):
        return 1
    elif input_str.startswith("Player") and input_str.endswith("died."):
        return 2
    elif input_str.startswith("Voting started"):
        return 2
    elif input_str.startswith("Night starts"):
        return 2
    elif input_str.startswith("Day starts"):
        return 2
    elif input_str.startswith("Nobody died last night"):
        return 2
    elif input_str.startswith("Game ends"):
        return 0
    else:
        return 3
def visualize_one_pickle(pickle_path, json_path):
    pickle_data = pickle.load(open(pickle_path, 'rb'))
    print(str(pickle_data))
    
    
    
    events = pickle_data.get_events_after(0)
    results = [str(x) for x in events]
    for i in range(len(results)):
        content = results[i][7:] if results[i].startswith("Event: ") else results[i]
        unimportance = unimportant_level(content)
        results[i] = (1+unimportance)*'    '  + content
    results = ['    '  + 'Preliminaries.'] + results
    # json.dump(results, open(json_path, 'w'), indent=4)
    data = results
    output_lines = []
    for line in data:
        # Count the number of leading spaces
        leading_spaces = len(line) - len(line.lstrip(' '))
        # Remove the leading spaces from the string
        stripped_line = line.lstrip(' ')
        # Store the leading spaces count and the stripped line
        output_lines.append((leading_spaces, stripped_line))

    # Now, write the output with indentation outside the strings
    with open(json_path, 'w') as file:
        file.write('[\n')
        for idx, (indent, content) in enumerate(output_lines):
            # Create the indentation outside the string
            indented_line = ' ' * indent + json.dumps(content)
            # Add a comma except for the last element
            if idx < len(output_lines) - 1:
                indented_line += ','
            file.write(indented_line + '\n')
        file.write(']')
if __name__ == '__main__':
    visualize_one_pickle(r'transport/v9vv1_game4.pkl', 'a.json')

            