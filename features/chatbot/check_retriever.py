import asyncio

from features.chatbot.retriever import retrieve

CASES = [
    ("탈퇴하면 데이터는 언제 삭제돼요?", "2.3"),
    ("카카오 말고 다른 로그인도 되나요?", "2.1"),
    ("그룹 이름은 몇 글자까지 쓸 수 있어요?", "3.1"),
    ("그룹은 최대 몇 개까지 참여할 수 있어요?", "3.4"),
    ("교환 요청이 진행 중인데 그룹을 나갈 수 있어요?", "3.5"),
    ("물건 사진은 몇 장까지 올릴 수 있어요?", "4.1"),
    ("교환 완료는 누가 확정하나요?", "5.3"),
    ("채팅방을 나가면 다시 들어갈 수 있어요?", "6.3"),
    ("신고를 당하면 어떤 제재를 받아요?", "9.2"),
    ("제재 받았는데 이의 제기는 어떻게 해요?", "9.3"),
]
OUT_OF_SCOPE = ["오늘 날씨 어때?", ".", "점심 뭐 먹지"]


# retrieve가 비동기 함수라서 이것도 비동기
async def main() -> None:
    hits = 0
    for question, expected in CASES:
        # results: 정책 2개의 목록
        results = await retrieve(question)
        sections = [item["section"] for item in results]
        distances = [round(item["distance"], 3) for item in results]
        # hit: 정답 번호가 찾은 번호 안에 있는지 true/false
        hit = expected in sections
        hits += hit
        mark = "O" if hit else "X"
        print(f"{mark} {question} | 정답 {expected} | 결과 {sections} {distances}")
    print(f"\n적중: {hits}/{len(CASES)} ({hits / len(CASES):.0%})")

    print("\n[범위 밖 질문의 거리]")
    for question in OUT_OF_SCOPE:
        results = await retrieve(question)
        distances = [round(item["distance"], 3) for item in results]
        print(question, distances)


if __name__ == "__main__":
    asyncio.run(main())
