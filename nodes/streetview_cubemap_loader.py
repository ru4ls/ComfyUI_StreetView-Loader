# file: ComfyUI_StreetView-Loader/nodes/streetview_cubemap_loader.py

import torch
import numpy as np
import os
from dotenv import load_dotenv
from PIL import Image

from ..utils.connect_api_utils import fetch_streetview_image

# --- Load API Key ---
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
dotenv_path = os.path.join(parent_dir, '.env')
load_dotenv(dotenv_path=dotenv_path)
API_KEY_FROM_ENV = os.getenv("GOOGLE_STREET_VIEW_API_KEY")


class StreetViewCubemapLoader:
    """
    A ComfyUI node that creates a cubemap by fetching 6 Street View
    images at specific orientations (front, back, left, right, up, down)
    to form the 6 faces of a cube map for 3D applications.
    """

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "location": ("STRING", {"multiline": False, "default": "46.6237597,8.0305018"}),
                "face_resolution": ([
                    "256x256", "512x512", "640x640", "1024x1024"
                ], {"default": "512x512"}),
                "output_mode": ([
                    "individual_faces", 
                    "merged_cross", 
                    "merged_hstrip", 
                    "merged_vstrip"
                ], {"default": "merged_cross"}),
            }
        }

    RETURN_TYPES = ("IMAGE", "IMAGE", "IMAGE", "IMAGE", "IMAGE", "IMAGE", "IMAGE", "STRING")
    RETURN_NAMES = ("front", "back", "left", "right", "up", "down", "merged_cubemap", "metadata")
    FUNCTION = "load_cubemap"
    CATEGORY = "Ru4ls/StreetView/Environment"

    def pil_to_tensor(self, image: Image.Image):
        image_np = np.array(image).astype(np.float32) / 255.0
        return torch.from_numpy(image_np)[None,]

    def is_valid_image(self, image: Image.Image):
        """
        Check if the image is valid (not completely black or filled with a single color).
        This helps detect when the Street View API returns placeholder images.
        """
        # Convert to numpy array
        img_array = np.array(image)
        
        # Check if it's mostly black (typical for failed API requests)
        # If more than 90% of pixels are very dark, consider it invalid
        dark_pixels = np.sum(img_array < 30)  # pixels with values under 30/255
        total_pixels = img_array.size
        
        # If more than 90% of pixels are very dark, it's likely a failed request
        if dark_pixels / total_pixels > 0.9:
            return False
            
        # Also check if the image is filled with a uniform color (another failure indicator)
        # Calculate the standard deviation of pixel values; low std indicates uniform color
        if np.std(img_array) < 5:  # If standard deviation is very low, it's likely a uniform color
            return False
            
        return True

    def create_merged_cubemap(self, face_images, output_mode):
        """
        Create a merged cubemap texture based on the selected output mode.
        """
        if not face_images:
            return None

        # Get the dimensions of the faces
        width = face_images["front"].width
        height = face_images["front"].height

        if output_mode == "merged_cross":
            # Create a cross layout: up in center top, left-front-right-back in middle row, down in center bottom
            # Cross layout: 3 columns x 4 rows, with the side faces in the middle row
            cross_width = 4 * width
            cross_height = 3 * height
            
            merged_image = Image.new('RGB', (cross_width, cross_height), (0, 0, 0))
            
            # Place faces in cross layout
            # Up face at top center (column 1, row 0)
            merged_image.paste(face_images["up"], (width, 0))
            
            # Middle row: left, front, right, back
            merged_image.paste(face_images["left"], (0, height))
            merged_image.paste(face_images["front"], (width, height))
            merged_image.paste(face_images["right"], (width * 2, height))
            merged_image.paste(face_images["back"], (width * 3, height))
            
            # Down face at bottom center (column 1, row 2)
            merged_image.paste(face_images["down"], (width, height * 2))
            
        elif output_mode == "merged_hstrip":
            # Horizontal strip layout: all 6 faces in a single row
            strip_width = 6 * width
            strip_height = height
            
            merged_image = Image.new('RGB', (strip_width, strip_height), (0, 0, 0))
            
            # Order: right, left, up, down, front, back (common for some 3D engines)
            merged_image.paste(face_images["right"], (0, 0))  # Right
            merged_image.paste(face_images["left"], (width, 0))  # Left
            merged_image.paste(face_images["up"], (2 * width, 0))  # Up
            merged_image.paste(face_images["down"], (3 * width, 0))  # Down
            merged_image.paste(face_images["front"], (4 * width, 0))  # Front
            merged_image.paste(face_images["back"], (5 * width, 0))  # Back
            
        elif output_mode == "merged_vstrip":
            # Vertical strip layout: all 6 faces in a single column
            strip_width = width
            strip_height = 6 * height
            
            merged_image = Image.new('RGB', (strip_width, strip_height), (0, 0, 0))
            
            # Order: right, left, up, down, front, back
            merged_image.paste(face_images["right"], (0, 0))  # Right
            merged_image.paste(face_images["left"], (0, height))  # Left
            merged_image.paste(face_images["up"], (0, 2 * height))  # Up
            merged_image.paste(face_images["down"], (0, 3 * height))  # Down
            merged_image.paste(face_images["front"], (0, 4 * height))  # Front
            merged_image.paste(face_images["back"], (0, 5 * height))  # Back
            
        else:
            # Default to individual faces if mode is invalid
            return None
            
        return merged_image

    def load_cubemap(self, location, face_resolution, output_mode):
        if not API_KEY_FROM_ENV:
            raise ValueError("Google Street View API key not found in .env file.")

        # Determine width and height for each face based on resolution selection
        if face_resolution == "256x256":
            width, height = 256, 256
        elif face_resolution == "512x512":
            width, height = 512, 512
        elif face_resolution == "640x640":
            width, height = 640, 640
        elif face_resolution == "1024x1024":
            width, height = 1024, 1024
        else:
            width, height = 512, 512

        # Define the 6 face orientations for the cubemap
        # For perfect cubemap geometry, we use 90° FOV for all faces
        # Note: For up/down faces, extreme pitch values (+90/-90) may not work with Street View API,
        # so we use near-vertical values that are more likely to succeed while maintaining 90° FOV
        face_orientations = {
            "front": (0, 0),       # Facing forward
            "back": (180, 0),      # Facing backward  
            "left": (270, 0),      # Facing left
            "right": (90, 0),      # Facing right
            "up": (0, 90),         # Looking up (with 90° FOV - may fail but geometrically correct)
            "down": (0, -90)       # Looking down (with 90° FOV - may fail but geometrically correct)
        }

        face_images = {}
        face_metadata = []
        successful_fetches = 0

        print(f"StreetView Cubemap: Fetching 6 images for cubemap faces at resolution {width}x{height}.")
        
        # Fetch each face of the cubemap using 90° FOV for all faces (optimal for cubemap geometry)
        for face_name, (heading, pitch) in face_orientations.items():
            print(f"  - Fetching {face_name} face at heading {heading}°, pitch {pitch}°, fov 90°...")
            try:
                image_pil, metadata_url = fetch_streetview_image(
                    API_KEY_FROM_ENV, location, heading, pitch, 90, width, height  # Always use 90° FOV for proper cubemap geometry
                )
                
                # Check if the image is valid (not all black, which often indicates API failure at extreme angles)
                if image_pil and self.is_valid_image(image_pil):
                    face_images[face_name] = image_pil
                    face_metadata.append(f"{face_name}: {metadata_url}")
                    successful_fetches += 1
                else:
                    # For up/down faces, try a fallback pitch if the extreme pitch failed
                    if face_name in ["up", "down"]:
                        fallback_pitch = 85 if face_name == "up" else -85
                        print(f"  - {face_name} face failed with {pitch}° pitch, trying {fallback_pitch}°...")
                        
                        fallback_image, fallback_metadata_url = fetch_streetview_image(
                            API_KEY_FROM_ENV, location, heading, fallback_pitch, 90, width, height
                        )
                        
                        if fallback_image and self.is_valid_image(fallback_image):
                            face_images[face_name] = fallback_image
                            face_metadata.append(f"{face_name}: (fallback) {fallback_metadata_url}")
                            successful_fetches += 1
                            print(f"  - Successfully fetched {face_name} face with fallback pitch {fallback_pitch}°")
                        else:
                            print(f"  - Failed to fetch {face_name} face with fallback, using gray placeholder.")
                            face_images[face_name] = Image.new('RGB', (width, height), color=(64, 64, 64))  # Gray fallback
                    else:
                        # For non-up/down faces, use fallback immediately
                        print(f"  - Failed to fetch {face_name} face, using fallback image.")
                        face_images[face_name] = Image.new('RGB', (width, height), color=(64, 64, 64))  # Gray fallback
            except Exception as e:
                print(f"  - Error fetching {face_name} face: {str(e)}")
                face_images[face_name] = Image.new('RGB', (width, height), color=(64, 64, 64))  # Gray fallback

        if successful_fetches == 0:
            empty_tensor = torch.zeros((1, height, width, 3), dtype=torch.float32)
            return (empty_tensor,) * 6 + (empty_tensor, "Failed to fetch any cubemap faces.")

        # Convert each face to tensor if we're only outputting individual faces
        # Convert individual faces to tensors
        front_tensor = self.pil_to_tensor(face_images["front"])
        back_tensor = self.pil_to_tensor(face_images["back"])
        left_tensor = self.pil_to_tensor(face_images["left"])
        right_tensor = self.pil_to_tensor(face_images["right"])
        up_tensor = self.pil_to_tensor(face_images["up"])
        down_tensor = self.pil_to_tensor(face_images["down"])

        # Create merged cubemap based on selected mode
        if output_mode in ["merged_cross", "merged_hstrip", "merged_vstrip"]:
            merged_image = self.create_merged_cubemap(face_images, output_mode)
            merged_tensor = self.pil_to_tensor(merged_image) if merged_image else torch.zeros((1, height, width, 3), dtype=torch.float32)
        else:  # individual_faces
            # For individual faces mode, create a blank merged tensor
            merged_tensor = torch.zeros((1, height, width, 3), dtype=torch.float32)

        # Prepare metadata string
        if output_mode == "individual_faces":
            metadata = f"Successfully created cubemap with {successful_fetches}/6 faces. Resolution: {width}x{height}, FOV: 90°, Output mode: {output_mode}\n"
        else:
            metadata = f"Successfully created cubemap with {successful_fetches}/6 faces. Resolution: {width}x{height}, FOV: 90°, Output mode: {output_mode}\n"
        metadata += "\n".join(face_metadata)

        return (front_tensor, back_tensor, left_tensor, right_tensor, up_tensor, down_tensor, merged_tensor, metadata)