import os
from openai import OpenAI


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-default-api-key")
MODEL = os.getenv("MODEL", "gpt-4")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "your-default-api-key"))
MODEL = os.getenv("MODEL", "gpt-4")

def call_llm(system_prompt, message, kwarg1=None) -> str:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content or ""