import re
from typing import Any

from app.mock_data import MOCK_CONTACTS
from app.schemas import ProcessResponse
from app.slot_finder import find_common_slot

REQUIRED_FIELDS = {
    "send_email": {"to", "body"},
    "draft_email": {"to", "body"},
    "schedule_meeting": {"participants", "duration_minutes", "date"},
}

FOLLOW_UP_QUESTIONS = {
    "to": "Who should I send this email to?",
    "body": "What would you like the email to say?",
    "subject": "What subject should I use for this email?",
    "participants": "Who should be invited to the meeting?",
    "duration_minutes": "How long should the meeting be (in minutes)?",
    "date": "When should the meeting be scheduled?",
}

def extract_contacts(text):
    lowered = text.lower()
    return [c for c in MOCK_CONTACTS if c.lower() in lowered]

def get_confidence(tool, args):
    reqs = REQUIRED_FIELDS.get(tool, set())
    if not reqs:
        return 0.5
    found = set(args.keys()) & reqs
    ratio = len(found) / len(reqs)
    return min(round(0.4 + (ratio * 0.55), 2), 0.95)

def parse_llm_output(raw: dict[str, Any], user_query: str) -> ProcessResponse:
    if re.match(r"^(hi+|hello|hey|yo)[!?. ]*$", user_query.strip(), re.IGNORECASE):
        return ProcessResponse(
            tool="draft_email",
            confidence=0.0,
            args={},
            missing_fields=["to", "body"],
            follow_up_question="Hi! I can help you send emails, draft messages, or schedule meetings. What would you like to do?",
        )

    tool = raw.get("tool")
    if tool not in ("send_email", "draft_email", "schedule_meeting"):
        tool = "draft_email"

    args = raw.get("args", {})
    if not isinstance(args, dict):
        args = {}

    if "time_range" in args and "date" not in args:
        args["date"] = args.pop("time_range")
    if "time" in args and "date" not in args:
        args["date"] = args.pop("time")

    if tool == "schedule_meeting":
        if not args.get("participants"):
            contacts = extract_contacts(user_query)
            if contacts:
                args["participants"] = contacts

        if re.search(r"(find|search|look for).*(slot|time)|free", user_query, re.IGNORECASE):
            if "selected_slot" not in args:
                dur = args.get("duration_minutes", 30)
                slot = find_common_slot(args.get("participants", []), dur)
                if slot:
                    args["selected_slot"] = slot
                    args.pop("date", None)

        if not args.get("date"):
            m = re.search(r"(tomorrow|next week|today|next \w+)", user_query, re.IGNORECASE)
            if m:
                args["date"] = m.group(1)

        if not args.get("duration_minutes"):
            m = re.search(r"(\d+)\s*(min|minute|hour|hr)", user_query, re.IGNORECASE)
            if m:
                val = int(m.group(1))
                if m.group(2).lower() in ("hour", "hr"):
                    val *= 60
                args["duration_minutes"] = val

    reqs = REQUIRED_FIELDS.get(tool, set()).copy()
    if tool == "schedule_meeting" and "selected_slot" in args:
        reqs.discard("date")
    missing = list(reqs - set(args.keys()))

    question = None
    if missing:
        question = FOLLOW_UP_QUESTIONS.get(missing[0], f"Could you provide the missing {missing[0]}?")

    return ProcessResponse(
        tool=tool,
        confidence=get_confidence(tool, args),
        args=args,
        missing_fields=missing,
        follow_up_question=question,
    )

def build_followup_response(previous: ProcessResponse, user_reply: str) -> ProcessResponse:
    if not previous.missing_fields:
        return previous

    args = dict(previous.args)
    target = previous.missing_fields[0]

    if previous.tool in ("send_email", "draft_email"):
        if target == "to":
            c = extract_contacts(user_reply)
            args["to"] = c if c else [user_reply.strip()]
        else:
            args[target] = user_reply.strip()

    elif previous.tool == "schedule_meeting":
        if target == "participants":
            c = extract_contacts(user_reply)
            args["participants"] = c if c else [p.strip() for p in user_reply.split(",") if p.strip()]
        elif target in ("duration_minutes", "date"):
            if not args.get("duration_minutes"):
                m = re.search(r"(\d+)", user_reply)
                if m: args["duration_minutes"] = int(m.group(1))
            if not args.get("date"):
                clean = re.sub(r"\d+\s*(minutes|minute|mins|min|hours|hour|hrs|hr)", "", user_reply, flags=re.IGNORECASE).strip()
                if clean and clean != str(args.get("duration_minutes", "")):
                    args["date"] = clean

    reqs = REQUIRED_FIELDS.get(previous.tool, set())
    new_missing = [r for r in reqs if not args.get(r)]

    question = None
    if new_missing:
        question = FOLLOW_UP_QUESTIONS.get(new_missing[0], f"Could you provide the missing {new_missing[0]}?")

    return ProcessResponse(
        tool=previous.tool,
        confidence=get_confidence(previous.tool, args),
        args=args,
        missing_fields=new_missing,
        follow_up_question=question,
    )
