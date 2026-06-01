# Gmail + Calendar AI Assistant

A mini AI assistant that converts natural language requests into structured JSON actions for Gmail and Calendar

It uses FastAPI for the backend, React for the frontend shadcn for UI, and Groq (Llama 3) for the AI model

## Screenshots of frontend chat
![chats](image-1.png)
![alt text](image-2.png)

## Architecture
![architecture](image.png)

## Features
- Understands intents: `send_email`, `draft_email`, `schedule_meeting`, `chat`.
- Extracts entities (names, times, durations).
- Auto-finds available time slots when user says "anytime we're both free".
- Detects missing info and asks a follow-up question.
- Maintains conversation context across messages.
- Answers status questions like "did you create a meet?" with actual details from history.
- Small web UI to chat and view the JSON output.

## Setup

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Add your Groq API key to `.env`:
```
GROQ_API_KEY=your_key_here
```

Run the server:
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```
Then open http://localhost:5173

## Tests
```bash
cd backend
pytest -v
```

## System Prompt

```
You are an AI assistant that converts natural language into structured JSON for email and calendar actions.

You will receive conversation history as prior messages. ALWAYS use this history to maintain context.
If the user asks about something you previously did (e.g., "did you create a meet?", "was the email sent?"),
refer to the conversation history and answer accurately.

Identify user intent as one of: send_email, draft_email, schedule_meeting, or chat.
Extract all relevant parameters and detect missing required info.
If something is missing, ask exactly one follow-up question.

Tools:

send_email:
  Required: to (list of names), body (email content)
  Optional: subject. If not given, infer a short one from context.

draft_email:
  Required: to (list of names), body (email content)
  Optional: subject. If not given, infer a short one from context.

schedule_meeting:
  Required: participants (list of names), duration_minutes (int), date (YYYY-MM-DD or relative like "tomorrow", "next Monday")
  Optional: time_preference (morning/afternoon/evening), find_available_slot (boolean)

chat:
  Use for greetings, status questions, casual conversation, or anything not related to emails/meetings.
  Required: none. Put your conversational response in follow_up_question.

Known contacts: Rahul, Priya, John, Meera, Design Team, Engineering Managers.

Rules:
- Do NOT hallucinate values. If user didn't mention a field, leave it out of args and put it in missing_fields.
- For emails: if body is missing, mark it missing. Subject can be inferred if context is clear.
- For meetings:
  - duration_minutes MUST always be in minutes. If user says "2 hours", set duration_minutes to 120.
  - date must be a specific date or relative expression. Do NOT put vague phrases like "anytime" in the date field.
  - If the user says "anytime" or "whenever we are free", do NOT set a date. Instead mark date as missing and set find_available_slot to true in args.
- Map names to closest available contact.
- confidence is 0.0 to 1.0. Higher when all required fields are present.
- follow_up_question: one concise question, or null if nothing missing.
- missing_fields: only list REQUIRED fields that are absent.
- For greetings, casual chats, status questions: set tool to "chat", confidence to 1.0, use empty args and empty missing_fields, and put your conversational response in the follow_up_question field.
- Return ONLY valid JSON.

Output format:
{
  "tool": "send_email | draft_email | schedule_meeting | chat",
  "confidence": 0.0,
  "args": {},
  "missing_fields": [],
  "follow_up_question": null
}
```

## Example Inputs and Outputs

### 1. Complete email request

Input: `Send an email to Rahul saying I will be late tomorrow`

Output:
```json
{
  "tool": "send_email",
  "confidence": 0.95,
  "args": {
    "to": [
      "Rahul"
    ],
    "body": "I will be late tomorrow"
  },
  "missing_fields": [],
  "follow_up_question": null
}
```

### 2. Draft email with topic

Input: `Draft an email to the design team about Friday's release`

Output:
```json
{
  "tool": "draft_email",
  "confidence": 0.95,
  "args": {
    "to": [
      "Design Team"
    ],
    "body": "about Friday's release"
  },
  "missing_fields": [],
  "follow_up_question": null
}
```

### 3. Complete meeting request

Input: `Schedule a 45 minute meeting with Rahul and Priya next Tuesday afternoon`

Output:
```json
{
  "tool": "schedule_meeting",
  "confidence": 0.95,
  "args": {
    "participants": [
      "Rahul",
      "Priya"
    ],
    "duration_minutes": 45,
    "time_preference": "afternoon",
    "date": "next Tuesday"
  },
  "missing_fields": [],
  "follow_up_question": null
}
```

### 4. Missing date and duration

Input: `Schedule a meeting with Rahul`

Output:
```json
{
  "tool": "schedule_meeting",
  "confidence": 0.58,
  "args": {
    "participants": [
      "Rahul"
    ]
  },
  "missing_fields": [
    "duration_minutes",
    "date"
  ],
  "follow_up_question": "How long should the meeting be (in minutes)?"
}
```

### 5. Meeting with auto slot finding

