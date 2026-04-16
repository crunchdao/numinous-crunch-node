"""
Gateway worker — FastAPI app serving the Gateway.

Reads predictions, scores, agent runs directly from PG
and exposes them via REST endpoints.
"""

if True:
    # bt_compat MUST be imported before any neurons.validator.* module
    import crunch_node.bt_compat  # noqa: F401

import os
import re
from contextvars import ContextVar

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from neurons.miner.gateway.app import ChutesClient, DesearchClient, LightningRodClient, LunarCrushClient, NuminousIndiciaClient, NuminousSignalsClient, OpenAIClient, OpenRouterClient, PerplexityClient, PublicDataProxyClient, UnusualWhalesClient, VericoreClient, app
from neurons.miner.gateway.providers import public_data as public_data_provider
from neurons.validator.sandbox.signing_proxy.async_host import AsyncValidatorSigningProxy

from crunch_node.config import CrunchNodeConfig

config = CrunchNodeConfig()
request_ctx: ContextVar[Request] = ContextVar("request_ctx")


@app.middleware("http")
async def set_request_context(request: Request, call_next):
    token = request_ctx.set(request)
    response = await call_next(request)
    request_ctx.reset(token)
    return response


os.environ["RUN_REGISTRY_DIR"] = config.run_registry_dir
path_validator = AsyncValidatorSigningProxy(
    wallet=None,
    proxy_upstream_url=None,
    port=None,
)


@app.middleware("http")
async def body_middleware(request: Request, call_next):
    path = request.url.path
    if not path.startswith("/api/gateway/"):
        return await call_next(request)

    if not request.method in ("POST", "PUT", "PATCH"):
        return await call_next(request)

    body = await request.body()

    blocked = path_validator._check_track_access(path, body)
    if blocked is not None:
        return JSONResponse(
            status_code=blocked.status,
            content={"detail": blocked.text},
        )

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    request._receive = receive

    response = await call_next(request)
    return response


CLIENTS = {
    "chutes": (ChutesClient, "CHUTES_API_KEY"),
    "desearch": (DesearchClient, "DESEARCH_API_KEY"),
    "lightning-rod": (LightningRodClient, "LIGHTNING_ROD_API_KEY"),
    "lunar-crush": (LunarCrushClient, "LUNAR_CRUSH_API_KEY"),
    "numinous-indicia": (NuminousIndiciaClient, None),
    "numinous-signals": (NuminousSignalsClient, "NUMINOUS_SIGNALS_API_KEY"),
    "openai": (OpenAIClient, "OPENAI_API_KEY"),
    "openrouter": (OpenRouterClient, "OPENROUTER_API_KEY"),
    "perplexity": (PerplexityClient, "PERPLEXITY_API_KEY"),
    "public-data": (None, None),
    "unusual-whales": (UnusualWhalesClient, "UNUSUAL_WHALES_API_KEY"),
    "vericore": (VericoreClient, "VERICORE_API_KEY"),
}


def _get_api_key_from_current_request(client_name: str) -> str:
    header_name = f"x-{client_name}-api-key"

    api_key = request_ctx.get().headers.get(header_name)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"{header_name} header is required for {client_name}",
        )

    return api_key


def patch_init(client_name: str, client_class: type):
    original = client_class.__init__

    def patched(self, **kwargs):
        kwargs["api_key"] = _get_api_key_from_current_request(client_name)
        original(self, **kwargs)

    return patched


for client_name, (client_class, api_key_env_var) in CLIENTS.items():
    if api_key_env_var is None:
        continue

    os.environ[api_key_env_var] = "invalid"

    client_class.__init__ = patch_init(client_name, client_class)


def patched_data_get_api_key_for_source(source: public_data_provider.PublicDataSourceInfo) -> str | None:
    if not source.requires_auth:
        return None

    client_name = source.name.lower().replace("_", "-")
    return _get_api_key_from_current_request(client_name)


public_data_provider._get_api_key_for_source = patched_data_get_api_key_for_source


for route in app.router.routes:
    match = re.match(r"/api/gateway/(.+?)/", route.path)
    if not match:
        continue

    client_name = match.group(1)
    client_class, api_key_env_var = CLIENTS[client_name]

    if client_class is None:
        continue

    if route.openapi_extra is None:
        route.openapi_extra = {}

    route.openapi_extra.setdefault("parameters", []).append({
        "name": f"x-{client_name}-api-key",
        "in": "header",
        "required": True,
        "schema": {"type": "string"},
        "description": f"{client_name} API key header",
    })

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
