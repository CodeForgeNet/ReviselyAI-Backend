import os
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")

if not PINECONE_API_KEY or not PINECONE_ENVIRONMENT:
    raise ValueError(
        "PINECONE_API_KEY and PINECONE_ENVIRONMENT must be set in the .env file")

pinecone_client = Pinecone(api_key=PINECONE_API_KEY,
                           environment=PINECONE_ENVIRONMENT)

def get_pinecone_index(index_name: str, dimension: int, metric: str = 'cosine'):
    """
    Initializes and returns a Pinecone index. Creates the index if it doesn't exist.
    """
    if index_name not in pinecone_client.list_indexes():
        pinecone_client.create_index(
            name=index_name,
            dimension=dimension,
            metric=metric,
            spec=ServerlessSpec(cloud='aws', region='us-east-1')
        )
    return pinecone_client.Index(index_name)

# Example usage (can be removed or commented out after initial setup)
# if __name__ == "__main__":
#     # Assuming you have an embedding model that outputs 768 dimensions
#     # You'll need to replace this with your actual embedding dimension
#     example_dimension = 768
#     example_index = get_pinecone_index("revisely-test-index", example_dimension)
#     print(f"Successfully connected to Pinecone index: {example_index.name}")
