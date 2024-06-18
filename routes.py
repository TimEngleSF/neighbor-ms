from handlers import request_neighbor, webhook_listener


def setup_routes(app):
    app.router.add_post("/neighbor", request_neighbor)
    app.router.add_post("/wh", webhook_listener)
