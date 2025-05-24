# backend/agents/keyword_generator.py
import openai
import os
from dotenv import load_dotenv
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
def generate_keywords(angle, arguments):
    """
    Generate search keywords based on the research angle and extracted arguments.
    """
    prompt = (
        f"You are a legal research assistant. Given the new research angle:\n\n\"{angle}\"\n\n"
        f"and the following extracted arguments:\n{arguments}\n\n"
        "Suggest 5 concise keywords or phrases that would help find relevant legal papers."
    )
    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    keywords = [kw.strip() for kw in response.choices[0].message.content.split(',')]
    print(keywords)
    return keywords
