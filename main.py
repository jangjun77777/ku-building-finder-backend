# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
import os
import json

from buildings import load_buildings, find_building_local, Building

# 환경 변수 로드 (.env에서 OPENAI_API_KEY 가져옴)
load_dotenv()

# OpenAI 클라이언트 생성 (환경변수에서 키를 자동으로 읽음)
client = OpenAI()

# CSV 경로 (파일명만 바꾸고 싶으면 여기 수정)
CSV_PATH = "Building_information_data.csv"
BUILDINGS = load_buildings(CSV_PATH)

app = FastAPI(title="KU Campus Building Finder API")

# CORS 설정 (프론트엔드에서 호출 가능하도록)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 배포 시에는 특정 도메인만 허용 권장
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SYSTEM_PROMPT = """
You are KU Campus Building Finder, a multilingual assistant for Korea University (Seoul).

- Users can speak in Korean, English, or any other language.
- Understand their natural language request about buildings on campus.
- When they ask where a building is, or what its code/name is, or how to find it,
  call the `find_building` tool with an appropriate query string
  (building code, nickname, or English/Korean name).
- Do not make up building information. Always rely on tool results.

If no building is found, answer in English:
"The code you entered was not recognized. Please try again."

If a building is found, reply in this format (in English, but keep Korean name as is):

Here is the information.
Code: <code>
Building name(KOREAN): <name_kr>
Building name(ENGLISH): <name_en>
Map link(Naver map): <map_link>
"""

# GPT에게 노출할 "툴" 정의 (find_building)
tools = [
    {
        "type": "function",
        "function": {
            "name": "find_building",
            "description": "Find a KU building by code, English/Korean name, or nickname.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Building code, English name, Korean name, or abbreviation extracted from the user's request."
                    }
                },
                "required": ["query"],
            },
        },
    }
]


def run_tool(tool_call):
    """
    OpenAI가 tool_call을 요청하면 실제 Python 함수 실행 후
    JSON 문자열로 결과 반환.
    """
    name = tool_call.function.name
    arguments = tool_call.function.arguments
    args = json.loads(arguments)

    if name == "find_building":
        query = args["query"]
        b = find_building_local(query, BUILDINGS)
        if not b:
            return json.dumps({"found": False})

        return json.dumps({
            "found": True,
            "code": b.code,
            "name_kr": b.name_kr,
            "name_en": b.name_en,
            "map_link": b.map_link,
        })

    # 이 예제에서는 find_building만 사용
    return json.dumps({"error": "unknown tool"})


def ku_multilingual_chat(user_message: str) -> str:
    """
    1) 유저 메시지를 GPT에 전달
    2) GPT가 필요하면 find_building 툴을 호출
    3) 툴 결과를 바탕으로 최종 답변 생성
    """
    # 1차 호출: GPT가 도구를 쓸지 판단
    first = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        tools=tools,
        tool_choice="auto",
    )

    msg = first.choices[0].message

    # 도구를 안 쓴 경우: 그냥 답변이 content에 들어 있음
    if not msg.tool_calls:
        return msg.content or ""

    # 여기서는 첫 번째 tool_call만 처리
    tool_call = msg.tool_calls[0]
    tool_result = run_tool(tool_call)

    # 2차 호출: 도구 결과를 바탕으로 최종 답변 생성
    second = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
            msg,  # tool_call이 들어 있는 assistant 메시지
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": tool_call.function.name,
                "content": tool_result,
            },
        ],
    )

    return second.choices[0].message.content or ""


# === FastAPI용 Request/Response 모델 ===
class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


# === /chat 엔드포인트 ===
@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    reply = ku_multilingual_chat(req.message)
    return ChatResponse(reply=reply)
