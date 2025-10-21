# file: ComfyUI_StreetView-Loader/nodes/streetview_pano_loader.py

import torch
import numpy as np
import os
from dotenv import load_dotenv
from PIL import Image
import cv2

from ..utils.connect_api_utils import fetch_streetview_image

# --- Load API Key ---
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
dotenv_path = os.path.join(parent_dir, '.env')
load_dotenv(dotenv_path=dotenv_path)
API_KEY_FROM_ENV = os.getenv("GOOGLE_STREET_VIEW_API_KEY")


class StreetViewPanoLoader:
    """
    A ComfyUI node that creates a panorama by fetching multiple Street View
    images and stitching them using OpenCV for a seamless result.
    """

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "location": ("STRING", {"multiline": False, "default": "46.6237597,8.0305018"}),
                "center_heading": ("FLOAT", {"default": 133.44, "min": 0, "max": 360, "step": 0.1, "display": "slider"}),
                "pitch": ("FLOAT", {"default": -5.0, "min": -90, "max": 90, "step": 0.1, "display": "slider"}),
                "fov_per_image": ("INT", {"default": 90, "min": 30, "max": 120, "step": 1, "display": "slider"}),
                "num_images": ("INT", {"default": 3, "min": 2, "max": 5, "step": 1, "display": "slider"}),
                "overlap_percentage": ("INT", {"default": 30, "min": 10, "max": 70, "step": 1, "display": "slider"}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("image", "metadata")
    FUNCTION = "load_panorama"
    CATEGORY = "Ru4ls/StreetView"

    def simple_stitch(self, images, width, height):
        """ Fallback function for a simple side-by-side stitch if OpenCV fails. """
        total_width = width * len(images)
        stitched_image = Image.new('RGB', (total_width, height))
        for i, img in enumerate(images):
            stitched_image.paste(img, (i * width, 0))
        return stitched_image

    def pil_to_tensor(self, image: Image.Image):
        image_np = np.array(image).astype(np.float32) / 255.0
        return torch.from_numpy(image_np)[None,]

    def load_panorama(self, location, center_heading, pitch, fov_per_image, num_images, overlap_percentage):
        if not API_KEY_FROM_ENV:
            raise ValueError("Google Street View API key not found in .env file.")

        images_pil = []
        width, height = 640, 640 # Fetch square images for max data
        
        # Calculate Headings Based on Overlap
        step_angle = fov_per_image * (1 - (overlap_percentage / 100.0))
        start_heading = center_heading - (step_angle * (num_images - 1) / 2.0)

        print(f"StreetView Pano: Fetching {num_images} images with {fov_per_image}° FOV and {overlap_percentage}% overlap.")
        
        for i in range(num_images):
            current_heading = (start_heading + i * step_angle) % 360
            print(f"  - Fetching image {i+1}/{num_images} at heading {current_heading:.2f}°...")
            image_pil, _ = fetch_streetview_image(API_KEY_FROM_ENV, location, current_heading, pitch, fov_per_image, width, height)
            if image_pil:
                images_pil.append(image_pil)

        if not images_pil:
            return (torch.zeros((1, height, width, 3), dtype=torch.float32), "Failed to fetch any images.")

        # --- OpenCV Stitching ---
        images_cv = [cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR) for img in images_pil]
        
        stitcher = cv2.Stitcher_create()
        (status, stitched_image_bgr) = stitcher.stitch(images_cv)
        
        if status == cv2.Stitcher_OK:
            print("StreetView Pano: OpenCV stitching successful!")
            stitched_image_rgb = cv2.cvtColor(stitched_image_bgr, cv2.COLOR_BGR2RGB)
            final_image = Image.fromarray(stitched_image_rgb)
            metadata = f"OpenCV Stitched {len(images_pil)} images. Final size: {final_image.width}x{final_image.height}"
        else:
            print(f"StreetView Pano: OpenCV stitching failed (Status code: {status}). Reason: Not enough matching features.")
            print("  - FALLING BACK to simple side-by-side stitching. Try increasing overlap or changing FOV.")
            final_image = self.simple_stitch(images_pil, width, height)
            metadata = f"STITCHING FAILED. Fallback to simple stitch. Size: {final_image.width}x{final_image.height}"
        
        final_tensor = self.pil_to_tensor(final_image)
        return (final_tensor, metadata)