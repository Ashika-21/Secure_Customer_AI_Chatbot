
import ollama
from qdrant_client import QdrantClient, models
from uuid import uuid5, NAMESPACE_DNS

client = QdrantClient(path="qdrant_storage")
COLLECTION_NAME = "customer_records"


def create_embedding(text: str):
    response = ollama.embed(
        model="nomic-embed-text",
        input=text
    )
    return response["embeddings"][0]


def create_collection():
    if not client.collection_exists(COLLECTION_NAME):
        sample_vector = create_embedding("test record")

        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=len(sample_vector),
                distance=models.Distance.COSINE
            )
        )


def store_record(customer_id: int, record_id: int, text: str):
    create_collection()

    vector = create_embedding(text)

    point_id = str(
        uuid5(
            NAMESPACE_DNS,
            f"customer-{customer_id}-record-{record_id}"
        )
    )

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            models.PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    "customer_id": customer_id,
                    "record_id": record_id,
                    "record_type": "invoice",
                    "text": text
                }
            )
        ]
    )


def search_records(customer_id: int, query: str, limit: int = 5):
    create_collection()

    query_vector = create_embedding(query)

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        query_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="customer_id",
                    match=models.MatchValue(value=customer_id)
                )
            ]
        ),
        limit=limit,
        with_payload=True
    )

    return [
        {
            "record_id": point.payload["record_id"],
            "text": point.payload["text"]
        }
        for point in results.points
    ]


def close_vector_store():
    client.close()
