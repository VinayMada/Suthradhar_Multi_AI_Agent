# backend/agents/argument_extractor.py
import openai
import os
from dotenv import load_dotenv
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")


def extract_arguments(text_or_url):
    """
    Extract key legal arguments or points from the given text.
    Uses OpenAI's ChatCompletion API to summarize or highlight arguments.
    """
    # For simplicity, assume 'text_or_url' is plain text of the document.
    prompt = f"Extract the main legal arguments or issues from the following text:\n\n{text_or_url}"
    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    # Expecting a structured list in the response.
    arguments = response.choices[0].message.content.strip().split('\n')
    return arguments
