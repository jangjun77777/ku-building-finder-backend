from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
import json

from buildings import load_buildings, find_building_local

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

SYSTEM_PROMPT = """
You are KU Campus Building Finder, a multilingual assistant for Korea University (Seoul).

Rules:
- Respond in the same language user used.
- Provide:
  1) Korean building name
  2) English building name
  3) Naver map link
- Do NOT include building code unless asked explicitly.
- Always include the Naver map link if available.
- If the building is underground, use: "Basement 2F (지하 2층)" style.
- Never guess — respond only based on provided data.
"""


def format_building_response(b, lang="en"):
    if lang == "ko":
        return f"""
건물명(한국어): {b.name_kr}
건물명(영어): {b.name_en}
네이버 지도 링크: {b.map_link}
"""
    else:
        return f"""
Building name (Korean): {b.name_kr}
Building name (English): {b.name_en}
Naver Map link: {b.map_link}
"""


def detect_language(text: str) -> str:
    # 아주 단순한 한국어 판단 로직
    return "ko" if any("\uac00" <= ch <= "\ud7a3" for ch in text) else "en"


def ku_chat(user_message: str) -> str:
    # GPT가 건물명을 뽑아냄
    extract = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Extract only the building identifier (code or name)."},
            {"role": "user", "content": user_message},
        ]
    )
    query = extract.choices[0].message.content.strip()
    b = find_building_local(query, BUILDINGS)

    lang = detect_language(user_message)

    if not b:
        return "알 수 없는 건물입니다. 다시 입력해주세요." if lang == "ko" else \
               "Could not recognize that building. Please try again."

    return format_building_response(b, lang)


class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str


@app.post("/chat", response_model=ChatResponse)
@app.post("/chat/", response_model=ChatResponse)
async def chat(req: ChatRequest):
    reply = ku_chat(req.message)
    return ChatResponse(reply=reply)
