# # backend/app.py
# from flask import Flask, request, jsonify
# from agents.argument_extractor import extract_arguments
# from agents.keyword_generator import generate_keywords
# from agents.source_searcher import search_scholar, search_indiankanoon
# from agents.relevance_scorer import score_relevance
# from agents.citation_chainer import format_citation
# from agents.summary_formatter import summarize_source
# from flask import Flask
# from flask_cors import CORS

# app = Flask(__name__)
# CORS(app) 


# @app.route('/api/analyze', methods=['POST'])
# def analyze_research_paper():
#     """
#     Handle submission of a base paper (PDF or URL) and a new research angle.
#     Coordinates the agent modules to produce a research brief.
#     """
#     data = request.json
#     base_url = data.get('url')
#     base_pdf = data.get('pdf_text')
#     angle = data.get('angle')
#     user_keywords = data.get('keywords', [])

#     # 1. Extract arguments from the base paper (using OCR or summarization).
#     #    Here we assume 'base_pdf' contains extracted text if a PDF was uploaded.
#     arguments = extract_arguments(base_pdf or base_url)
    
#     # 2. Generate search keywords (if not provided) from the angle + arguments.
#     keywords = user_keywords or generate_keywords(angle, arguments)
    
#     # 3. Simulated search for sources.
#     scholar_results = search_scholar(keywords)
#     kanoon_results = search_indiankanoon(keywords)
#     all_sources = scholar_results + kanoon_results
    
#     # 4. Score relevance for each source against the angle.
#     for source in all_sources:
#         source['score'] = score_relevance(source, angle, keywords)

#     # Sort sources by relevance score (descending).
#     sorted_sources = sorted(all_sources, key=lambda s: s['score'], reverse=True)
    
#     # 5. Format citations for each source (e.g., APA or MLA style).
#     for source in sorted_sources:
#         source['citation'] = format_citation(source, style=data.get('citation_style', 'APA'))

#     # 6. Summarize each source's content/snippet.
#     for source in sorted_sources:
#         source['summary'] = summarize_source(source['snippet'])

#     # Return JSON response with ranked sources.
#     return jsonify({
#         'sources': sorted_sources,
#         'angle': angle,
#         'keywords': keywords,
#         'arguments': arguments
#     })

# if __name__ == '__main__':
#     app.run(debug=True)



# backend/app.py
import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import openai
from flask import Flask
from flask_cors import CORS

app = Flask(__name__)
CORS(app) 

# Load environment
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

# from agents.argument_extractor import extract_arguments
from agents.keyword_generator import generate_keywords
# from agents.source_searcher import search_scholar, search_indiankanoon
# from agents.relevance_scorer import score_relevance
# from agents.citation_chainer import format_citation
# from agents.summary_formatter import summarize_source
from agents.new_argument_extractor import main_function
from agents.new_relevance_scorer import main_function_for_relevance
# from agents.citations_data_extractor import extract_route

# app = Flask(__name__)

@app.route('/api/analyze', methods=['POST'])
def analyze_research_paper():
    """
    Handle submission of a base paper (PDF or URL) and a new research angle.
    Coordinates the agent modules to produce a research brief.
    """
    data = request.json
    base_url = data.get('url')
    base_pdf = data.get('pdf_text')
    angle = data.get('angle')
    user_keywords = data.get('keywords', [])
    citation_style = data.get('citation_style', 'APA')

    if(base_pdf):
        arguments=main_function(base_pdf,True)
    else:
        arguments=main_function(base_url,False)

    generated_keywords = generate_keywords(angle,arguments)
    keywords = user_keywords + generated_keywords
    print(keywords)
    sources = []
    for keyword in keywords:
        sources = sources + main_function_for_relevance(keyword)

    urls=[]
    source={}
    for item in sources:
        url=item[0]
        # extracted_text=extract_route(url)
        # print(extracted_text)
        urls.append(url)
        source['link']=item[0]
        source['title']=item[0].split("post/")[1]
        source['score']=item[2]
        source['summary']=item[1]

    
    # sorted_sources = sorted(all_sources, key=lambda s: s['score'], reverse=True)

    # # 5. Format citations and summaries
    # for source in sorted_sources:
    #     try:
    #         source['citation'] = format_citation(source, style=citation_style)
    #     except Exception:
    #         source['citation'] = ''
    #     source['summary'] = summarize_source(source.get('snippet', ''))

    return jsonify({
        'sources': source,
        'angle': angle,
        'keywords': keywords,
        'arguments': arguments
    })

if __name__ == '__main__':
    app.run(debug=True)

