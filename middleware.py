import logging

from aiohttp import web
from config import CLIENT_KEY

logger = logging.getLogger(__name__)


@web.middleware
async def api_key_middleware(request, handler):
    if request.path == "/neighbor":
        auth_header = request.headers.get("authorization")
        api_key = auth_header.split(" ")[1]
        if api_key != CLIENT_KEY:
            return web.json_response({"error": "Forbidden"}, status=403)
    return await handler(request)


@web.middleware
async def request_logger_middleware(request, handler):
    logger.info(f"Incoming request: {request.method} {request.path}")
    response = await handler(request)
    return response
