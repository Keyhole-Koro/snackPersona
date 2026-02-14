import random
import time
from typing import List, Dict
from snackPersona.utils.logger import logger

from snackPersona.traveler.utils.data_models import TravelerGenome, ExecutionResult
from snackPersona.traveler.executor.browser import SearchClient, WebCrawler
from snackPersona.traveler.utils.source_memory import SourceMemory


class Traveler:
    """
    Real web traveler executor using a hybrid strategy (Search + Crawl).
    """
    def __init__(self, genome: TravelerGenome, memory: SourceMemory = None, global_domain_counts: Dict[str, int] = None):
        self.genome = genome
        self.global_domain_counts = global_domain_counts or {}
        
        # Try SerpApi first, fall back to scraping
        from snackPersona.traveler.executor.browser import SerpApiClient
        self.serp_client = SerpApiClient()
        if self.serp_client.api_key:
            self.search_client = self.serp_client
        else:
            self.search_client = SearchClient(num_results=5)
            
        self.crawler = WebCrawler(timeout=10)
        self.memory = memory

    def execute(self) -> ExecutionResult:
        """
        Executes the hybrid exploration strategy.
        1. Generate query (simple template for now)
        2. Perform seed search
        3. Crawl/Deep dive based on genome parameters
        """
        start_time = time.time()
        
        # 1. Generate Query
        query = self._generate_query()
        
        # 2. Seed Search
        seed_urls = self.search_client.search(query)
        
        # 3. Hybrid Selection & Crawling
        # Initial depth 0
        visited_urls = []
        retrieved_content = []
        
        # Priority queue or simple list to explore
        # Format: (url, depth, score)
        to_visit = [(url, 0) for url in seed_urls]
        
        # Limit total visits to avoid infinite loops
        max_visits = 5 + (self.genome.search_depth * 3)
        visit_count = 0
        
        while to_visit and visit_count < max_visits:
            # Simple heuristic: Pop random or based on score?
            # For now, popping first (BFS-ish) but we can sort by genome bias
            # Let's sort to_visit based on genome bias before popping
            to_visit.sort(key=lambda x: self._score_url(x[0]), reverse=True)
            
            url, depth = to_visit.pop(0)
            
            if url in visited_urls:
                continue
            
            # Fetch
            page_data = self.crawler.fetch_page(url)
            if not page_data:
                continue
            
            visited_urls.append(url)
            visit_count += 1
            retrieved_content.append(page_data)
            
            # Expand if depth allows
            if depth < self.genome.search_depth:
                # Extract links and add to queue
                new_links = page_data.get("links", [])
                
                # Filter/Score new links
                # If novelty_weight is high, prefer external domains or less common ones
                random.shuffle(new_links) # Shuffle to avoid just following menu links
                
                for link in new_links[:5]: # Add top 5 links to avoid explosion
                    if link not in visited_urls:
                        to_visit.append((link, depth + 1))

        # Record visited domains in source memory
        if self.memory:
            from urllib.parse import urlparse
            for page in retrieved_content:
                try:
                    domain = urlparse(page["url"]).netloc
                    self.memory.record_visit(domain)
                except:
                    pass

        execution_time = time.time() - start_time
        
        # Extract headlines from page titles
        headlines = self._extract_headlines(retrieved_content)
        
        return ExecutionResult(
            genome_id=self.genome.genome_id,
            retrieved_urls=visited_urls,
            generated_queries=[query],
            log=f"Visited {len(visited_urls)} pages. Depth {self.genome.search_depth}.",
            content_summary={"pages": [p["title"] for p in retrieved_content]},
            headlines=headlines,
            api_calls=1,
            execution_time=execution_time,
        )

    def _extract_headlines(self, pages: List[Dict]) -> List[str]:
        """Extracts clean headlines from crawled page data."""
        headlines = []
        for page in pages:
            title = page.get("title", "").strip()
            if not title or title == "No Title":
                continue
            # Clean: remove site suffixes like " - CNN" or " | Reuters"
            for sep in [" - ", " | ", " – ", " — ", " :: "]:
                if sep in title:
                    title = title.split(sep)[0].strip()
                    break
            # Truncate long titles
            if len(title) > 80:
                title = title[:77] + "..."
            if title and title not in headlines:
                headlines.append(title)
        return headlines

    def _generate_query(self) -> str:
        """Generates a search query based on the template ID."""
        # Simple template mapping for now. In future, use LLM.
        templates = {
            "template_v1_broad": "latest trends in technology 2026",
            "template_v2_specific": "AI implementation examples in agriculture",
            "template_v3_questioning": "Is remote work actually productive?",
            "template_v4_news_focused": "breaking news technology sector"
        }
        base = templates.get(self.genome.query_template_id, "technology news")
        return base

    def _score_url(self, url: str) -> float:
        """
        Scores a URL based on the genome's source_bias.
        Higher score = more likely to be visited first.
        """
        score = 0.5 # Base score
        
        # Domain heuristics
        domain_map = {
            "academic": [".edu", ".ac.jp", "arxiv.org", "scholar", "nature.com"],
            "news": ["cnn.com", "bbc.com", "nikkei.com", "reuters.com", "yahoo.co.jp"],
            "official": [".gov", ".go.jp", "digital.go.jp", "whitehouse.gov"],
            "blogs": ["hatenablog", "note.com", "qiita.com", "medium.com", "ameblo.jp"]
        }
        
        bias = self.genome.source_bias
        
        for cat, keywords in domain_map.items():
            for kw in keywords:
                if kw in url:
                    cat_bias = getattr(bias, cat, 0)
                    score += cat_bias * 0.5 
                    break
        
        # Boost from persistent source memory
        if self.memory:
            from urllib.parse import urlparse
            try:
                domain = urlparse(url).netloc
                score += self.memory.get_domain_boost(domain)
            except:
                pass
        
        # Global diversity penalty (Novelty feedback)
        if self.global_domain_counts:
            from urllib.parse import urlparse
            try:
                domain = urlparse(url).netloc
                global_count = self.global_domain_counts.get(domain, 0)
                if global_count > 0:
                    # Penalize based on total frequency across all personas.
                    # Higher global_count = larger penalty.
                    # Simple log-based penalty or inverse sqrt.
                    import math
                    penalty = 0.1 * math.log(global_count + 1)
                    score -= min(penalty, 0.4) # Cap penalty at 0.4
            except:
                pass

        # Novelty weight influence
        if self.genome.novelty_weight > 0.7:
             score += random.uniform(-0.2, 0.2)
             
        return score

    def __str__(self) -> str:
        return f"HybridTraveler(genome_id={self.genome.genome_id}, depth={self.genome.search_depth})"

