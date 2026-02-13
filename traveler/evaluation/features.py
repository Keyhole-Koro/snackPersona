import random
from snackPersona.traveler.utils.data_models import ExecutionResult, FeatureDescriptors

def calculate_feature_descriptors(result: ExecutionResult) -> FeatureDescriptors:
    """
    Calculates the feature descriptors (niche coordinates) from execution results.

    """
    
    # Real metrics based on retrieved content
    
    # Authority: Analyze retrieved domains against a scored list
    authority_scores = {
        'ac.jp': 0.9, 'gov': 0.9, 'go.jp': 0.9, 
        'arxiv.org': 0.8, 'nature.com': 0.8,
        'nikkei.com': 0.7, 'reuters.com': 0.7, 'bbc.com': 0.7,
        'wikipedia.org': 0.5, 
        'qiita.com': 0.4, 'zenn.dev': 0.4, 'note.com': 0.3, 'hatenablog': 0.3
    }
    
    total_score = 0
    count = 0
    from urllib.parse import urlparse
    
    for url in result.retrieved_urls:
        try:
            domain = urlparse(url).netloc
            score = 0.5 # Default
            for key, val in authority_scores.items():
                if key in domain:
                    score = val
                    break
            total_score += score
            count += 1
        except:
            pass
    
    authority = (total_score / count) if count > 0 else 0.5

    # Concreteness: Heuristic based on average title length from content summary
    # Assumption: Longer titles often indicate more specific/concrete topics vs generic homepages
    titles = result.content_summary.get("pages", [])
    if titles:
        avg_len = sum(len(t) for t in titles) / len(titles)
        # Normalize: assume 50 chars is "very concrete" (1.0)
        concreteness = min(1.0, avg_len / 50.0)
    else:
        concreteness = 0.5

    return FeatureDescriptors(
        concreteness=concreteness,
        authority=authority,
    )
