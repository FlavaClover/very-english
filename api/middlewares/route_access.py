from fastapi import Request
from fastapi.routing import APIRoute
from starlette.routing import Match

from api.access_policy import ENDPOINT_ACCESS_RULES, EndpointAccessRule


def resolve_endpoint_access_rule(request: Request) -> EndpointAccessRule | None:
    """Возвращает правило доступа для текущего HTTP-запроса."""
    route_path = _resolve_route_path(request)
    if route_path is None:
        return None
    return ENDPOINT_ACCESS_RULES.get((request.method.upper(), route_path))


def _resolve_route_path(request: Request) -> str | None:
    for route in request.app.router.routes:
        if not isinstance(route, APIRoute):
            continue
        match, _ = route.matches(request.scope)
        if match == Match.FULL:
            return route.path
    return None
