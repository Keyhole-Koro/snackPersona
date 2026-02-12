# Future Improvements

Areas identified for future development, primarily around robustness and error handling.

---

## LLM API Error Handling

### Retry with Exponential Backoff

Currently, LLM API failures return an empty string or fallback values silently. A retry mechanism should be added:

```python
import time

def call_with_retry(func, max_retries=3, base_delay=1.0):
    for attempt in range(max_retries):
        try:
            return func()
        except (RateLimitError, TimeoutError) as e:
            delay = base_delay * (2 ** attempt)
            logger.warning(f"Retry {attempt+1}/{max_retries} after {delay}s: {e}")
            time.sleep(delay)
    raise MaxRetriesExceeded(f"Failed after {max_retries} attempts")
```

### Graceful Degradation

When the LLM API is unavailable:
- **Evaluator**: Fall back to `BasicEvaluator` heuristics instead of crashing
- **LLMMutator**: Fall back to `SimpleFieldMutator`
- **SimulationAgent**: Use a template-based response (e.g., `"[{persona.name} is thinking...]"`) instead of empty string
- **Engagement decisions**: Default to `True` (always engage) if LLM cannot decide

### Rate Limiting

For production use with paid APIs:
- Implement a token bucket or sliding window rate limiter
- Track token usage per generation for cost estimation
- Add `--max_tokens_per_gen` CLI flag as a budget cap

---

## Input Validation

### Config File Validation
- Validate `evolution_config.json` against a JSON schema on load
- Ensure fitness weights sum to 1.0 (or normalise automatically)
- Validate niche sigma > 0 and alpha > 0
- Warn if population_size < elite_count

### Seed Persona Validation
- Validate each persona against `PersonaGenotype` schema before starting evolution
- Check for duplicate names (which would break per-agent transcript filtering)
- Ensure age is within valid range (18+)
- Warn if personality trait values are outside [0, 1]

---

## Timeout Handling

### Per-call Timeouts
- Add timeout parameter to `LLMClient.generate_text()`
- Default: 30s for generation, 10s for evaluation judgements
- On timeout: log the event and return fallback value

### Per-generation Timeouts
- Add `--gen_timeout` CLI flag (default: no limit)
- If a generation takes too long, save partial results and move on

---

## Async / Parallel Processing

### Agent-level Parallelism
- LLM calls within a simulation group are independent
- Use `asyncio.gather()` or `concurrent.futures.ThreadPoolExecutor`
- Expected speedup: ~4x for groups of 4 agents

### Evaluation Parallelism
- Each agent's evaluation is independent
- Batch embedding calls (already supported by sentence-transformers)

### Implementation Priority
1. Thread-pool for LLM calls within `SimulationEnvironment`
2. Batch embeddings in `DiversityEvaluator`
3. Full async rewrite of the pipeline (longer term)

---

## Observability

### Metrics to Track
- Total LLM tokens used per generation
- API call latency (p50, p95, p99)
- Failure rate per LLM backend
- Evolution convergence rate (fitness plateau detection)

### Dashboard
- Read `generation_stats.jsonl` and plot fitness curves
- Matplotlib or Streamlit for quick visualization
