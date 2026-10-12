from functools import lru_cache

from core.config import settings


@lru_cache(maxsize=1)
def _get_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(settings.embedding_model_name)


# query = 찾는 쪽 (사용자 질문)
def embed_queries(texts: list[str]) -> list[list[float]]:
    prefixed = [f"query: {text}" for text in texts]
    return _get_model().encode(prefixed, normalize_embeddings=True).tolist()


# passages = 찾아지는 쪽 (정책 문서 섹션)
def embed_passages(texts: list[str]) -> list[list[float]]:
    prefixed = [f"passage: {text}" for text in texts]
    return _get_model().encode(prefixed, normalize_embeddings=True).tolist()
