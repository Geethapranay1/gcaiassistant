import re
from datetime import datetime, timedelta
from typing import Any

from app.mock_data import MOCK_CONTACTS
from app.schemas import ProcessResponse
from app.slot_finder import find_common_slot, list_available_slots

REQUIRED_FIELDS = {
    "send_email": {"to", "body"},
    "draft_email": {"to", "body"},
    "schedule_meeting": {"participants", "duration_minutes", "date"},
    "chat": set(),
}

FOLLOW_UP_QUESTIONS = {
    "to": "Who should I send this email to?",
    "body": "What would you like the email to say?",
    "subject": "What subject should I use for this email?",
    "participants": "Who should be invited to the meeting?",
    "duration_minutes": "How long should the meeting be (in minutes)?",
    "date": "When should the meeting be scheduled?",
}

VAGUE_DATE_PATTERNS = [
    r"anytime",
    r"whenever",
    r"when.*(?:free|available|both)",
    r"any\s*(?:day|time|slot)",
    r"doesn.?t matter",
    r"no preference",
    r"find.*(?:slot|time)",
]

def extract_contacts(text):
    lowered = text.lower()
    return [c for c in MOCK_CONTACTS if c.lower() in lowered]

def get_confidence(tool, args):
    if tool == "chat":
        return 1.0
    reqs = REQUIRED_FIELDS.get(tool, set())
    if not reqs:
        return 0.5
    found = set(args.keys()) & reqs
    ratio = len(found) / len(reqs)
    return min(round(0.4 + (ratio * 0.55), 2), 0.95)

def is_vague_date(value):
    if not isinstance(value, str):
        return False
    for pat in VAGUE_DATE_PATTERNS:
        if re.search(pat, value, re.IGNORECASE):
            return True
    if len(value) > 30:
        return True
    return False

def extract_duration_from_text(text):
    m = re.search(r"(\d+(?:\.\d+)?)\s*(hours?|hrs?|minutes?|mins?)", text, re.IGNORECASE)
    if m:
        val = float(m.group(1))
        unit = m.group(2).lower()
        if unit.startswith("hour") or unit.startswith("hr"):
            return int(val * 60)
        return int(val)
    return None

def resolve_relative_date(text):
    today = datetime.now()
    lowered = text.lower().strip()
    if lowered == "today":
        return today.strftime("%Y-%m-%d")
    if lowered == "tomorrow":
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")
    days_map = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
                "friday": 4, "saturday": 5, "sunday": 6}
    m = re.match(r"next\s+(\w+)", lowered)
    if m:
        day_name = m.group(1)
        if day_name in days_map:
            target = days_map[day_name]
            current = today.weekday()
            diff = (target - current) % 7
            if diff == 0:
                diff = 7
            return (today + timedelta(days=diff)).strftime("%Y-%m-%d")
        if day_name == "week":
            return (today + timedelta(days=7)).strftime("%Y-%m-%d")
    return text  

def build_status_response(history):
    if not history:
        return None

    seen = set()
    actions = []
    for msg in history:
        content = msg.content if hasattr(msg, 'content') else msg.get('content', '')
        role = msg.role if hasattr(msg, 'role') else msg.get('role', '')
        if role != 'assistant':
            continue

  
        if content.startswith("Yes!") or content.startswith("Here's what"):
            continue


        lowered = content.lower()
        if 'scheduled a meeting' in lowered or 'i scheduled' in lowered:
            if content not in seen:
                seen.add(content)
                actions.append(('meeting', content))
        elif 'sent an email' in lowered or 'drafted an email' in lowered:
            if content not in seen:
                seen.add(content)
                actions.append(('email', content))

    if not actions:
        return None


    if len(actions) == 1:
        return f"Yes! {actions[0][1]}"

    parts = [detail for _, detail in actions]
    return "Here's what I've done so far:\n" + "\n".join(f"• {p}" for p in parts)


