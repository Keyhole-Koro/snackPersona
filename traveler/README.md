## Main Execution Flow

`snackTraveler` now uses a **Hybrid Exploration Strategy** that combines Google Search with Web Crawling.

1.  **Search Phase**: The traveler generates a query based on its genome and retrieves top results from Google Search.
2.  **Crawl Phase**: It visits the retrieved pages and extracts links.
3.  **Selection**: Links are scored based on the traveler's `source_bias` (e.g., favoring academic vs news).
4.  **Deep Dive**: If `search_depth` allows, it recursively visits high-scoring links to find niche information.

### Architecture

```mermaid
graph TD
    A[Start] --> B[Initialize EliteMap and BanditAllocator];
    B --> C[Create initial population];
    
    subgraph "Evolutionary Loop (Exploration)"
        D[For each generation] --> E{For each genome};
        E --> F[Execute Hybrid Traveler];
        F --> G[Search (google-search)];
        G --> H[Crawl & Score Links];
        H --> I[Deep Dive (requests/bs4)];
        I --> J[Evaluate Result (Real Metrics)];
        J --> K[Add to EliteMap];
        K --> E;
    end

    C --> D;
```
