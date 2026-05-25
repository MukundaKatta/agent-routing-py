"""agent-routing-py — route messages to different LLM configs based on intent."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Route:
    name: str
    matcher: Callable[[str], bool]
    config: dict
    priority: int = 0


@dataclass
class RoutingResult:
    route_name: str
    config: dict
    matched_text: str
    score: float = 1.0


class NoRouteError(Exception):
    """Raised when no route matches and there is no default."""


class Router:
    """
    Route messages to different LLM configs based on content/intent.

    Supports keyword matching, regex matching, and custom predicate functions.
    Routes are evaluated in priority order (higher = first).

    Example::

        router = Router(default_config={"model": "fast-model"})
        router.add_keyword_route("code", ["python", "typescript", "function", "def "],
                                  config={"model": "code-model"})
        router.add_keyword_route("creative", ["story", "poem", "write a"],
                                  config={"model": "creative-model"})

        result = router.route("Write a python function to sort a list")
        # result.route_name == "code"
    """

    def __init__(self, default_config: dict | None = None) -> None:
        self._routes: list[Route] = []
        self._default_config = default_config

    # ------------------------------------------------------------------
    # Route registration
    # ------------------------------------------------------------------

    def add_route(
        self,
        name: str,
        matcher: Callable[[str], bool],
        config: dict,
        priority: int = 0,
    ) -> "Router":
        self._routes.append(Route(name, matcher, config, priority))
        return self

    def add_keyword_route(
        self,
        name: str,
        keywords: list[str],
        config: dict,
        priority: int = 0,
        case_sensitive: bool = False,
    ) -> "Router":
        """Match if any keyword appears in the text."""
        def matcher(text: str) -> bool:
            t = text if case_sensitive else text.lower()
            return any((kw if case_sensitive else kw.lower()) in t for kw in keywords)
        return self.add_route(name, matcher, config, priority)

    def add_regex_route(
        self,
        name: str,
        pattern: str,
        config: dict,
        priority: int = 0,
        flags: int = re.IGNORECASE,
    ) -> "Router":
        """Match via regular expression."""
        compiled = re.compile(pattern, flags)

        def matcher(text: str) -> bool:
            return bool(compiled.search(text))
        return self.add_route(name, matcher, config, priority)

    def add_length_route(
        self,
        name: str,
        min_length: int | None = None,
        max_length: int | None = None,
        config: dict | None = None,
        priority: int = 0,
    ) -> "Router":
        """Match based on text length."""
        _config = config or {}
        def matcher(text: str) -> bool:
            n = len(text)
            if min_length is not None and n < min_length:
                return False
            if max_length is not None and n > max_length:
                return False
            return True
        return self.add_route(name, matcher, _config, priority)

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def route(self, text: str) -> RoutingResult:
        """
        Return the best matching route for the given text.
        Raises NoRouteError if no match and no default is configured.
        """
        sorted_routes = sorted(self._routes, key=lambda r: -r.priority)
        for route in sorted_routes:
            if route.matcher(text):
                return RoutingResult(
                    route_name=route.name,
                    config=route.config,
                    matched_text=text,
                )

        if self._default_config is not None:
            return RoutingResult(
                route_name="__default__",
                config=self._default_config,
                matched_text=text,
                score=0.0,
            )
        raise NoRouteError(f"No route matched text (length={len(text)})")

    def route_messages(self, messages: list[dict]) -> RoutingResult:
        """Route based on the last user message content."""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, list):
                    content = " ".join(
                        b.get("text", "") for b in content
                        if isinstance(b, dict) and b.get("type") == "text"
                    )
                return self.route(str(content))
        return self.route("")

    def all_routes(self) -> list[str]:
        return [r.name for r in self._routes]


__all__ = ["Router", "Route", "RoutingResult", "NoRouteError"]
