import pytest
from agent_routing import Router, RoutingResult, NoRouteError


# ---------------------------------------------------------------------------
# Keyword routes
# ---------------------------------------------------------------------------

def test_keyword_match():
    r = Router()
    r.add_keyword_route("code", ["python", "function"], config={"model": "code-model"})
    result = r.route("write a python function")
    assert result.route_name == "code"
    assert result.config["model"] == "code-model"


def test_keyword_case_insensitive_by_default():
    r = Router()
    r.add_keyword_route("code", ["PYTHON"], config={})
    result = r.route("write some python code")
    assert result.route_name == "code"


def test_keyword_case_sensitive():
    r = Router()
    r.add_keyword_route("code", ["Python"], config={}, case_sensitive=True)
    with pytest.raises(NoRouteError):
        r.route("write some python code")  # lowercase won't match


def test_keyword_no_match_raises():
    r = Router()
    r.add_keyword_route("code", ["python"], config={})
    with pytest.raises(NoRouteError):
        r.route("tell me a joke")


# ---------------------------------------------------------------------------
# Default config
# ---------------------------------------------------------------------------

def test_default_config_used_on_no_match():
    r = Router(default_config={"model": "default"})
    result = r.route("something unrelated")
    assert result.route_name == "__default__"
    assert result.config["model"] == "default"
    assert result.score == 0.0


def test_default_config_not_used_when_match():
    r = Router(default_config={"model": "default"})
    r.add_keyword_route("code", ["python"], config={"model": "code-model"})
    result = r.route("write python code")
    assert result.route_name == "code"


# ---------------------------------------------------------------------------
# Priority
# ---------------------------------------------------------------------------

def test_higher_priority_wins():
    r = Router()
    r.add_keyword_route("low", ["python"], config={"model": "low"}, priority=0)
    r.add_keyword_route("high", ["python"], config={"model": "high"}, priority=10)
    result = r.route("write python code")
    assert result.route_name == "high"


def test_equal_priority_first_registered_wins():
    r = Router()
    r.add_keyword_route("first", ["python"], config={"m": 1}, priority=5)
    r.add_keyword_route("second", ["python"], config={"m": 2}, priority=5)
    result = r.route("python code")
    assert result.route_name == "first"


# ---------------------------------------------------------------------------
# Regex routes
# ---------------------------------------------------------------------------

def test_regex_route_matches():
    r = Router()
    r.add_regex_route("email", r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", config={"type": "email"})
    result = r.route("send email to user@example.com")
    assert result.route_name == "email"
    assert result.config["type"] == "email"


def test_regex_no_match():
    r = Router(default_config={"type": "generic"})
    r.add_regex_route("email", r"\S+@\S+\.\S+", config={})
    result = r.route("no email here")
    assert result.route_name == "__default__"


# ---------------------------------------------------------------------------
# Length routes
# ---------------------------------------------------------------------------

def test_length_route_min():
    r = Router()
    r.add_length_route("long", min_length=100, config={"type": "long"})
    result = r.route("x" * 150)
    assert result.route_name == "long"


def test_length_route_max():
    r = Router()
    r.add_length_route("short", max_length=20, config={"type": "short"})
    result = r.route("hi")
    assert result.route_name == "short"


def test_length_route_range():
    r = Router()
    r.add_length_route("medium", min_length=10, max_length=50, config={"type": "medium"})
    result = r.route("x" * 30)
    assert result.route_name == "medium"


def test_length_route_no_match():
    r = Router(default_config={})
    r.add_length_route("short", max_length=5, config={})
    result = r.route("this is a longer message")
    assert result.route_name == "__default__"


# ---------------------------------------------------------------------------
# Custom predicate route
# ---------------------------------------------------------------------------

def test_custom_predicate():
    r = Router()
    r.add_route("question", lambda t: t.endswith("?"), config={"type": "question"})
    result = r.route("what is the weather?")
    assert result.route_name == "question"


def test_custom_predicate_no_match():
    r = Router(default_config={})
    r.add_route("question", lambda t: t.endswith("?"), config={})
    result = r.route("tell me the weather")
    assert result.route_name == "__default__"


# ---------------------------------------------------------------------------
# route_messages
# ---------------------------------------------------------------------------

def test_route_messages_uses_last_user():
    r = Router()
    r.add_keyword_route("code", ["python"], config={"model": "code"})
    messages = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
        {"role": "user", "content": "write python code"},
    ]
    result = r.route_messages(messages)
    assert result.route_name == "code"


def test_route_messages_content_list():
    r = Router()
    r.add_keyword_route("code", ["python"], config={})
    messages = [
        {"role": "user", "content": [{"type": "text", "text": "write python code"}]}
    ]
    result = r.route_messages(messages)
    assert result.route_name == "code"


def test_route_messages_empty_falls_to_default():
    r = Router(default_config={})
    result = r.route_messages([])
    assert result.route_name == "__default__"


# ---------------------------------------------------------------------------
# all_routes
# ---------------------------------------------------------------------------

def test_all_routes_listed():
    r = Router()
    r.add_keyword_route("a", ["x"], config={})
    r.add_keyword_route("b", ["y"], config={})
    assert set(r.all_routes()) == {"a", "b"}


# ---------------------------------------------------------------------------
# RoutingResult
# ---------------------------------------------------------------------------

def test_routing_result_has_matched_text():
    r = Router()
    r.add_keyword_route("code", ["python"], config={})
    result = r.route("python rocks")
    assert result.matched_text == "python rocks"


def test_routing_result_score_default():
    r = Router()
    r.add_keyword_route("code", ["python"], config={})
    result = r.route("python")
    assert result.score == 1.0
