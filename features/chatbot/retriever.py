import asyncio
from functools import lru_cache

import chromadb

from core.config import settings
from features.chatbot.exceptions import EmbeddingModelError, RetrievalError
from shared.embedding.embedding_provider import embed_queries


# 저장된 정책 컬렉션을 여는 함수
@lru_cache(maxsize=1)
def _get_collection():
    client = chromadb.PersistentClient(path=settings.chroma_path)
    return client.get_collection(settings.chroma_collection_name)


# 질문 글(query)을 받아서 찾은 정책 목록 돌려주는 함수
async def retrieve(query: str) -> list[dict]:
    try:
        # asyncio.to_thread: 모델 계산은 CPU를 오래 쓰는 일이라 스레드에서 돌림
        embedding = (await asyncio.to_thread(embed_queries, [query]))[0]
    except Exception as error:
        raise EmbeddingModelError(stage="retrieve", detail=str(error)) from error

    try:
        collection = _get_collection()
        result = await asyncio.to_thread(
            collection.query,
            query_embeddings=[embedding],
            n_results=settings.chatbot_top_k,  # 지금은 2개
        )
    except Exception as error:
        raise RetrievalError(stage="retrieve", detail=str(error)) from error

    return [
        {
            "section": meta["section"],
            "title": meta["title"],
            "content": document,
            "distance": distance,
        }
        for meta, document, distance in zip(
            result["metadatas"][0], result["documents"][0], result["distances"][0]
        )
    ]
