from transformers import AutoTokenizer, BertModel
import torch

tokenizer = AutoTokenizer.from_pretrained("google-bert/bert-base-uncased")
model = BertModel.from_pretrained("google-bert/bert-base-uncased")

sentences = []
sentences.append("Hello, my dog is cute")
sentences.append("Hello, my cat is cute")
sentences.append("Hello, my dog is dumb")

def get_bert_embedding(sentence):
    inputs = tokenizer("Hello, my dog is cute", return_tensors="pt")
    outputs = model(**inputs)
    return outputs.last_hidden_state

embeddings = []

for sentence in sentences:
    print(f"Sentence: {sentence}")
    embedding = get_bert_embedding(sentence)
    print(f"Embedding: {embedding}")
    embeddings.append(embedding)
    
#Check the distance of the sentences
distance_1_2 = torch.dist(embeddings[0], embeddings[1])
distance_1_3 = torch.dist(embeddings[0], embeddings[2])
distance_2_3 = torch.dist(embeddings[1], embeddings[2])
print(f"Distance between 1 and 2: {distance_1_2}")
print(f"Distance between 1 and 3: {distance_1_3}")
print(f"Distance between 2 and 3: {distance_2_3}")