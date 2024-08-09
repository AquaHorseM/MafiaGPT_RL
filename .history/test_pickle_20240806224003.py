import pickle

class B:
    def __init__(self):
        self.value = 0

class A:
    def __init__(self, B):
        self.b = B

# Create instances
bb = B()
a = A(bb)

# Modify a.b
a.b.value = 10

# Serialize a
with open('a.pickle', 'wb') as f:
    pickle.dump(a, f)

a.b.value = 20

# Deserialize a
with open('a.pickle', 'rb') as f:
    loaded_a = pickle.load(f)

# Check loaded_a.b
print(loaded_a.b.value)  # Output will be 10

# Check if loaded_a.b is bb
print(f"loaded_a.b is {bb}")  # Output will be True
