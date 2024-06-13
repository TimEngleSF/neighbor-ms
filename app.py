import logging
from aiohttp import web
from dotenv import load_dotenv

from routes import setup_routes
from middleware import api_key_middleware, request_logger_middleware

pending_requests = {}
pending_events = {}


async def init_app():
    app = web.Application(middlewares=[api_key_middleware, request_logger_middleware])
    setup_routes(app)
    ## TEMP IN MEMORY STORAGE ##
    app["pending_requests"] = pending_requests
    app["pending_events"] = pending_events
    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info("Starting...")

    web.run_app(init_app())
