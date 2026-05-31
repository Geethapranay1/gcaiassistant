import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.llm_client import LLMClient
from app.parser import parse_llm_output, build_followup_response
from app.prompt import SYSTEM_PROMPT
from app.schemas import ProcessRequest, ProcessResponse, SlotRequest, SlotResponse
from app.slot_finder import find_common_slot, list_available_slots

load_dotenv()

llm: LLMClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global llm
    if os.getenv("GROQ_API_KEY"):
        llm = LLMClient()
    yield


app = FastAPI(title="Gmail Calendar Assistant", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/process", response_model=ProcessResponse)
def process_query(req: ProcessRequest):
    if not llm:
        return ProcessResponse(
            tool="draft_email",
            confidence=0.0,
            args={},
            missing_fields=["to", "body"],
            follow_up_question="LLM client is not configured. Set GROQ_API_KEY.",
        )
    raw = llm.call(SYSTEM_PROMPT, req.query)
    return parse_llm_output(raw, req.query)


@app.post("/followup", response_model=ProcessResponse)
def follow_up(previous: ProcessResponse, user_reply: str):
    return build_followup_response(previous, user_reply)


@app.post("/find-slot", response_model=SlotResponse)
def find_slot(req: SlotRequest):
    slot = find_common_slot(req.participants, req.duration_minutes)
    slots = list_available_slots(req.participants)
    return SlotResponse(selected_slot=slot, available_slots=slots)


@app.get("/health")
def health():
    return {"status": "ok", "llm_ready": llm is not None}