Input: `Schedule a 2 hour meeting with Rahul anytime when we're both free`

Output:
```json
{
  "tool": "schedule_meeting",
  "confidence": 0.95,
  "args": {
    "participants": [
      "Rahul"
    ],
    "duration_minutes": 120,
    "selected_slot": "2026-06-02 11:00",
    "date": "2026-06-02",
    "time": "11:00"
  },
  "missing_fields": [],
  "follow_up_question": null
}
```

### 6. Missing email body

Input: `Send an email to Priya`

Output:
```json
{
  "tool": "send_email",
  "confidence": 0.68,
  "args": {
    "to": [
      "Priya"
    ]
  },
  "missing_fields": [
    "body"
  ],
  "follow_up_question": "What would you like the email to say?"
}
```

### 7. Send follow-up

Input: `Send a follow-up to John about the pending invoice`

Output:
```json
{
  "tool": "send_email",
  "confidence": 0.95,
  "args": {
    "to": [
      "John"
    ],
    "body": "about the pending invoice",
    "subject": "Follow-up on Pending Invoice"
  },
  "missing_fields": [],
  "follow_up_question": null
}
```

### 8. Calendar event with time

Input: `Create a calendar event with Priya and Meera tomorrow at 4 PM`

Output:
```json
{
  "tool": "schedule_meeting",
  "confidence": 0.77,
  "args": {
    "participants": [
      "Priya",
      "Meera"
    ],
    "date": "tomorrow",
    "time_preference": "afternoon"
  },
  "missing_fields": [
    "duration_minutes"
  ],
  "follow_up_question": "How long should the meeting be (in minutes)?"
}
```

### 9. Group email

Input: `Draft an email to all engineering managers about the production issue`

Output:
```json
{
  "tool": "draft_email",
  "confidence": 0.68,
  "args": {
    "to": [
      "Engineering Managers"
    ],
    "subject": "Production Issue"
  },
  "missing_fields": [
    "body"
  ],
  "follow_up_question": "What would you like the email to say?"
}
```

### 10. Greeting

Input: `hi`

Output:
```json
{
  "tool": "chat",
  "confidence": 1.0,
  "args": {},
  "missing_fields": [],
  "follow_up_question": "Hi! I can help you send emails, draft messages, or schedule meetings. What would you like to do?"
}
```

### 11. Status question with context

Input: `did you create a meet?` (after scheduling a meeting with Rahul)

Output:
```json
{
  "tool": "chat",
  "confidence": 1.0,
  "args": {},
  "missing_fields": [],
  "follow_up_question": "Yes! I scheduled a meeting with Rahul for 120 minutes on 2026-06-02 at 11:00."
}
```

### 12. Slot finder endpoint

Input (via `POST /find-slot`):
```json
{
  "participants": ["Rahul", "Priya"],
  "duration_minutes": 30
}
```

Output:
```json
{
  "selected_slot": "2026-06-02 15:00",
  "available_slots": ["2026-06-02 15:00"]
}
```

## Conversation Flow Example

```
User: can u schedule a meet between me and rahul
Bot:  → schedule_meeting (0.58 confidence), missing: duration_minutes, date
      "How long should the meeting be?"

User: 2 hours anytime when we both are available
Bot:  → schedule_meeting (0.95 confidence)
      duration_minutes: 120, date: 2026-06-02, time: 11:00
      (auto-found common free slot from mock calendar)

User: did u create a meet?
Bot:  "Yes! I scheduled a meeting with Rahul for 120 minutes on 2026-06-02 at 11:00."

User: at what time?
Bot:  "Yes! I scheduled a meeting with Rahul for 120 minutes on 2026-06-02 at 11:00."

User: email to priya
Bot:  → send_email (0.68 confidence), missing: body
      "What would you like the email to say?"

User: this is urgent
Bot:  → send_email (0.95 confidence), to: Priya, body: "this is urgent"

User: did u send mail?
Bot:  "Yes! I sent an email to Priya saying "this is urgent"."
```

## Assumptions

- No real Gmail/Calendar APIs, everything is mocked with JSON since the assignment said that's fine
- Contacts and calendar slots are hardcoded lists in `mock_data.py`
- If the LLM returns garbage or an unknown tool name, the parser falls back to `draft_email` instead of crashing
- I don't fill in default durations or dates on the first request, if the user didn't say it, we ask them
- Confidence is calculated on the backend based on how many required fields are present, instead of trusting whatever number the LLM gives back
- Greetings and status questions use the `chat` tool which renders as a text bubble instead of a JSON card
- Status responses ("did you create a meet?") are built from conversation history at the parser level for accuracy, since the LLM tends to hedge on specifics
- Duration conversion (hours to minutes) is enforced both in the prompt and in the parser as a safety net
- When user says "anytime", the slot finder automatically checks mock calendar data for common free slots
- Chats are saved to localStorage so they don't disappear on refresh
