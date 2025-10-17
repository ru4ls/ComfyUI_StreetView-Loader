# file: ComfyUI_StreetView-Loader\nodes\streetview_loader.py

import torch
import numpy as np
import os
from dotenv import load_dotenv
from PIL import Image

from ..utils.connect_api_utils import fetch_streetview_image

# --- Load API Key from .env file ---
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
    using a secret API key stored in a .env file.
    """
    
    @classmethod
    def INPUT_TYPES(s):
        """
        Defines the input fields for the node. The API key is handled in the
        background and is not exposed as an input in the UI.
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
                "width": ("INT", {"default": 512, "min": 64, "max": 640, "step": 8}),
                "height": ("INT", {"default": 512, "min": 64, "max": 640, "step": 8}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("image", "metadata")
    FUNCTION = "load_image"
    CATEGORY = "Ru4ls/StreetView"

    def load_image(self, location, heading, pitch, fov, width, height):

        if not API_KEY_FROM_ENV:
            raise ValueError("Google Street View API key not found in .env file. Please ensure GOOGLE_STREET_VIEW_API_KEY is set in ComfyUI_StreetView-Loader/.env")

        image_pil, metadata = fetch_streetview_image(
            api_key=API_KEY_FROM_ENV,
            location=location,
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
        return torch.from_numpy(image_np)[None,]