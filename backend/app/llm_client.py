import json
import os

from openai import OpenAI


class LLMClient:
    def __init__(self):
        key = os.getenv("GROQ_API_KEY")
        if not key:
            raise RuntimeError("GROQ_API_KEY not set")
        self.client = OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")
        self.model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    def call(self, system_prompt: str, user_query: str) -> dict:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query},
                ],
                temperature=0.1,
                max_tokens=512,
                response_format={"type": "json_object"},
            )
            return json.loads(response.choices[0].message.content)
        except Exception:
            return {
                "tool": "draft_email",
                "confidence": 0.0,
                "args": {},
                "missing_fields": ["to", "body"],
                "follow_up_question": "I had trouble understanding that. Could you rephrase?",
            }
