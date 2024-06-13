import logging
from aiohttp import web
import json
import asyncio
from uuid import uuid4


from pprint import pprint


from gptChat import GPTChat
from leonardo import LeonardoGeneration

logger = logging.getLogger(__name__)


async def request_neighbor(request):
    pending_requests = request.app["pending_requests"]
    pending_events = request.app["pending_events"]
    leo = None

    try:
        data = await request.json()

        # Validate the input
        description = data.get("description")
        userId = data.get("userId")
        neighborName = data.get("neighborName")

        prompts = {
            "user": description,
            "gpt": "",
            "leonardo": "90's Disney 2D, medium torso shot, facing right, white background, full torso in frame, looking at camera, rustic, peppy, ",
        }

        if not description:
            return web.json_response(
                {"error": "Invalid message: 'description' is required"}, status=422
            )
        if not isinstance(description, str):
            return web.json_response(
                {"error": "Invalid message: 'description' must be a string"}, status=422
            )

        if not userId:
            return web.json_response(
                {"error": "Invalid userId: 'userId' is required"}, status=422
            )
        if not isinstance(userId, str):
            return web.json_response(
                {"error": "Invalid userId: 'userId' must be a string"}, status=422
            )

        if not neighborName:
            return web.json_response(
                {"error": "Invalid neighborName: 'neighborName' is required"},
                status=422,
            )
        if not isinstance(neighborName, str):
            return web.json_response(
                {"error": "Invalid neighborName: 'neighborName' must be a string"},
                status=422,
            )

        # Process user description with GPT
        gpt = GPTChat(user_prompt=description)
        gpt_description = await gpt.get_leonardo_prompt()
        prompts["gpt"] = gpt_description
        prompts["leonardo"] = prompts["leonardo"] + prompts["gpt"]

        # Request image generation from Leonardo
        leo = LeonardoGeneration(prompt=prompts["leonardo"])
        await leo.generate_img()

        # Store the request and event
        pending_requests[leo.id] = {
            "description": description,
            "userId": userId,
            "neighborName": neighborName,
        }

        pending_events[leo.id] = asyncio.Event()
        # Wait for the event to complete
        await pending_events[leo.id].wait()

        response_data = pending_requests.pop(leo.id, None)
        pending_events.pop(leo.id, None)

        if "error" in response_data:
            return web.json_response({"error": response_data["error"]}, status=500)

        return web.json_response(
            {"status": "success", "data": response_data}, status=201
        )

    except json.JSONDecodeError:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)
    finally:
        if leo and leo.id in pending_requests:
            pending_requests.pop(leo.id, None)
            pending_events.pop(leo.id, None)


async def webhook_listener(request):
    try:
        # Parse the incoming JSON
        body = await request.json()
        data = body["data"]["object"]
        imgage_data = data["images"][0]
        generation_id = imgage_data["generationId"]

        # Get the pending requests and events
        pending_requests = request.app["pending_requests"]
        pending_events = request.app["pending_events"]

        # Get the request data that corresponds to a pending request
        if generation_id in pending_requests:
            pending_events[generation_id].set()
            pending_requests[generation_id]["image"] = imgage_data
            logger.info(f"Received webhook data for generation id: {generation_id}")
        logger.warning(f"No pending request found for generation id: {generation_id}")
        return
    except json.JSONDecodeError:
        logger.error("Invalid JSON received by webhook_listener")
        if generation_id in pending_requests:
            pending_requests[generation_id]["error"] = "Invalid JSON received"
            pending_events[generation_id].set()
    except Exception as e:
        logger.error(f"Error in webhook_listener: {str(e)}")
        if generation_id in pending_requests:
            pending_requests[generation_id]["error"] = str(e)
            pending_events[generation_id].set()


def setup_routes(app):
    app.router.add_post("/neighbor", request_neighbor)
    app.router.add_post("/wh", webhook_listener)
