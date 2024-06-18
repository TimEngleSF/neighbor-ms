import logging
from aiohttp import web
import aiohttp
import json
import asyncio

from gptChat import GPTChat
from leonardo import LeonardoGeneration

logger = logging.getLogger(__name__)


async def request_neighbor(request):
    # Retrieve the dictionaries to store pending requests and events
    pending_requests = request.app["pending_requests"]
    pending_events = request.app["pending_events"]
    leo = None

    try:
        data = await request.json()
        expected_fields = {
            "description",
            "userId",
        }
        received_fields = set(data.keys())

        # Check for unexpected fields
        unexpected_fields = received_fields - expected_fields
        if unexpected_fields:
            return web.json_response(
                {
                    "error": f"Unexpected fields in request: {', '.join(unexpected_fields)}"
                },
                status=422,
            )

        description = data.get("description")
        userId = data.get("userId")

        # Prepare prompts for GPT and Leonardo
        prompts = {
            "user": description,
            "gpt": "",
            "leonardo": "90's Disney 2D, medium torso shot, facing right, white background, full torso in frame, looking at camera, rustic, peppy, ",
        }

        # Input validation
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

        # Process user description with GPT to get a better prompt for Leonardo  # Process user description with GPT to get a better prompt for Leonardo
        gpt = GPTChat(user_prompt=description)
        leo_prompt_task = gpt.get_leonardo_prompt()

        # Request image generation from Leonardo (async but dependent on GPT prompt)
        leo = LeonardoGeneration(prompt=await leo_prompt_task)
        generate_img_task = leo.generate_img()

        await generate_img_task

        prompts["gpt"] = gpt.gptDescription.strip('"')
        prompts["leonardo"] = gpt.leonardo_prompt


        # Store the request details and initialize an asyncio.Event for the generation process
        pending_requests[leo.generation_id] = {
            "description": description,
            "userId": userId,
            "bg_removal_status": None,
        }

        pending_events[leo.generation_id] = asyncio.Event()

        # Wait for the image generation event to complete
        await pending_events[leo.generation_id].wait()
        leo.image_id = pending_requests[leo.generation_id]["image"]["id"]

        # Clean up the generation event
        pending_events.pop(leo.generation_id, None)
        response_data = pending_requests.pop(leo.generation_id, None)

        # Request background removal from Leonardo
        pending_requests[leo.image_id] = response_data
        await leo.request_bg_removal()

        # Initialize and wait for the background removal event to complete
        pending_events[leo.bg_removal_id] = asyncio.Event()
        await pending_events[leo.bg_removal_id].wait()

        # Retrieve and clean up the response data
        response_data = pending_requests.pop(leo.image_id, None)
        leo.processed_img_url = response_data["image_url"]
        pending_events.pop(leo.bg_removal_id, None)

        # Save the processed image
        async with aiohttp.ClientSession() as session:
            await leo.save_processed_img(session)

        payload = {
            "userId": response_data["userId"],
            "prompt": {
                "user": prompts["user"],
                "gpt": prompts["gpt"],
                "leonardo": prompts["leonardo"],
            },
            "image": {
                "filename": leo.processed_filename,
                "path": leo.processed_filepath,
                "url": leo.processed_img_url,
            },
            "leonardoImageData": response_data["image"],
        }

        # Check for errors in the response data
        if "error" in response_data:
            return web.json_response({"error": response_data["error"]}, status=500)

        # Return a successful response with the response data
        return web.json_response({"data": payload}, status=201)

    except json.JSONDecodeError:
        # Handle JSON decoding errors
        return web.json_response({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        # Handle other exceptions
        return web.json_response({"error": str(e)}, status=500)
    finally:
        # Clean up pending requests and events in case of an exception
        if leo:
            if leo.generation_id and leo.generation_id in pending_requests:
                pending_requests.pop(leo.generation_id, None)
                pending_events.pop(leo.generation_id, None)
            if leo.image_id and leo.image_id in pending_requests:
                pending_requests.pop(leo.image_id, None)
                pending_events.pop(leo.image_id, None)


async def webhook_listener(request):
    try:
        # Parse the incoming JSON
        body = await request.json()
        job_type = body["type"]
        data = body["data"]["object"]

        # Check for image generation completion event
        if job_type == "image_generation.complete":
            imgage_data = data["images"][0]
            generation_id = imgage_data["generationId"]

            # Get the pending requests and events
            pending_requests = request.app["pending_requests"]
            pending_events = request.app["pending_events"]

            # Update the pending request with image data
            if generation_id in pending_requests:
                pending_events[generation_id].set()
                pending_requests[generation_id]["image"] = imgage_data
                logger.info(f"Received webhook data for generation id: {generation_id}")
            else:
                logger.warning(
                    f"No pending request found for generation id: {generation_id}"
                )

        # Check for post-processing completion event
        if job_type == "post_processing.completed":
            bg_removal_id = data["id"]
            generation_id = data["generatedImageId"]
            image_url = data["url"]

            # Get the pending requests and events
            pending_requests = request.app["pending_requests"]
            pending_events = request.app["pending_events"]

            # Update the pending request with background removal status and image URL
            if bg_removal_id in pending_events:
                pending_events[bg_removal_id].set()
                pending_requests[generation_id]["bg_removal_status"] = "complete"
                pending_requests[generation_id]["image_url"] = image_url
                logger.info(f"Received webhook data for bg removal id: {bg_removal_id}")
            else:
                logger.warning(
                    f"No pending request found for bg removal id: {bg_removal_id}"
                )

        return web.json_response({"status": "success"}, status=200)
    except json.JSONDecodeError:
        # Handle JSON decoding errors
        logger.error("Invalid JSON received by webhook_listener")
        if generation_id in pending_requests:
            pending_requests[generation_id]["error"] = "Invalid JSON received"
            pending_events[generation_id].set()
        return web.json_response({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        # Handle other exceptions
        logger.error(f"Error in webhook_listener: {str(e)}")
        if generation_id in pending_requests:
            pending_requests[generation_id]["error"] = str(e)
            pending_events[generation_id].set()
        return web.json_response({"error": str(e)}, status=500)
