# backend/agents/citation_chainer.py
import openai
import os

from dotenv import load_dotenv
load_dotenv()

oai_key = os.getenv('OPENAI_API_KEY')
if not oai_key:
    raise ValueError("OPENAI_API_KEY environment variable not set")
openai.api_key = oai_key


def generate_apa_citation(info: dict) -> str:
    """
    Uses OpenAI to create an APA citation for a doctoral dissertation.
    Expects info dict with keys:
      - author: str
      - year: str or int
      - title: str
      - publication_number: str
      - institution: str
      - publisher: str
    """
    prompt = (
        "You are an expert in APA formatting. Create an APA citation for a doctoral dissertation "
        "using the following information:\n"
        f"Author: {info.get('author')}\n"
        f"Year: {info.get('year')}\n"
        f"Title: {info.get('title')}\n"
        f"Publication Number: {info.get('publication_number')}\n"
        f"Institution: {info.get('institution')}\n"
        f"Publisher: {info.get('publisher')}\n\n"
        "Format it exactly like official APA style."

        "If there is no details, give an empty string"

        "Only give the response,Don't give any extra information."

        "Example citation if details present:"

        "McNiel, D.S. (2006). Meaning through narrative: A personal narrative discussing growing up with an alcoholic mother (Publication No. 1434728) [Doctoral dissertation, University of Chicago]. ProQuest Dissertations and Theses database."

        "if any details not present replace them with ''"
    )
    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    citation = response.choices[0].message.content.strip()
    return citation


def generate_bluebook_citation(info: dict) -> str:
    """
    Uses OpenAI to create a Bluebook citation for a case.
    Expects info dict with keys:
      - case_name: str
      - source: str
      - page_number: str or int
      - congress: str
      - session: str
      - court_year: str or int
    """
    prompt = (
        "You are a legal writing assistant. Create a Bluebook citation using this information:\n"
        f"Case Name: {info.get('case_name')}\n"
        f"Source: {info.get('source')}\n"
        f"Page Number: {info.get('page_number')}\n"
        f"Congress: {info.get('congress')}\n"
        f"Session: {info.get('session')}\n"
        f"Court Year: {info.get('court_year')}\n\n"
        "Follow Bluebook format precisely."

         "If there is no details, give an empty string"

        "Only give the response,Don't give any extra information."

        "Example citation if details present:"

        "Perry Mason & Julius R. Windsor, Criminal Court Management in Utah, 13 Legm. C.L. & Criminal. 22 (2008)."

        "if any details not present replace them with ''"
    )
    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    citation = response.choices[0].message.content.strip()
    return citation


def format_citation(source: dict, style: str = "APA") -> str:
    """
    Determines which citation generator to invoke based on style.
    For APA dissertations, expects source['citation_info'] dict with APA fields.
    For Bluebook cases, expects source['citation_info'] dict with Bluebook fields.

    Example source structure:
      source['citation_info'] = {
          'author': 'McNiel, D.S.',
          'year': '2006',
          'title': 'Meaning through narrative:...',
          'publication_number': '1434728',
          'institution': 'University of Chicago',
          'publisher': 'ProQuest Dissertations...'
      }
    or
      source['citation_info'] = {
          'case_name': 'Minors Dream Aliens Protection Act',
          'source': 'C.S.',
          'page_number': '1711',
          'congress': '119th Cong.',
          'session': '§ 2',
          'court_year': '2012'
      }
    """
    info = source.get('citation_info', {})
    if style.upper() == 'APA':
        return generate_apa_citation(info)
    elif style.upper() == 'BLUEBOOK':
        return generate_bluebook_citation(info)
    else:
        raise ValueError(f"Unsupported citation style: {style}")

