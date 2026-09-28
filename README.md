# LLM Usage & Cost Analytics

A small, reusable Python/Pandas/Streamlit project for understanding request-level LLM usage, latency, reliability, and estimated spend.

## Structure

```text
data/llm_usage.csv       # request-level sample data
llm_analytics.py         # shared loading, cleaning, and metric helpers
dashboard/app.py         # Streamlit dashboard
notebooks/analysis.ipynb # exploratory analysis and findings
requirements.txt
```

## Run

```bash
pip install -r requirements.txt
streamlit run dashboard/app.py
jupyter notebook notebooks/analysis.ipynb
```

The dashboard looks for `data/llm_usage.csv` relative to the project root and also supports an uploaded CSV. Invalid rows are dropped with a warning; an empty or malformed file produces a helpful empty-state message rather than a traceback.

## Schema

| Column | Type | Description |
|---|---|---|
| `request_id` | string | Unique request identifier |
| `timestamp` | datetime | Request start time (UTC) |
| `application` | string | Calling product or workflow |
| `environment` | string | `production`, `staging`, or `development` |
| `model` | string | LLM model name |
| `status` | string | `success`, `error`, or `timeout` |
| `prompt_tokens` | integer | Input tokens |
| `completion_tokens` | integer | Output tokens |
| `latency_ms` | integer | End-to-end latency |

## Pricing assumptions

The sample dashboard uses illustrative, not vendor-contract, blended rates (USD per 1,000 tokens):

* `gpt-4o`: $0.005 input, $0.015 output
* `gpt-4o-mini`: $0.00015 input, $0.0006 output
* `claude-3-5-sonnet`: $0.003 input, $0.015 output
* `gemini-1.5-pro`: $0.00125 input, $0.005 output
* Unknown models use the conservative default of $0.001 input and $0.003 output.

Estimated cost is calculated only from token counts, regardless of request status. Replace `PRICING` in `llm_analytics.py` with your negotiated rates for production reporting.

## Validation

```bash
python -m py_compile llm_analytics.py dashboard/app.py
python -c "from llm_analytics import load_usage_data, summarize; print(summarize(load_usage_data()))"
```
# LLM-Analytics
