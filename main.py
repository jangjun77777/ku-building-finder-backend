from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
import re

from buildings import load_buildings, find_building_local, Building

# =====================
# 기본 설정
# =====================
load_dotenv()
client = OpenAI()

CSV_PATH = "Building_information_data.csv"
BUILDINGS = load_buildings(CSV_PATH)

app = FastAPI(title="KU Campus Building Finder API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================
# 유틸 함수
# =====================

def detect_language(text: str) -> str:
    return "ko" if any("\uac00" <= ch <= "\ud7a3" for ch in text) else "en"


def extract_room_info(text: str) -> str | None:
    """
    예: B202 → Basement 2nd floor, room 2
    """
    match = re.search(r"\bB(\d)(\d{2})\b", text.upper())
    if not match:
        return None

    floor = match.group(1)
    room = match.group(2)
    return f"B{floor}{room} means Basement {floor}F (지하 {floor}층), room {room}."


def format_single_building(b: Building, lang: str) -> str:
    if lang == "ko":
        return (
            f"건물명(한국어): {b.name_kr}\n"
            f"건물명(영어): {b.name_en}\n"
            f"네이버 지도 링크: {b.map_link}"
        )
    else:
        return (
            f"Building name (Korean): {b.name_kr}\n"
            f"Building name (English): {b.name_en}\n"
            f"Naver Map link: {b.map_link}"
        )


def format_multiple_buildings(buildings: list[Building], lang: str) -> str:
    header = (
        "다음 건물들이 해당될 수 있습니다:\n\n"
        if lang == "ko"
        else "These buildings may be relevant:\n\n"
    )

    items = []
    for b in buildings[:3]:
        items.append(
            format_single_building(b, lang)
        )

    return header + "\n\n".join(items)


def category_search(query: str) -> list[Building]:
    q = query.lower()

    if "도서관" in q or "library" in q:
        return [
            b for b in BUILDINGS
            if "도서관" in b.name_kr or "library" in b.name_en.lower()
        ]

    if "법학" in q or "law" in q:
        return [
            b for b in BUILDINGS
            if "법학" in b.name_kr or "law" in b.name_en.lower()
        ]

    if "사범" in q or "education" in q:
        return [
            b for b in BUILDINGS
            if "사범" in b.name_kr or "education" in b.name_en.lower()
        ]

    return []


# =====================
# 핵심 로직
# =====================

def ku_chat(user_message: str) -> str:
    lang = detect_language(user_message)

    # 1️⃣ GPT로 검색 키워드만 추출
    extract = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "Extract ONLY the building name, nickname, or building category. "
                    "Do not add explanations."
                )
            },
            {"role": "user", "content": user_message},
        ],
    )

    query = extract.choices[0].message.content.strip()
    query = re.sub(r"[\.입니다요]+$", "", query).strip()

    # 2️⃣ 정확한 단일 건물 검색
    exact = find_building_local(query, BUILDINGS)
    if exact:
        response = format_single_building(exact, lang)

        room_info = extract_room_info(user_message)
        if room_info:
            response += "\n\n" + room_info

        return response

    # 3️⃣ 카테고리 검색 (여러 건물)
    candidates = category_search(query)
    if candidates:
        response = format_multiple_buildings(candidates, lang)

        room_info = extract_room_info(user_message)
        if room_info:
            response += "\n\n" + room_info

        return response

    # 4️⃣ 실패
    return (
        "알 수 없는 건물입니다. 다시 입력해주세요."
        if lang == "ko"
        else "Could not recognize that building. Please try again."
    )


# =====================
# API
# =====================

class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@app.post("/chat", response_model=ChatResponse)
@app.post("/chat/", response_model=ChatResponse)
async def chat(req: ChatRequest):
    return ChatResponse(reply=ku_chat(req.message))


@app.get("/")
def root():
    return {"status": "ok"}
