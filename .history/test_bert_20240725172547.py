from transformers import AutoTokenizer, BertModel
import torch

tokenizer = AutoTokenizer.from_pretrained("google-bert/bert-base-uncased")
model = BertModel.from_pretrained("google-bert/bert-base-uncased")

sentences = []
sentences.append("I am a villager, and I suppose that player 3 is a werewolf.")
sentences.append("I am a villager and I know nothing as I am a simple villager.")
sentences.append("I am the seer and I know that player 3 is a werewolf.")

def get_bert_embedding(sentence):
    inputs = tokenizer(sentence, return_tensors="pt")
    outputs = model(**inputs)
    return torch.mean(outputs.last_hidden_state, dim=1)

embeddings = []

for sentence in sentences:
    print(f"Sentence: {sentence}")
    embedding = get_bert_embedding(sentence)
    print(f"Embedding shape: {embedding.shape}")
    embeddings.append(embedding)
    
#Check the distance of the sentences
distance_1_2 = torch.dist(embeddings[0], embeddings[1])
distance_1_3 = torch.dist(embeddings[0], embeddings[2])
distance_2_3 = torch.dist(embeddings[1], embeddings[2])
print(f"Distance between 1 and 2: {distance_1_2}")
print(f"Distance between 1 and 3: {distance_1_3}")
print(f"Distance between 2 and 3: {distance_2_3}")