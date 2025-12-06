from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
import json

from buildings import load_buildings, find_building_local

# Load API Key from .env
load_dotenv()
client = OpenAI()

# Load CSV
CSV_PATH = "Building_information_data.csv"
BUILDINGS = load_buildings(CSV_PATH)

# FastAPI App
app = FastAPI(title="KU Campus Building Finder API")

# CORS Settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prompt: extract building keyword only
EXTRACT_PROMPT = """
You extract ONLY the building code or building name from the user's message.
No other text. Just the building code "141" OR exact building name like "Central Library" or "하나스퀘어".
Return ONE best guess. If unsure, return the most likely term referring to a building.
"""

# Prompt: final formatting rules
ANSWER_PROMPT = """
You are KU Campus Building Finder, a multilingual assistant for Korea University (Seoul).

Rules:
- Always provide the Naver Map link directly
- Use clear underground floor notation if needed:
  Example: "Basement 2F (지하 2층)"
- Never guess. If no match → reply:
  "The code you entered was not recognized. Please try again."

Answer ONLY in this format when data exists:

Here is the information.
Code: <code>
Building name(KOREAN): <name_kr>
Building name(ENGLISH): <name_en>
Map link(Naver map): <map_link>
"""


# --- GPT Response Formatter ---------------------------------------------------

def format_answer(b):
    return f"""
Here is the information.
Code: {b.code}
Building name(KOREAN): {b.name_kr}
Building name(ENGLISH): {b.name_en}
Map link(Naver map): {b.map_link}
"""


# --- Chat Logic --------------------------------------------------------------

def ku_chat(user_message: str) -> str:
    # 1) Extract query keyword
    extract = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": EXTRACT_PROMPT},
            {"role": "user", "content": user_message},
        ]
    )

    query = extract.choices[0].message.content.strip()

    print("🔍 Extracted Query:", query)

    # Search local building DB
    b = find_building_local(query, BUILDINGS)

    if not b:
        return "The code you entered was not recognized. Please try again."

    # Return formatted building information
    return format_answer(b)


# --- FastAPI Models ----------------------------------------------------------

class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


# --- API Endpoints -----------------------------------------------------------

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    reply = ku_chat(req.message)
    return ChatResponse(reply=reply)


@app.get("/")  # For Render health check
def health():
    return {"status": "ok"}
