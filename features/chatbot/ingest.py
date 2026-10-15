import re
from pathlib import Path

import chromadb
from chromadb.errors import NotFoundError

from core.config import settings
from shared.embedding.embedding_provider import embed_passages


# 마크다운을 조각으로 나누는 함수
def parse_chunks(text: str) -> list[dict]:
    chunks: list[dict] = []
    chapter = ""
    current: dict | None = None

    for line in text.splitlines():
        if line.startswith("### "):
            title = line[4:].strip()
            current = {"title": f"{chapter} > {title}", "heading": title, "lines": []}
            chunks.append(current)
        elif line.startswith("## "):
            chapter = line[3:].strip()
            current = {"title": chapter, "heading": chapter, "lines": []}
            chunks.append(current)
        elif line.strip() == "---":
            continue
        elif current is not None:
            current["lines"].append(line)
    result = []
    for chunk in chunks:
        content = "\n".join(chunk["lines"]).strip()
        if not content:
            continue
        match = re.match(r"^(\d+(?:\.\d+)?)\.?\s", chunk["heading"])
        section = match.group(1) if match else chunk["heading"]
        result.append({"section": section, "title": chunk["title"], "content": content})
    return result


# main 읽고, 벡터로 바꾸고, 저장하는 함수
def main() -> None:
    chunks: list[dict] = []
    for path in sorted(Path(settings.policy_docs_path).glob("*.md")):
        chunks.extend(parse_chunks(path.read_text(encoding="utf-8")))

    texts = [f"{chunk['title']}\n{chunk['content']}" for chunk in chunks]
    embeddings = embed_passages(texts)

    client = chromadb.PersistentClient(path=settings.chroma_path)
    try:
        client.delete_collection(settings.chroma_collection_name)
    except NotFoundError:
        print("기존 컬렉션이 없어서 새로 만듭니다.")
    collection = client.create_collection(
        settings.chroma_collection_name,
        configuration={"hnsw": {"space": "cosine"}},
    )
    collection.add(
        ids=[chunk["section"] for chunk in chunks],
        embeddings=embeddings,
        documents=[chunk["content"] for chunk in chunks],
        metadatas=[
            {"section": chunk["section"], "title": chunk["title"]} for chunk in chunks
        ],
    )
    print(f"인제스트 완료: {len(chunks)}개 청크")


if __name__ == "__main__":
    main()
