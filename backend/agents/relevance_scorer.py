# backend/agents/relevance_scorer.py

def score_relevance(source, angle, keywords):
    """
    Score how relevant a source is to the research angle.
    Simple implementation: count keyword matches in title/snippet.
    """
    text = (source.get('title','') + " " + source.get('snippet','')).lower()
    if(keywords!=None and len(keywords)!=0):
        score = sum(text.count(kw.lower()) for kw in keywords)
    # Normalize to a 0-1 range (assuming at most 10 matches for scaling).
        return min(score / 10.0, 1.0)
    else:
        return 0
