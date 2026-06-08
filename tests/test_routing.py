"""Tests for agent_routing.

These tests use only the Python standard library (``unittest``) so they run
with no third-party dependencies::

    python3 -m unittest discover -s tests

The package uses a ``src/`` layout and is not assumed to be installed, so we
add ``src/`` to ``sys.path`` before importing it.
"""

import os
import re
import sys
import unittest

# Make ``src/agent_routing`` importable without installing the package.
_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from agent_routing import NoRouteError, Route, Router, RoutingResult  # noqa: E402


class KeywordRouteTests(unittest.TestCase):
    def test_keyword_match(self):
        r = Router()
        r.add_keyword_route(
            "code", ["python", "function"], config={"model": "code-model"}
        )
        result = r.route("write a python function")
        self.assertEqual(result.route_name, "code")
        self.assertEqual(result.config["model"], "code-model")

    def test_keyword_case_insensitive_by_default(self):
        r = Router()
        r.add_keyword_route("code", ["PYTHON"], config={})
        result = r.route("write some python code")
        self.assertEqual(result.route_name, "code")

    def test_keyword_case_sensitive(self):
        r = Router()
        r.add_keyword_route("code", ["Python"], config={}, case_sensitive=True)
        with self.assertRaises(NoRouteError):
            r.route("write some python code")  # lowercase won't match

    def test_keyword_no_match_raises(self):
        r = Router()
        r.add_keyword_route("code", ["python"], config={})
        with self.assertRaises(NoRouteError):
            r.route("tell me a joke")

    def test_empty_keyword_list_never_matches(self):
        r = Router(default_config={"model": "default"})
        r.add_keyword_route("never", [], config={})
        result = r.route("anything at all")
        self.assertEqual(result.route_name, "__default__")


class DefaultConfigTests(unittest.TestCase):
    def test_default_config_used_on_no_match(self):
        r = Router(default_config={"model": "default"})
        result = r.route("something unrelated")
        self.assertEqual(result.route_name, "__default__")
        self.assertEqual(result.config["model"], "default")
        self.assertEqual(result.score, 0.0)

    def test_default_config_not_used_when_match(self):
        r = Router(default_config={"model": "default"})
        r.add_keyword_route("code", ["python"], config={"model": "code-model"})
        result = r.route("write python code")
        self.assertEqual(result.route_name, "code")

    def test_empty_dict_default_config_is_honoured(self):
        # An empty dict is a valid default and must not be treated like None.
        r = Router(default_config={})
        result = r.route("nothing matches")
        self.assertEqual(result.route_name, "__default__")
        self.assertEqual(result.config, {})


class PriorityTests(unittest.TestCase):
    def test_higher_priority_wins(self):
        r = Router()
        r.add_keyword_route("low", ["python"], config={"model": "low"}, priority=0)
        r.add_keyword_route("high", ["python"], config={"model": "high"}, priority=10)
        result = r.route("write python code")
        self.assertEqual(result.route_name, "high")

    def test_equal_priority_first_registered_wins(self):
        r = Router()
        r.add_keyword_route("first", ["python"], config={"m": 1}, priority=5)
        r.add_keyword_route("second", ["python"], config={"m": 2}, priority=5)
        result = r.route("python code")
        self.assertEqual(result.route_name, "first")

    def test_negative_priority_still_matches(self):
        r = Router()
        r.add_keyword_route("only", ["python"], config={}, priority=-5)
        result = r.route("python")
        self.assertEqual(result.route_name, "only")


class RegexRouteTests(unittest.TestCase):
    def test_regex_route_matches(self):
        r = Router()
        r.add_regex_route(
            "email",
            r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
            config={"type": "email"},
        )
        result = r.route("send email to user@example.com")
        self.assertEqual(result.route_name, "email")
        self.assertEqual(result.config["type"], "email")

    def test_regex_no_match(self):
        r = Router(default_config={"type": "generic"})
        r.add_regex_route("email", r"\S+@\S+\.\S+", config={})
        result = r.route("no email here")
        self.assertEqual(result.route_name, "__default__")

    def test_regex_default_flags_are_case_insensitive(self):
        r = Router()
        r.add_regex_route("greet", r"hello", config={})
        result = r.route("HELLO THERE")
        self.assertEqual(result.route_name, "greet")

    def test_regex_explicit_case_sensitive_flags(self):
        r = Router(default_config={})
        r.add_regex_route("greet", r"hello", config={}, flags=0)
        result = r.route("HELLO THERE")
        self.assertEqual(result.route_name, "__default__")


