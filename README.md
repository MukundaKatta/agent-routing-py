# agent-routing-py

Route messages to different LLM configs based on intent and content.

```bash
pip install agent-routing-py
```

## Quick start

```python
from agent_routing import Router

router = Router(default_config={"model": "gpt-4o-mini"})

router.add_keyword_route("code",     ["python", "typescript", "function", "def "],
                          config={"model": "gpt-4o", "temperature": 0.2})
router.add_keyword_route("creative", ["story", "poem", "imagine", "write a"],
                          config={"model": "claude-opus-4-6", "temperature": 0.9})
router.add_length_route("long_context", min_length=2000,
                         config={"model": "claude-sonnet-4-6"})

result = router.route("Write a python function to sort a list")
# result.route_name == "code"
# result.config     == {"model": "gpt-4o", "temperature": 0.2}
```

## Route from messages

```python
result = router.route_messages(conversation_messages)
# Uses the last user message content
```

## Route types

```python
# Keyword — match if any keyword appears in text
router.add_keyword_route(name, keywords, config, priority=0, case_sensitive=False)

# Regex — match via regular expression
router.add_regex_route(name, pattern, config, priority=0, flags=re.IGNORECASE)

# Length — match based on text length
router.add_length_route(name, min_length=None, max_length=None, config, priority=0)

# Custom predicate
router.add_route(name, matcher=lambda text: ..., config, priority=0)
```

## Priority

Higher `priority` value = evaluated first. Equal priority = first registered wins.

## API

```python
Router(default_config=None)
  .add_route / .add_keyword_route / .add_regex_route / .add_length_route
  .route(text) -> RoutingResult
  .route_messages(messages) -> RoutingResult
  .all_routes() -> list[str]

RoutingResult.route_name   # str
RoutingResult.config       # dict
RoutingResult.matched_text # str
RoutingResult.score        # float (1.0 for match, 0.0 for default)
```

Raises `NoRouteError` when nothing matches and no `default_config` is set.

## Zero dependencies
