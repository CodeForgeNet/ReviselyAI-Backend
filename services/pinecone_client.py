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

REVISELY_INDEX_NAME = "revisely-documents"


def get_pinecone_index(dimension: int, metric: str = 'cosine'):
    """
    Initializes and returns a Pinecone index. Creates the index if it doesn't exist.
    """
    existing_indexes = pinecone_client.list_indexes()
    index_exists = False
    for index_info in existing_indexes:
        if index_info['name'] == REVISELY_INDEX_NAME:
            index_exists = True
            break

    if not index_exists:

        pinecone_client.create_index(
            name=REVISELY_INDEX_NAME,
            dimension=dimension,
            metric=metric,
            spec=ServerlessSpec(cloud='aws', region='us-east-1')
        )

    else:
        print(
            f"Pinecone index '{REVISELY_INDEX_NAME}' already exists. Connecting to existing index.")
    return pinecone_client.Index(REVISELY_INDEX_NAME)

# Example usage (can be removed or commented out after initial setup)
# if __name__ == "__main__":
#     # Assuming you have an embedding model that outputs 768 dimensions
#     # You'll need to replace this with your actual embedding dimension
#     example_dimension = 768
#     example_index = get_pinecone_index("revisely-test-index", example_dimension)
#     print(f"Successfully connected to Pinecone index: {example_index.name}")