def parse_llm_output(raw: dict[str, Any], user_query: str, history: list = None) -> ProcessResponse:
    tool = raw.get("tool", "draft_email")

   
    if tool == "chat":
        is_status_q = re.search(
            r"(did (you|u)|have (you|u)|was .*(created|sent|scheduled|done)|when.*(meet|mail|email|scheduled)|what.*(subject|time|date))",
            user_query, re.IGNORECASE
        )
        if is_status_q and history:
            status_msg = build_status_response(history)
            if status_msg:
                return ProcessResponse(
                    tool="chat",
                    confidence=1.0,
                    args={},
                    missing_fields=[],
                    follow_up_question=status_msg,
                )

        msg = raw.get("follow_up_question") or "Hi! I can help you send emails, draft messages, or schedule meetings. What would you like to do?"
        return ProcessResponse(
            tool="chat",
            confidence=1.0,
            args={},
            missing_fields=[],
            follow_up_question=msg,
        )

    
    if re.match(r"^(hi+|hello|hey|yo)[!?. ]*$", user_query.strip(), re.IGNORECASE):
        fallback_msg = raw.get("follow_up_question") or "Hi! I can help you send emails, draft messages, or schedule meetings. What would you like to do?"
        return ProcessResponse(
            tool="chat",
            confidence=1.0,
            args={},
            missing_fields=[],
            follow_up_question=fallback_msg,
        )

   
    if re.search(r"^(did (you|u)|have (you|u)|was it|is it|are (you|u)|thanks|thank you)", user_query.strip(), re.IGNORECASE):
        if tool not in ("send_email", "draft_email", "schedule_meeting"):
            if history:
                status_msg = build_status_response(history)
                if status_msg:
                    return ProcessResponse(
                        tool="chat",
                        confidence=1.0,
                        args={},
                        missing_fields=[],
                        follow_up_question=status_msg,
                    )
            msg = raw.get("follow_up_question") or "I'm here to help! What would you like me to do?"
            return ProcessResponse(
                tool="chat",
                confidence=1.0,
                args={},
                missing_fields=[],
                follow_up_question=msg,
            )

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

    
        dur_from_text = extract_duration_from_text(user_query)
        if dur_from_text:
            args["duration_minutes"] = dur_from_text
        elif args.get("duration_minutes"):
      
            if re.search(r"hours?|hrs?", user_query, re.IGNORECASE) and args["duration_minutes"] < 60:
                args["duration_minutes"] = args["duration_minutes"] * 60

        if args.get("date") and is_vague_date(args["date"]):
            args.pop("date")
            args["find_available_slot"] = True
        if args.get("find_available_slot") or re.search(
            r"(anytime|whenever|when.*(?:free|available|both)|find.*(?:slot|time)|availability)",
            user_query, re.IGNORECASE
        ):
            participants = args.get("participants", [])
            dur = args.get("duration_minutes", 30)
            if participants:
                slot = find_common_slot(participants, dur)
                if slot:
                    args["selected_slot"] = slot
                    args["date"] = slot.split()[0]
                    args["time"] = slot.split()[1]
                    args.pop("find_available_slot", None)
                else:
                    available = list_available_slots(participants)
                    if available:
                        args["available_slots"] = available

        if args.get("date") and not re.match(r"\d{4}-\d{2}-\d{2}", args["date"]):
            args["date"] = resolve_relative_date(args["date"])

        if not args.get("date"):
            m = re.search(r"(tomorrow|next week|today|next \w+)", user_query, re.IGNORECASE)
            if m:
                args["date"] = resolve_relative_date(m.group(1))

        if not args.get("duration_minutes"):
            dur = extract_duration_from_text(user_query)
            if dur:
                args["duration_minutes"] = dur

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
                dur = extract_duration_from_text(user_reply)
                if dur:
                    args["duration_minutes"] = dur
                else:
                    m2 = re.search(r"(\d+)", user_reply)
                    if m2:
                        args["duration_minutes"] = int(m2.group(1))
            if not args.get("date"):
                if re.search(r"(anytime|whenever|when.*free|when.*available)", user_reply, re.IGNORECASE):
                    participants = args.get("participants", [])
                    dur = args.get("duration_minutes", 30)
                    slot = find_common_slot(participants, dur)
                    if slot:
                        args["selected_slot"] = slot
                        args["date"] = slot.split()[0]
                        args["time"] = slot.split()[1]
                else:
                    clean = re.sub(r"\d+\s*(minutes|minute|mins|min|hours|hour|hrs|hr)", "", user_reply, flags=re.IGNORECASE).strip()
                    if clean and clean != str(args.get("duration_minutes", "")):
                        args["date"] = resolve_relative_date(clean)

    reqs = REQUIRED_FIELDS.get(previous.tool, set())
    if previous.tool == "schedule_meeting" and "selected_slot" in args:
        reqs = reqs.copy()
        reqs.discard("date")
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
