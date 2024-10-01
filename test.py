import re


def extract_info(string):
    pattern = r"Player (\d+)'s role is (\w+)(?: with (high|medium|low) confidence)?\.\s*My reason is: (.*)?"
    match = re.match(pattern, string)
    if match:
        id = match.group(1)
        role = match.group(2)
        confidence = match.group(3) if match.group(3) else None
        reason = match.group(4) if match.group(4) else None
        return {
            "id": id,
            "role": role,
            "confidence": confidence,
            "reason": reason
        }
    else:
        return None

# Example usage
test_string = "Player 42's role is detective. My reason is: Observed behavior."
result = extract_info(test_string)
print(result)
