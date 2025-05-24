import requests
from bs4 import BeautifulSoup
import re
import json
import os
import openai

# app = Flask(__name__)

# Load your OpenAI API key (ensure to set the environment variable before running)
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise EnvironmentError("Please set the OPENAI_API_KEY environment variable")

def scrape_article_content(url):
    """
    Scrape the article page at the given URL and extract key pieces of information:
    - Title of the article
    - Author line (which includes author(s) and affiliation)
    - ISSN (if present)
    - Content text (e.g., the abstract or main body)
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Failed to fetch URL: {e}")

    soup = BeautifulSoup(resp.text, 'html.parser')

    # Extract the article title
    title_tag = soup.find('h1')
    title = title_tag.get_text(strip=True) if title_tag else ""
    if not title:
        # Fallback: sometimes the title might be in <title>
        title_tag = soup.find('title')
        title = title_tag.get_text(strip=True) if title_tag else ""
    
    # Extract the author line (with institution). We look for a paragraph with commas and likely an affiliation keyword
    author_line = ""
    for p in soup.find_all('p'):
        text = p.get_text()
        # Look for patterns like "Name, Institution" or "Name & Name, Institution"
        if ',' in text and re.search(r'School|University|College|Institute|Ltd', text):
            author_line = text.strip()
            break

    # Extract ISSN using regex search in the entire text
    issn = ""
    issn_match = re.search(r'ISSN\s*[:\-]\s*([\dXx-]+)', resp.text)
    if issn_match:
        issn = issn_match.group(1).strip()

    # Extract the main content (e.g., abstract). Look for an "ABSTRACT" heading and get following <p> tags
    content_text = ""
    abstract_heading = soup.find(lambda tag: tag.name in ['p', 'div', 'strong'] and tag.get_text(strip=True).upper() == "ABSTRACT")
    if abstract_heading:
        # Collect all the paragraph siblings after the "ABSTRACT" heading
        abstract_paras = []
        next_tag = abstract_heading.find_next_sibling()
        while next_tag and next_tag.name == 'p':
            para_text = next_tag.get_text().strip()
            if para_text:
                abstract_paras.append(para_text)
            next_tag = next_tag.find_next_sibling()
        content_text = " ".join(abstract_paras)
    else:
        # Fallback: concatenate all <p> tags (this may include authors, headings etc., but as a last resort)
        paras = [p.get_text().strip() for p in soup.find_all('p') if p.get_text().strip()]
        content_text = " ".join(paras)

    # Return a dictionary of the scraped pieces
    return {
        "title": title,
        "author_line": author_line,
        "issn": issn,
        "content": content_text
    }

def extract_with_gpt(scraped_data):
    """
    Given scraped data (title, author_line, content), use GPT-4 to summarize and extract structured fields.
    """
    title = scraped_data.get("title", "")
    author_line = scraped_data.get("author_line", "")
    content = scraped_data.get("content", "")
    
    # Prepare prompt for GPT
    prompt = (
        f"Article Title: {title}\n"
        f"Authors/Affiliation: {author_line}\n\n"
        f"Content:\n{content}\n\n"
        "Please perform the following:\n"
        "1. Write a concise summary of the article content.\n"
        "2. Extract the ISSN number.\n"
        "3. Confirm the article title.\n"
        "4. Extract the full name of the first author.\n"
        "5. Extract the year of publication.\n"
        "6. Provide the first and last name initials of the first author.\n"
        "7. Extract the institution/affiliation of the first author.\n\n"
        "Return the result as a JSON object with the keys: summary, issn, title, author_full_name, year, author_initials, author_institution.\n"
        "Only output valid JSON (no additional text)."
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
    except Exception as e:
        raise RuntimeError(f"OpenAI API request failed: {e}")
    
    # Extract and parse the JSON from GPT's response
    reply = response.choices[0].message.content.strip()
    try:
        data = json.loads(reply)
    except json.JSONDecodeError:
        raise ValueError(f"GPT response is not valid JSON: {reply}")
    
    return data

# @app.route('/extract', methods=['POST'])
def extract_route(url):
    """
    API endpoint that accepts a JSON payload with a 'url' key.
    It scrapes the page at the URL, processes it with GPT, and returns extracted data in JSON.
    """

    try:
        scraped = scrape_article_content(url)
        # if not scraped["title"] or not scraped["author_line"]:
        #     return jsonify({"error": "Could not find title or author information on the page."}), 422

        # Use GPT to extract structured data
        extracted = extract_with_gpt(scraped)

    except Exception as e:
        # Catch and report errors (bad URL, scraping errors, GPT errors, etc.)
        return e

    print(extracted)
    return extracted
