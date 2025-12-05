# file: ComfyUI_StreetView-Loader\nodes\streetview_loader.py

import torch
import numpy as np
import os
from dotenv import load_dotenv
from PIL import Image

# Import the refactored API call function from our utility file
from ..utils.connect_api_utils import fetch_streetview_image

# --- Load API Key from .env file ---
# This logic finds the .env file in the parent directory (ComfyUI_StreetView-Loader)
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
dotenv_path = os.path.join(parent_dir, '.env')

# Load the environment variables from the found .env file
load_dotenv(dotenv_path=dotenv_path)

# Get the API key from the loaded environment variables
API_KEY_FROM_ENV = os.getenv("GOOGLE_STREET_VIEW_API_KEY")


class StreetViewLoader:
    """
    A ComfyUI node to load images directly from the Google Street View Static API,
    using a secret API key stored in a .env file and aspect ratio presets.
    """

    @classmethod
    def INPUT_TYPES(s):
        """
        Defines the input fields for the node. Width and height are now controlled
        by a user-friendly aspect ratio dropdown menu.
        """
        return {
            "required": {
                "location": ("STRING", {
                    "multiline": False,
                    "default": "40.720032,-73.988354" # Example: Near Katz's Deli, NYC
                }),
                "heading": ("FLOAT", {"default": 151.78, "min": 0, "max": 360, "step": 0.1, "display": "slider"}),
                "pitch": ("FLOAT", {"default": -0.76, "min": -90, "max": 90, "step": 0.1, "display": "slider"}),
                "fov": ("INT", {"default": 90, "min": 10, "max": 120, "step": 1, "display": "slider"}),
                "aspect_ratio": ([
                    "1:1 Square (640x640)",
                    "16:9 Widescreen (640x360)",
                    "9:16 Vertical (360x640)",
                    "4:3 Classic (640x480)",
                    "3:2 Photography (640x427)"
                    ],),
            },
            # NEW: Optional input for Historical Date ID (Panorama ID)
            "optional": {
                "historical_date_id": ("STRING", {"default": "", "multiline": False, "tooltip": "Enter a panorama ID to load a historical image from a specific date"}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("image", "metadata")
    FUNCTION = "load_image"
    CATEGORY = "Ru4ls/StreetView"

    def load_image(self, location, heading, pitch, fov, aspect_ratio, historical_date_id=""):

        if not API_KEY_FROM_ENV:
            raise ValueError("Google Street View API key not found in .env file. Please ensure GOOGLE_STREET_VIEW_API_KEY is set in ComfyUI_StreetView-Loader/.env")

        # Logic to determine width and height based on the selected aspect ratio
        if aspect_ratio == "1:1 Square (640x640)":
            width, height = 640, 640
        elif aspect_ratio == "16:9 Widescreen (640x360)":
            width, height = 640, 360
        elif aspect_ratio == "9:16 Vertical (360x640)":
            width, height = 360, 640
        elif aspect_ratio == "4:3 Classic (640x480)":
            width, height = 640, 480
        elif aspect_ratio == "3:2 Photography (640x427)":
            width, height = 640, 427
        else:
            # Fallback to a default just in case
            width, height = 640, 640

        # Call the refactored utility function with the calculated width and height.
        # Logic: If historical_date_id is provided, pass it. It overrides the location.
        image_pil, metadata = fetch_streetview_image(
            api_key=API_KEY_FROM_ENV,
            location=location,
            pano_id=historical_date_id,  # Pass the ID here
            heading=heading,
            pitch=pitch,
            fov=fov,
            width=width,
            height=height
        )

        # Convert the returned PIL image to the tensor format ComfyUI expects.
        image_tensor = self.pil_to_tensor(image_pil)

        return (image_tensor, metadata)

    def pil_to_tensor(self, image: Image.Image):
        """ Helper function to convert a PIL Image to a PyTorch Tensor for ComfyUI. """
        image_np = np.array(image).astype(np.float32) / 255.0
        # Add the batch dimension [None,] which is equivalent to unsqueeze(0)
        return torch.from_numpy(image_np)[None,]