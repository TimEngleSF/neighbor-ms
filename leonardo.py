import os
import logging

import aiohttp
from aiohttp import web
from pprint import pprint
import aiofiles

from config import LEONARDO_KEY, PROCESSED_IMG_DIR

logger = logging.getLogger(__name__)


class LeonardoGeneration:
    def __init__(self, prompt: str):
        self.generation_id = None
        self.image_id = None
        self.bg_removal_id = None
        self.prompt = prompt

        self.img_url = None
        self.processed_img_url = None

        self.processed_filename = None
        self.processed_filepath = None

        self.payload = payload_template.copy()
        self.payload["prompt"] = self.prompt

        self.generation_req_url = "https://cloud.leonardo.ai/api/rest/v1/generations"
        self.bg_removal_req_url = (
            "https://cloud.leonardo.ai/api/rest/v1/variations/nobg"
        )

    # async func to request img generation from Leonardo
    async def generate_img(self) -> str:
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {LEONARDO_KEY}",
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.generation_req_url, json=self.payload, headers=headers, ssl=False
            ) as response:
                if response.status != 200:
                    raise Exception("error in generating image from Leonardo")
                # Parse data
                parsed_response = await response.json()
                sd_generation_job = parsed_response["sdGenerationJob"]
                self.generation_id = sd_generation_job["generationId"]
                return self.generation_id

    async def request_bg_removal(self) -> str:
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {LEONARDO_KEY}",
        }

        payload = {"id": self.image_id, "isVariation": False}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.bg_removal_req_url, json=payload, headers=headers, ssl=False
            ) as response:
                if response.status != 200:

                    raise Exception(
                        "Error in removing background from Leonardo",
                    )
                # Parse data
                parsed_response = await response.json()
                self.bg_removal_id = parsed_response["sdNobgJob"]["id"]
                return self.bg_removal_id

    async def save_processed_img(self, session):
        try:
            # Request the processed image
            async with session.get(self.processed_img_url, ssl=False) as response:
                if response.status == 200:
                    content = await response.read()
                    # Generate filename and filepath for the processed image
                    self.processed_filename = self.bg_removal_id + ".png"
                    self.processed_filepath = os.path.join(
                        PROCESSED_IMG_DIR, self.processed_filename
                    )
                    # Save the processed image to disk
                    async with aiofiles.open(self.processed_filepath, "wb") as file:
                        await file.write(content)
                    logger.info(f"Processed image saved to {self.processed_filepath}")
                else:
                    raise Exception(
                        f"Failed to download image, status code: {response.status}"
                    )
        except aiohttp.ClientError as e:
            logger.error(f"Client error while downloading image: {e}")
            raise
        except OSError as e:
            logger.error(f"File operation error while saving image: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise


# payload_template = {
#     "alchemy": False,
#     "presetStyle": "DYNAMIC",
#     "modelId": "b24e16ff-06e3-43eb-8d33-4416c2d75876",
#     "controlnets": None,
#     "negative_prompt": "",
#     "height": 512,
#     "width": 512,
#     "num_images": 1,
#     "public": False,
#     "guidance_scale": 0,
# }


payload_template = {
    "alchemy": True,
    "presetStyle": "ILLUSTRATION",
    "modelId": "e71a1c2f-4f80-4800-934f-2c68979d8cc8",
    "controlnets": [
        {
            "initImageId": "8863b6b0-7d4f-4e25-b26a-795bea37a1df",
            "initImageType": "UPLOADED",
            "preprocessorId": 67,
            "strengthType": "High",
        },
        {
            "initImageId": "9ed196f0-318e-4b5d-a80b-47998267f861",
            "initImageType": "UPLOADED",
            "preprocessorId": 67,
            "strengthType": "High",
        },
        {
            "initImageId": "4c12a068-3156-4891-9ee1-ba04532a61e2",
            "initImageType": "UPLOADED",
            "preprocessorId": 67,
            "strengthType": "High",
        },
        {
            "initImageId": "8ec571c9-8552-408a-b453-8409179e6628",
            "initImageType": "UPLOADED",
            "preprocessorId": 67,
            "strengthType": "High",
        },
        {
            "initImageId": "a8dfc503-8971-4891-ac24-7cb0a28beffc",
            "initImageType": "UPLOADED",
            "preprocessorId": 67,
            "strengthType": "High",
        },
        {
            "initImageId": "c50357d2-cdb5-4b64-a9e4-feb3bd980bc0",
            "initImageType": "UPLOADED",
            "preprocessorId": 67,
            "strengthType": "High",
        },
    ],
    "negative_prompt": "full body shots, lower body, legs, feet, complex backgrounds, text, logos, watermarks, animals, secondary characters, clutter, blurriness, pixelation, low resolution, distorted features, dramatic lighting, shadows, reflections, unrealistic proportions, exaggerated expressions, overly detailed clothing, fantasy elements, sci-fi elements, abstract shapes, surrealism, head out of frame, more than 10 fingers, nudity, blurry eyes, two heads, plastic look, deformed or poorly drawn features, mutations, extra limbs, missing limbs, floating or disconnected limbs, long necks or bodies, close-ups, black and white, grainy texture, extra fingers, bad anatomy, bad proportions, blind or dead eyes, vignette, over saturation, monochrome.",
    "height": 896,
    "width": 512,
    "num_images": 1,
    "public": False,
    "guidance_scale": 10,
}
