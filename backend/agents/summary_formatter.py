# backend/agents/summary_formatter.py
import openai
import os
from dotenv import load_dotenv
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
def summarize_source(text_snippet):
    """
    Summarize a text snippet into a short explanation.
    """
    prompt = f"Summarize the following passage in 2-3 sentences:\n\n\"{text_snippet}\""
    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()
