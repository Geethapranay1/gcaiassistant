from app.parser import parse_llm_output, build_followup_response
from app.schemas import ProcessResponse


def test_send_email_complete():
    raw = {
        "tool": "send_email",
        "args": {
            "to": ["Rahul"],
            "subject": "Regarding tomorrow",
            "body": "I will be late tomorrow",
        },
    }
    result = parse_llm_output(raw, "Send an email to Rahul saying I will be late tomorrow")
    assert result.tool == "send_email"
    assert result.missing_fields == []
    assert result.follow_up_question is None
    assert result.confidence > 0.8


def test_schedule_meeting_missing_fields():
    raw = {
        "tool": "schedule_meeting",
        "args": {"participants": ["Rahul"]},
    }
    result = parse_llm_output(raw, "Schedule a meeting with Rahul")
    assert result.tool == "schedule_meeting"
    assert "duration_minutes" in result.missing_fields
    assert "date" in result.missing_fields
    assert result.follow_up_question is not None
    assert result.confidence < 0.8


def test_send_email_missing_body():
    raw = {"tool": "send_email", "args": {"to": ["Priya"]}}
    result = parse_llm_output(raw, "Send an email to Priya")
    assert result.tool == "send_email"
    assert "body" in result.missing_fields
    assert result.follow_up_question is not None


def test_draft_email_generates_subject():
    raw = {
        "tool": "draft_email",
        "args": {
            "to": ["Design Team"],
            "subject": "Friday Release",
            "body": "The release is delayed till Friday.",
        },
    }
    result = parse_llm_output(raw, "Draft an email to the design team about Friday's release")
    assert result.tool == "draft_email"
    assert "Design Team" in result.args["to"]
    assert result.missing_fields == []


def test_followup_provides_body():
    prev = ProcessResponse(
        tool="send_email",
        confidence=0.6,
        args={"to": ["Priya"]},
        missing_fields=["body"],
        follow_up_question="What would you like the email to say?",
    )
    result = build_followup_response(prev, "Please review the attached document")
    assert result.args["body"] == "Please review the attached document"
    assert result.missing_fields == []
    assert result.follow_up_question is None


def test_followup_provides_duration():
    prev = ProcessResponse(
        tool="schedule_meeting",
        confidence=0.5,
        args={"participants": ["Rahul"]},
        missing_fields=["duration_minutes", "date"],
        follow_up_question="How long and when?",
    )
    result = build_followup_response(prev, "45 minutes next Tuesday")
    assert result.args["duration_minutes"] == 45
    assert result.args["date"] == "next Tuesday"
    assert result.missing_fields == []


def test_invalid_tool_fallback():
    raw = {"tool": "unknown_tool", "args": {}}
    result = parse_llm_output(raw, "Do something weird")
    assert result.tool == "draft_email"


def test_schedule_meeting_full():
    raw = {
        "tool": "schedule_meeting",
        "args": {
            "participants": ["Rahul", "Priya"],
            "duration_minutes": 45,
            "date": "next Tuesday",
            "time_preference": "afternoon",
        },
    }
    result = parse_llm_output(raw, "Schedule a 45 minute meeting with Rahul and Priya next Tuesday afternoon")
    assert result.tool == "schedule_meeting"
    assert result.missing_fields == []
    assert result.follow_up_question is None
    assert result.confidence > 0.85
