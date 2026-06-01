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

    def call(self, system_prompt: str, user_query: str, history: list = None) -> dict:
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            for msg in history:
                if isinstance(msg, dict):
                    messages.append({"role": msg["role"], "content": msg["content"]})
                else:
                    messages.append({"role": msg.role, "content": msg.content})
        
        messages.append({"role": "user", "content": user_query})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1,
                max_tokens=512,
                response_format={"type": "json_object"},
            )
            return json.loads(response.choices[0].message.content)
        except Exception:
            return {
                "tool": "chat",
                "confidence": 1.0,
                "args": {},
                "missing_fields": [],
                "follow_up_question": "I had trouble understanding that. Could you rephrase?",
            }
