from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
import re

from buildings import load_buildings, find_building_local, Building

load_dotenv()
client = OpenAI()

CSV_PATH = "Building_information_data.csv"
BUILDINGS = load_buildings(CSV_PATH)

WATER_PURIFIER_LOCATIONS = {
    "우당교양관": {"ko": "2층 로비", "en": "2F lobby"},
    "미디어관": {"ko": "1층 로비", "en": "1F lobby"},
    "정경관": {"ko": "1층, 2층, 5층", "en": "1F, 2F, and 5F"},
    "학생회관": {"ko": "1층, 2층(학생식당 내부)", "en": "1F and inside the 2F cafeteria"},
    "SK미래관": {"ko": "2층, 4층", "en": "2F and 4F"},
}

app = FastAPI(title="KU Campus Building Finder API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def detect_language(text: str) -> str:
    return "ko" if any("\uac00" <= ch <= "\ud7a3" for ch in text) else "en"


def clean_query(text: str) -> str:
    text = text.strip()
    text = re.sub(r"[.!?]+$", "", text)
    text = re.sub(r"(입니다|이에요|예요|요)$", "", text)
    return text.strip()


def normalize_text(text: str) -> str:
    return str(text or "").strip().lower().replace(" ", "")


def is_water_query(text: str) -> bool:
    q = text.lower().strip()

    keywords = [
        "정수기",
        "물",
        "water",
        "water purifier",
        "water dispenser",
        "drinking water",
        "water station",
    ]

    return any(k in q for k in keywords)


def format_water_purifier_locations(lang: str) -> str:
    if lang == "ko":
        return (
            "정수기 위치는 다음과 같습니다:\n\n"
            "• 우당교양관: 2층 로비\n"
            "• 미디어관: 1층 로비\n"
            "• 정경관: 1층, 2층, 5층\n"
            "• 학생회관: 1층, 2층(학생식당 내부)\n"
            "• SK미래관: 2층, 4층"
        )

    return (
        "Water purifier locations:\n\n"
        "• Woodang General Education Hall: 2F lobby\n"
        "• Media Hall: 1F lobby\n"
        "• Political Science and Economics Building: 1F, 2F, and 5F\n"
        "• Student Union: 1F and inside the 2F cafeteria\n"
        "• SK Future Hall: 2F and 4F"
    )


def extract_room_info(text: str) -> str | None:
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

    return (
        f"Building name (Korean): {b.name_kr}\n"
        f"Building name (English): {b.name_en}\n"
        f"Naver Map link: {b.map_link}"
    )


def format_multiple_buildings(buildings: list[Building], lang: str) -> str:
    count = len(buildings)

    header = (
        f"다음 건물 {count}개가 해당될 수 있습니다:\n\n"
        if lang == "ko"
        else f"{count} buildings may be relevant:\n\n"
    )

    items = [format_single_building(b, lang) for b in buildings]
    return header + "\n\n".join(items)


def is_general_category_query(text: str) -> bool:
    q = text.strip().lower()

    general_queries = {
        "library", "libraries", "도서관",
        "cafe", "cafes", "café", "coffee", "카페", "커피",
        "cafeteria", "cafeterias", "dining hall", "dining halls",
        "student cafeteria", "student cafeterias", "식당", "학생식당", "학식",
        "building", "buildings", "건물",
    }

    return q in general_queries


def category_search(query: str) -> list[Building]:
    q = query.lower().strip()

    category_keywords = {
        "library": ["도서관", "library", "libraries"],
        "cafeteria": [
            "cafeteria",
            "cafeterias",
            "student cafeteria",
            "student cafeterias",
            "dining hall",
            "dining halls",
            "학생식당",
            "학식",
            "식당",
            "밥",
            "점심",
            "lunch",
            "meal",
        ],
        "cafe": [
            "cafe",
            "cafes",
            "café",
            "coffee",
            "coffee shop",
            "카페",
            "커피",
            "음료",
            "drink",
        ],
        "law": ["법학", "law"],
        "education": ["사범", "education"],
        "nursing": ["간호", "nursing"],
        "engineering": ["공학", "engineering"],
        "science": ["과학", "science"],
        "business": ["경영", "business"],
    }

    matched_category = None
    matched_keywords = None

    if q in {
        "cafe", "cafes", "café",
        "coffee", "coffee shop",
        "카페", "커피"
    }:
        matched_category = "cafe"
        matched_keywords = category_keywords["cafe"]

    elif q in {
        "cafeteria", "cafeterias",
        "student cafeteria", "student cafeterias",
        "dining hall", "dining halls",
        "학생식당", "학식", "식당"
    }:
        matched_category = "cafeteria"
        matched_keywords = category_keywords["cafeteria"]

    else:
        for category, keywords in category_keywords.items():
            if any(keyword in q for keyword in keywords):
                matched_category = category
                matched_keywords = keywords
                break

    if not matched_category:
        return []

    if matched_category == "library":
        library_names = {
            "대학원", "Graduate School",
            "중앙도서관", "Central Library",
            "과학도서관", "Science Library",
            "Science & Engineering Library",
            "의학도서관", "Medical Library",
            "해송법학도서관", "Haesong Law Library",
            "백주년기념삼성관/박물관",
            "Centennial Samsung Hall / Museum/Library",
        }

        normalized_library_names = {normalize_text(x) for x in library_names}

        return [
            b for b in BUILDINGS
            if normalize_text(b.name_kr) in normalized_library_names
            or normalize_text(b.name_en) in normalized_library_names
            or any(
                normalize_text(n) in normalized_library_names
                for n in str(b.nickname or "").split(",")
            )
        ]

          if matched_category == "cafeteria":
        cafeteria_names = {
            "학생회관",
            "Student Union",
            "애기능생활관",
            "애기능 생활관",
            "Aegineung Residence Hall",
            "Aegineung Life Hall",
            "Tiger Rice Bowl Cafeteria",
            "Tiger Rice Bowl",
        }

        normalized_cafeteria_names = {normalize_text(x) for x in cafeteria_names}

        return [
            b for b in BUILDINGS
            if normalize_text(b.name_kr) in normalized_cafeteria_names
            or normalize_text(b.name_en) in normalized_cafeteria_names
            or any(
                normalize_text(n) in normalized_cafeteria_names
                for n in str(b.nickname or "").split(",")
            )
        ]

    if matched_category == "cafe":
        return [
            b for b in BUILDINGS
            if (
                any(k in b.name_kr.lower() for k in matched_keywords)
                or any(k in b.name_en.lower() for k in matched_keywords)
                or any(k in b.nickname.lower() for k in matched_keywords)
            )
            and "cafeteria" not in b.name_en.lower()
            and "student cafeteria" not in b.name_en.lower()
            and "학생식당" not in b.name_kr
            and "식당" not in b.name_kr
        ]

    return [
        b for b in BUILDINGS
        if any(k in b.name_kr.lower() for k in matched_keywords)
        or any(k in b.name_en.lower() for k in matched_keywords)
        or any(k in b.nickname.lower() for k in matched_keywords)
    ]


def ku_chat(user_message: str) -> str:
    lang = detect_language(user_message)

    if is_water_query(user_message):
        return format_water_purifier_locations(lang)

    if is_general_category_query(user_message):
        candidates = category_search(user_message)

        if candidates:
            response = format_multiple_buildings(candidates, lang)

            room_info = extract_room_info(user_message)
            if room_info:
                response += "\n\n" + room_info

            return response

    exact = find_building_local(user_message, BUILDINGS)

    if exact:
        response = format_single_building(exact, lang)

        room_info = extract_room_info(user_message)
        if room_info:
            response += "\n\n" + room_info

        return response

    extract = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an information extractor for Korea University campus. "
                    "Return ONLY one building name or ONE category. "
                    "Available categories are: building, library, cafe, cafeteria. "
                    "If the user asks only about libraries or 도서관 in general, return 'library'. "
                    "If the user asks only about cafes, coffee, 카페, or 커피 in general, return 'cafe'. "
                    "If the user asks only about cafeterias, dining halls, student cafeterias, 식당, 학생식당, or 학식 in general, return 'cafeteria'. "
                    "If the user mentions a specific building, library, cafe, cafeteria, or nickname, return ONLY that specific name. "
                    "Examples: "
                    "science library -> Science & Engineering Library. "
                    "central library -> Central Library. "
                    "medical library -> Medical Library. "
                    "law library -> Haesong Law Library. "
                    "library -> library. "
                    "libraries -> library. "
                    "cafe -> cafe. "
                    "coffee -> cafe. "
                    "cafeteria -> cafeteria. "
                    "student cafeteria -> cafeteria. "
                    "Do not explain."
                ),
            },
            {
                "role": "user",
                "content": user_message,
            },
        ],
    )

    query = clean_query(extract.choices[0].message.content.strip())

    if is_general_category_query(query):
        candidates = category_search(query)

        if candidates:
            response = format_multiple_buildings(candidates, lang)

            room_info = extract_room_info(user_message)
            if room_info:
                response += "\n\n" + room_info

            return response

    exact = find_building_local(query, BUILDINGS)

    if exact:
        response = format_single_building(exact, lang)

        room_info = extract_room_info(user_message)
        if room_info:
            response += "\n\n" + room_info

        return response

    candidates = category_search(f"{query} {user_message}")

    if candidates:
        response = format_multiple_buildings(candidates, lang)

        room_info = extract_room_info(user_message)
        if room_info:
            response += "\n\n" + room_info

        return response

    return (
        "알 수 없는 건물입니다. 다시 입력해주세요."
        if lang == "ko"
        else "Could not recognize that building. Please try again."
    )


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
