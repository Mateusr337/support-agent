LLM_LATENCY_MESSAGES = frozenset({"LLM response", "LLM stream response"})
TURN_LATENCY_MESSAGE = "Agent reply generated"
TOKEN_USAGE_TYPE = "Token Usage"
TOOL_RESULT_TYPE = "Tool Result"

TOKEN_HISTOGRAM_BUCKETS = (
    (0, 500),
    (500, 1000),
    (1000, 2000),
    (2000, None),
)
