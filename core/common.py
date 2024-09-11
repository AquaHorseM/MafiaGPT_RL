n_speak_actions = 7

speak_type_mapping = {
    "none": 0, # "no speech type"
    "honest challenge": 1,
    "deceptive challenge": 2,
    "honest protect": 3,
    "deceptive protect": 4,
    "honest statement": 5,
    "deceptive statement": 6
}

speak_type_id_to_str = {v: k for k, v in speak_type_mapping.items()}