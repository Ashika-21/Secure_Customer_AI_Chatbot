import ollama

response = ollama.embed(
    model="nomic-embed-text",
    input="Arun has an unpaid invoice for 1500 rupees."
)

vector = response["embeddings"][0]

print("Embedding successful!")
print("Vector dimensions:", len(vector))
print("First 5 values:", vector[:5])