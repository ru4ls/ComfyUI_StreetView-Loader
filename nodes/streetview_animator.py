# file: ComfyUI_StreetView-Loader/nodes/streetview_animator.py

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


class StreetViewAnimator:
    """
    A ComfyUI node to animate StreetView parameters (heading, pitch, fov) over time,
    generating a sequence of images based on duration and FPS settings.
    """
    
    @classmethod
    def INPUT_TYPES(s):
        """
        Defines the input fields for the animation node.
        Includes start/end values for heading, pitch, fov, and animation settings.
        """
        return {
            "required": {
                "location": ("STRING", {
                    "multiline": False, 
                    "default": "40.720032,-73.988354" # Example: Near Katz's Deli, NYC
                }),
                # Start values for animation
                "start_heading": ("FLOAT", {"default": 0.0, "min": 0, "max": 360, "step": 0.1, "display": "slider"}),
                "end_heading": ("FLOAT", {"default": 360.0, "min": 0, "max": 360, "step": 0.1, "display": "slider"}),
                "start_pitch": ("FLOAT", {"default": 0.0, "min": -90, "max": 90, "step": 0.1, "display": "slider"}),
                "end_pitch": ("FLOAT", {"default": 0.0, "min": -90, "max": 90, "step": 0.1, "display": "slider"}),
                "start_fov": ("INT", {"default": 90, "min": 10, "max": 120, "step": 1, "display": "slider"}),
                "end_fov": ("INT", {"default": 90, "min": 10, "max": 120, "step": 1, "display": "slider"}),
                "duration": ("FLOAT", {"default": 5.0, "min": 0.1, "max": 60.0, "step": 0.1, "display": "slider"}),
                "fps": ("INT", {"default": 24, "min": 1, "max": 60, "step": 1, "display": "slider"}),
                "aspect_ratio": ([
                    "1:1 Square (640x640)", 
                    "16:9 Widescreen (640x360)", 
                    "9:16 Vertical (360x640)",
                    "4:3 Classic (640x480)",
                    "3:2 Photography (640x427)"
                ],),
                "interpolation": ([
                    "linear",  # Smooth linear transition
                    "ease_in", # Slow start, accelerate
                    "ease_out", # Fast start, decelerate
                    "ease_in_out" # Slow start, fast middle, slow end
                ], {"default": "linear"}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "metadata")
    FUNCTION = "animate_streetview"
    CATEGORY = "Ru4ls/StreetView/Animation"

    def linear_interpolation(self, start_val, end_val, progress):
        """Linear interpolation between two values."""
        return start_val + (end_val - start_val) * progress

    def ease_in_interpolation(self, start_val, end_val, progress):
        """Ease-in interpolation (slow start)."""
        return start_val + (end_val - start_val) * (progress ** 2)

    def ease_out_interpolation(self, start_val, end_val, progress):
        """Ease-out interpolation (slow end)."""
        return start_val + (end_val - start_val) * (1 - (1 - progress) ** 2)

    def ease_in_out_interpolation(self, start_val, end_val, progress):
        """Ease-in-out interpolation (slow start and end)."""
        if progress < 0.5:
            return start_val + (end_val - start_val) * (2 * progress ** 2)
        else:
            return start_val + (end_val - start_val) * (1 - (-2 * progress + 2) ** 2 / 2)

    def animate_streetview(self, location, start_heading, end_heading, start_pitch, end_pitch, start_fov, end_fov, duration, fps, aspect_ratio, interpolation):
        if not API_KEY_FROM_ENV:
            raise ValueError("Google Street View API key not found in .env file. Please ensure GOOGLE_STREET_VIEW_API_KEY is set in ComfyUI_StreetView-Loader/.env")

        # Determine width and height based on the selected aspect ratio
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
            width, height = 640, 640

        # Calculate total frames based on duration and fps
        total_frames = int(duration * fps)
        if total_frames < 1:
            total_frames = 1

        # Select interpolation function based on parameter
        interp_func = self.linear_interpolation
        if interpolation == "ease_in":
            interp_func = self.ease_in_interpolation
        elif interpolation == "ease_out":
            interp_func = self.ease_out_interpolation
        elif interpolation == "ease_in_out":
            interp_func = self.ease_in_out_interpolation

        # Generate frames
        image_tensors = []
        for frame in range(total_frames):
            progress = frame / (total_frames - 1) if total_frames > 1 else 0.0
            
            # Interpolate parameters based on progress
            current_heading = interp_func(start_heading, end_heading, progress)
            current_pitch = interp_func(start_pitch, end_pitch, progress)
            current_fov = int(interp_func(start_fov, end_fov, progress))
            
            # Ensure fov is within valid range
            current_fov = max(10, min(120, current_fov))

            # Handle heading wrap-around (0 to 360 degrees)
            if abs(end_heading - start_heading) > 180:  # Wrap-around case
                if end_heading > start_heading:
                    current_heading = start_heading + ((current_heading - start_heading + 180) % 360) - 180
                else:
                    current_heading = start_heading + ((current_heading - start_heading - 180) % 360) + 180

            # Normalize heading to 0-360 range
            current_heading = current_heading % 360
            if current_heading < 0:
                current_heading += 360

            # Fetch the image for this frame
            image_pil, metadata = fetch_streetview_image(
                api_key=API_KEY_FROM_ENV,
                location=location,
                heading=current_heading,
                pitch=current_pitch,
                fov=current_fov,
                width=width,
                height=height
            )

            # Convert the returned PIL image to the tensor format ComfyUI expects
            image_tensor = self.pil_to_tensor(image_pil)
            image_tensors.append(image_tensor)

        # Stack all frames into a single tensor
        if image_tensors:
            stacked_images = torch.cat(image_tensors, dim=0)
            metadata = f"Animation: {total_frames} frames, {duration}s at {fps}fps. Parameters: heading ({start_heading:.1f}° to {end_heading:.1f}°), pitch ({start_pitch:.1f}° to {end_pitch:.1f}°), fov ({start_fov} to {end_fov}). Interpolation: {interpolation}"
        else:
            # Fallback to single black image if no frames were generated
            stacked_images = torch.zeros((1, height, width, 3), dtype=torch.float32)
            metadata = "Error: No frames were generated for animation"

        return (stacked_images, metadata)

    def pil_to_tensor(self, image: Image.Image):
        """ Helper function to convert a PIL Image to a PyTorch Tensor for ComfyUI. """
        image_np = np.array(image).astype(np.float32) / 255.0
        # Add the batch dimension [None,] which is equivalent to unsqueeze(0)
        return torch.from_numpy(image_np)[None,]