from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
import os
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
- Understand building requests in any language.
- Always give the Naver Map link directly.
- Use clear underground floor notation: "Basement 2F (지하 2층)" if needed.
- Never guess. Only use tool results.
"""

def gpt_answer(user_message: str, result: dict) -> str:
    if not result["found"]:
        return "The code you entered was not recognized. Please try again."

    return f"""
Here is the information.
Code: {result['code']}
Building name(KOREAN): {result['name_kr']}
Building name(ENGLISH): {result['name_en']}
Map link(Naver map): {result['map_link']}
"""


def ku_chat(user_message: str) -> str:
    # 모델이 building name/code를 추출
    extract = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]
    )

    query = extract.choices[0].message.content.strip()

    # 로컬에서 검색
    b = find_building_local(query, BUILDINGS)

    if not b:
        return "The code you entered was not recognized. Please try again."

    return gpt_answer(user_message, {
        "found": True,
        "code": b.code,
        "name_kr": b.name_kr,
        "name_en": b.name_en,
        "map_link": b.map_link,
    })


class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str


@app.post("/chat", response_model=ChatResponse)
@app.post("/chat/", response_model=ChatResponse)
async def chat(req: ChatRequest):
    return ChatResponse(reply=ku_chat(req.message))
