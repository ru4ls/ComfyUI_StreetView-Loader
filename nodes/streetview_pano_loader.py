# file: ComfyUI_StreetView-Loader/nodes/streetview_pano_loader.py

import torch
import numpy as np
import os
from dotenv import load_dotenv
from PIL import Image

# We can reuse the exact same utility function! This is the power of good refactoring.
from ..utils.connect_api_utils import fetch_streetview_image

# --- Load API Key from .env file ---
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
dotenv_path = os.path.join(parent_dir, '.env')
load_dotenv(dotenv_path=dotenv_path)
API_KEY_FROM_ENV = os.getenv("GOOGLE_STREET_VIEW_API_KEY")


class StreetViewPanoLoader:
    """
    A ComfyUI node to load a panoramic image by fetching multiple Google Street
    View images with different headings and stitching them side-by-side.
    """

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "location": ("STRING", {"multiline": False, "default": "46.6237597,8.0305018"}), # Switzerland example
                "center_heading": ("FLOAT", {"default": 133.44, "min": 0, "max": 360, "step": 0.1, "display": "slider"}),
                "pitch": ("FLOAT", {"default": -5.0, "min": -90, "max": 90, "step": 0.1, "display": "slider"}),
                "fov_per_image": ("INT", {"default": 90, "min": 30, "max": 120, "step": 1, "display": "slider"}),
                "num_images": ("INT", {"default": 3, "min": 2, "max": 5, "step": 1, "display": "slider"}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("image", "metadata")
    FUNCTION = "load_panorama"
    CATEGORY = "Ru4ls/StreetView"

    def load_panorama(self, location, center_heading, pitch, fov_per_image, num_images):
        if not API_KEY_FROM_ENV:
            raise ValueError("Google Street View API key not found in .env file.")

        images = []
        # We will fetch 640x640 images as they give the most vertical data for stitching.
        width, height = 640, 640
        
        # --- Calculate Headings for Each Image ---
        # This determines how far apart each camera shot is.
        # For a simple side-by-side stitch, the step angle is equal to the field of view.
        step_angle = fov_per_image
        
        # Calculate the heading for the very first (leftmost) image
        start_heading = center_heading - (step_angle * (num_images - 1) / 2.0)

        print(f"StreetView Pano: Fetching {num_images} images with {fov_per_image}° FOV each.")
        
        for i in range(num_images):
            # Calculate the heading for the current shot in the sequence
            current_heading = (start_heading + i * step_angle) % 360
            
            print(f"  - Fetching image {i+1}/{num_images} at heading {current_heading:.2f}°...")
            
            # Fetch a single image using our existing utility function
            image_pil, _ = fetch_streetview_image(
                api_key=API_KEY_FROM_ENV,
                location=location,
                heading=current_heading,
                pitch=pitch,
                fov=fov_per_image,
                width=width,
                height=height
            )
            if image_pil:
                images.append(image_pil)

        if not images:
            print("StreetView Pano: Failed to fetch any images.")
            blank_image = torch.zeros((1, height, width, 3), dtype=torch.float32)
            return (blank_image, "Failed to fetch any images.")

        # --- Stitch the Images Together ---
        total_width = width * len(images)
        stitched_image = Image.new('RGB', (total_width, height))
        
        for i, img in enumerate(images):
            stitched_image.paste(img, (i * width, 0))
        
        print(f"StreetView Pano: Stitching complete. Final size: {total_width}x{height}")

        # Convert the final stitched PIL image to the tensor format ComfyUI expects
        final_tensor = self.pil_to_tensor(stitched_image)
        metadata = f"Stitched {len(images)} images. Center Heading: {center_heading}, Total Width: {total_width}px"
        
        return (final_tensor, metadata)

    def pil_to_tensor(self, image: Image.Image):
        image_np = np.array(image).astype(np.float32) / 255.0
        return torch.from_numpy(image_np)[None,]