class LengthRouteTests(unittest.TestCase):
    def test_length_route_min(self):
        r = Router()
        r.add_length_route("long", min_length=100, config={"type": "long"})
        result = r.route("x" * 150)
        self.assertEqual(result.route_name, "long")

    def test_length_route_max(self):
        r = Router()
        r.add_length_route("short", max_length=20, config={"type": "short"})
        result = r.route("hi")
        self.assertEqual(result.route_name, "short")

    def test_length_route_range(self):
        r = Router()
        r.add_length_route(
            "medium", min_length=10, max_length=50, config={"type": "medium"}
        )
        result = r.route("x" * 30)
        self.assertEqual(result.route_name, "medium")

    def test_length_route_no_match(self):
        r = Router(default_config={})
        r.add_length_route("short", max_length=5, config={})
        result = r.route("this is a longer message")
        self.assertEqual(result.route_name, "__default__")

    def test_length_route_boundaries_are_inclusive(self):
        r = Router(default_config={})
        r.add_length_route("exact", min_length=5, max_length=5, config={"ok": True})
        self.assertEqual(r.route("x" * 5).route_name, "exact")
        self.assertEqual(r.route("x" * 4).route_name, "__default__")
        self.assertEqual(r.route("x" * 6).route_name, "__default__")

    def test_length_route_without_config_defaults_to_empty_dict(self):
        r = Router()
        r.add_length_route("any", min_length=0)
        result = r.route("hello")
        self.assertEqual(result.route_name, "any")
        self.assertEqual(result.config, {})


class CustomPredicateTests(unittest.TestCase):
    def test_custom_predicate(self):
        r = Router()
        r.add_route("question", lambda t: t.endswith("?"), config={"type": "question"})
        result = r.route("what is the weather?")
        self.assertEqual(result.route_name, "question")

    def test_custom_predicate_no_match(self):
        r = Router(default_config={})
        r.add_route("question", lambda t: t.endswith("?"), config={})
        result = r.route("tell me the weather")
        self.assertEqual(result.route_name, "__default__")


class RouteMessagesTests(unittest.TestCase):
    def test_route_messages_uses_last_user(self):
        r = Router()
        r.add_keyword_route("code", ["python"], config={"model": "code"})
        messages = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
            {"role": "user", "content": "write python code"},
        ]
        result = r.route_messages(messages)
        self.assertEqual(result.route_name, "code")

    def test_route_messages_content_list(self):
        r = Router()
        r.add_keyword_route("code", ["python"], config={})
        messages = [
            {"role": "user", "content": [{"type": "text", "text": "write python code"}]}
        ]
        result = r.route_messages(messages)
        self.assertEqual(result.route_name, "code")

    def test_route_messages_content_list_multiple_text_blocks(self):
        r = Router()
        r.add_keyword_route("code", ["python"], config={})
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "write some"},
                    {"type": "image", "source": "..."},
                    {"type": "text", "text": "python code"},
                ],
            }
        ]
        result = r.route_messages(messages)
        self.assertEqual(result.route_name, "code")

    def test_route_messages_empty_falls_to_default(self):
        r = Router(default_config={})
        result = r.route_messages([])
        self.assertEqual(result.route_name, "__default__")

    def test_route_messages_none_content_does_not_route_literal_none(self):
        # A user message with content=None must be treated as empty text,
        # not coerced to the literal string "None".
        r = Router()
        r.add_keyword_route("none", ["none"], config={})
        with self.assertRaises(NoRouteError):
            r.route_messages([{"role": "user", "content": None}])

    def test_route_messages_missing_content_falls_to_default(self):
        r = Router(default_config={"model": "default"})
        result = r.route_messages([{"role": "user"}])
        self.assertEqual(result.route_name, "__default__")

    def test_route_messages_ignores_non_user_roles(self):
        r = Router(default_config={"model": "default"})
        r.add_keyword_route("code", ["python"], config={})
        messages = [
            {"role": "system", "content": "python system prompt"},
            {"role": "assistant", "content": "python answer"},
        ]
        result = r.route_messages(messages)
        self.assertEqual(result.route_name, "__default__")


class AllRoutesTests(unittest.TestCase):
    def test_all_routes_listed(self):
        r = Router()
        r.add_keyword_route("a", ["x"], config={})
        r.add_keyword_route("b", ["y"], config={})
        self.assertEqual(set(r.all_routes()), {"a", "b"})

    def test_all_routes_empty_initially(self):
        self.assertEqual(Router().all_routes(), [])


class RoutingResultTests(unittest.TestCase):
    def test_routing_result_has_matched_text(self):
        r = Router()
        r.add_keyword_route("code", ["python"], config={})
        result = r.route("python rocks")
        self.assertEqual(result.matched_text, "python rocks")

    def test_routing_result_score_default(self):
        r = Router()
        r.add_keyword_route("code", ["python"], config={})
        result = r.route("python")
        self.assertEqual(result.score, 1.0)

    def test_route_returns_routing_result_instance(self):
        r = Router()
        r.add_keyword_route("code", ["python"], config={})
        result = r.route("python")
        self.assertIsInstance(result, RoutingResult)


class FluentApiTests(unittest.TestCase):
    def test_add_methods_return_router_for_chaining(self):
        r = Router(default_config={})
        returned = (
            r.add_keyword_route("a", ["x"], config={})
            .add_regex_route("b", r"y", config={})
            .add_length_route("c", min_length=1, config={})
            .add_route("d", lambda t: False, config={})
        )
        self.assertIs(returned, r)
        self.assertEqual(set(r.all_routes()), {"a", "b", "c", "d"})

    def test_route_dataclass_fields(self):
        route = Route(name="x", matcher=lambda t: True, config={"k": 1}, priority=3)
        self.assertEqual(route.name, "x")
        self.assertEqual(route.priority, 3)
        self.assertTrue(route.matcher("anything"))


if __name__ == "__main__":
    unittest.main()
