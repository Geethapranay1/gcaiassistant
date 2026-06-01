import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.llm_client import LLMClient
from app.parser import parse_llm_output, build_followup_response
from app.prompt import SYSTEM_PROMPT
from app.schemas import ProcessRequest, ProcessResponse, SlotRequest, SlotResponse, Message
from app.slot_finder import find_common_slot, list_available_slots

load_dotenv()

llm: LLMClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global llm
    if os.getenv("GROQ_API_KEY"):
        llm = LLMClient()
    yield


from starlette.requests import Request
from starlette.responses import JSONResponse

app = FastAPI(title="Gmail Calendar Assistant", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )


@app.post("/process", response_model=ProcessResponse)
def process_query(req: ProcessRequest):
    if not llm:
        return ProcessResponse(
            tool="chat",
            confidence=0.0,
            args={},
            missing_fields=[],
            follow_up_question="LLM client is not configured. Set GROQ_API_KEY.",
        )
    raw = llm.call(SYSTEM_PROMPT, req.query, req.history)
    return parse_llm_output(raw, req.query, req.history)


class FollowUpRequest(BaseModel):
    previous: ProcessResponse
    previous_history: list[Message] = Field(default_factory=list)

@app.post("/followup", response_model=ProcessResponse)
def follow_up(req: FollowUpRequest, user_reply: str):
    if llm:
        prompt = f"{SYSTEM_PROMPT}\n\nThe user was trying to {req.previous.tool} but was missing {req.previous.missing_fields}. You asked: {req.previous.follow_up_question} \n\n Current arguments parsed so far: {req.previous.args}\n\nUpdate the parsed arguments based on their reply."
        try:
            raw = llm.call(prompt, user_reply, req.previous_history)
            
  
            merged_args = {**req.previous.args, **raw.get("args", {})}
            raw["args"] = merged_args
            raw["tool"] = req.previous.tool
            return parse_llm_output(raw, user_reply)
        except Exception:
            pass

    return build_followup_response(req.previous, user_reply)


@app.post("/find-slot", response_model=SlotResponse)
def find_slot(req: SlotRequest):
    slot = find_common_slot(req.participants, req.duration_minutes)
    slots = list_available_slots(req.participants)
    return SlotResponse(selected_slot=slot, available_slots=slots)


@app.get("/health")
def health():
    return {"status": "ok", "llm_ready": llm is not None}
