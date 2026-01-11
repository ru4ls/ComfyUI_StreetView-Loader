# file: ComfyUI_StreetView-Loader/nodes/streetview_equirectangular_loader.py

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


class StreetViewEquirectangularLoader:
    """
    A ComfyUI node that creates an equirectangular panoramic image by fetching
    6 Street View images (front, back, left, right, top, bottom) and converting them to equirectangular format.
    """

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "location": ("STRING", {"multiline": False, "default": "-6.1954402,106.8234648"}),
                "face_resolution": ([
                    "256x256", "512x512", "640x640"
                ], {"default": "640x640"}), # Max 640 for Street View Static API
                "upscale_factor": ("INT", {"default": 2, "min": 1, "max": 4, "step": 1}),
                "upscale_method": (["LANCZOS", "BICUBIC", "BILINEAR", "NEAREST"], {"default": "LANCZOS"}),
                "interpolation_mode": (["BILINEAR", "NEAREST"], {"default": "BILINEAR"}),
            },
            "optional": {
                "historical_date_id": ("STRING", {"default": "", "multiline": False, "tooltip": "Enter a panorama ID to load a historical equirectangular image from a specific date. Requires Street View Image Metadata API enabled on GCP."}),
            }
        }

    RETURN_TYPES = ("IMAGE", "IMAGE", "IMAGE", "IMAGE", "IMAGE", "IMAGE", "IMAGE", "STRING")
    RETURN_NAMES = ("equirectangular_image", "front", "back", "left", "right", "top", "bottom", "metadata")
    FUNCTION = "load_equirectangular"
    CATEGORY = "Ru4ls/StreetView"

    def pil_to_tensor(self, image: Image.Image):
        image_np = np.array(image).astype(np.float32) / 255.0
        return torch.from_numpy(image_np)[None,]

    def is_valid_image(self, image: Image.Image):
        img_array = np.array(image)
        if img_array.ndim == 2:
            img_array = np.stack([img_array]*3, axis=-1)

        dark_pixels = np.sum(img_array < 30)
        total_pixels = img_array.size

        if dark_pixels / total_pixels > 0.95:
            return False
        if np.std(img_array) < 5:
            return False
        return True

    def cube_to_equirectangular(self, faces_pil_dict, interpolation_mode):
        cube_side = faces_pil_dict["front"].width
        if any(face.width != cube_side or face.height != cube_side for face in faces_pil_dict.values()):
            raise ValueError("All cube map faces must be square and of the same dimensions.")

        equi_width = 2 * cube_side
        equi_height = cube_side

        faces_np_dict = {name: np.array(img) for name, img in faces_pil_dict.items()}
        equi_img_np = np.zeros((equi_height, equi_width, 3), dtype=np.uint8)

        # Vectorized computation for better performance
        y_coords, x_coords = np.mgrid[0:equi_height, 0:equi_width]

        # Convert equirectangular coordinates to spherical coordinates
        lon = (x_coords / equi_width - 0.5) * 2 * np.pi
        lat = (0.5 - y_coords / equi_height) * np.pi

        # Convert spherical to Cartesian coordinates
        x_cart = np.cos(lat) * np.sin(lon)
        y_cart = np.sin(lat)
        z_cart = np.cos(lat) * np.cos(lon)

        abs_X = np.abs(x_cart)
        abs_Y = np.abs(y_cart)
        abs_Z = np.abs(z_cart)

        # Determine which face each pixel maps to
        face_mask_x = (abs_X >= abs_Y) & (abs_X >= abs_Z)  # X-axis faces (Right/Left)
        face_mask_y = (abs_Y >= abs_X) & (abs_Y >= abs_Z)  # Y-axis faces (Top/Bottom)
        face_mask_z = (abs_Z >= abs_X) & (abs_Z >= abs_Y)  # Z-axis faces (Front/Back)

        # Initialize face assignment matrix
        face_assignment = np.full((equi_height, equi_width), "", dtype=object)

        # Assign faces based on direction
        # X-axis faces (Right/Left)
        right_mask = face_mask_x & (x_cart > 0)
        left_mask = face_mask_x & (x_cart <= 0)
        face_assignment[right_mask] = "back"  # Right Face (+X_cart) -> should map to Back
        face_assignment[left_mask] = "front"  # Left Face (-X_cart) -> should map to Front

        # Y-axis faces (Top/Bottom)
        top_mask = face_mask_y & (y_cart > 0)
        bottom_mask = face_mask_y & (y_cart <= 0)
        face_assignment[top_mask] = "top"
        face_assignment[bottom_mask] = "bottom"

        # Z-axis faces (Front/Back)
        front_mask = face_mask_z & (z_cart > 0)
        back_mask = face_mask_z & (z_cart <= 0)
        face_assignment[front_mask] = "right"  # Front Face (+Z_cart) -> should map to Right
        face_assignment[back_mask] = "left"   # Back Face (-Z_cart) -> should map to Left

        # Calculate UV coordinates for each face type
        u_coords = np.zeros((equi_height, equi_width))
        v_coords = np.zeros((equi_height, equi_width))

        with np.errstate(divide='ignore', invalid='ignore'):
            # X-axis faces (Right/Left)
            u_coords[right_mask] = -z_cart[right_mask] / x_cart[right_mask]
            v_coords[right_mask] = y_cart[right_mask] / x_cart[right_mask]
            u_coords[left_mask] = z_cart[left_mask] / x_cart[left_mask]
            v_coords[left_mask] = y_cart[left_mask] / x_cart[left_mask]

            # Y-axis faces (Top/Bottom)
            u_coords[top_mask] = x_cart[top_mask] / y_cart[top_mask]
            v_coords[top_mask] = -z_cart[top_mask] / y_cart[top_mask]
            u_coords[bottom_mask] = x_cart[bottom_mask] / y_cart[bottom_mask]
            v_coords[bottom_mask] = z_cart[bottom_mask] / y_cart[bottom_mask]

            # Z-axis faces (Front/Back)
            u_coords[front_mask] = x_cart[front_mask] / z_cart[front_mask]
            v_coords[front_mask] = y_cart[front_mask] / z_cart[front_mask]
            u_coords[back_mask] = -x_cart[back_mask] / z_cart[back_mask]
            v_coords[back_mask] = y_cart[back_mask] / z_cart[back_mask]

        # Clamp UV coordinates to valid range [-1, 1] and convert to pixel coordinates
        u_coords = np.clip(u_coords, -1, 1)
        v_coords = np.clip(v_coords, -1, 1)
        px_u = np.clip((u_coords * 0.5 + 0.5) * cube_side, 0, cube_side - 1)
        px_v = np.clip((v_coords * 0.5 + 0.5) * cube_side, 0, cube_side - 1)

        # Process each face separately
        for face_name in faces_np_dict.keys():
            face_mask = face_assignment == face_name
            if not np.any(face_mask):
                continue

            # Get the face's pixel data
            face_data = faces_np_dict[face_name]

            # Get the corresponding u,v coordinates for this face
            face_u = px_u[face_mask].astype(int)
            face_v = px_v[face_mask].astype(int)

            # Sample pixels from the face
            sampled_pixels = face_data[face_v, face_u]

            # Assign to output
            equi_img_np[face_mask] = sampled_pixels

        return Image.fromarray(equi_img_np)

    def load_equirectangular(self, location, face_resolution, upscale_factor, upscale_method, interpolation_mode, historical_date_id=""):
        if not API_KEY_FROM_ENV:
            raise ValueError("Google Street View API key not found in .env file.")

        res_parts = face_resolution.split('x')
        width, height = int(res_parts[0]), int(res_parts[1])

        # Calculate the upscaling dimensions
        upscaled_width = width * upscale_factor
        upscaled_height = height * upscale_factor

        face_orientations = {
            "front": (0, 0),       # Heading 0, Pitch 0
            "right": (90, 0),      # Heading 90, Pitch 0
            "back": (180, 0),      # Heading 180, Pitch 0
            "left": (270, 0),      # Heading 270, Pitch 0
            "top": (0, 90),        # Heading 0, Pitch 90
            "bottom": (0, -90)     # Heading 0, Pitch -90
        }

        face_images_tensors = {}
        faces_pil_for_conversion = {}
        face_metadata = []
        successful_fetches = 0

        print(f"StreetView Equirectangular: Fetching 6 images for cube faces at resolution {width}x{height}, then upscaling by factor {upscale_factor} to {upscaled_width}x{upscaled_height}.")

        for face_name, (heading, pitch) in face_orientations.items():
            print(f"  - Fetching {face_name} face at heading {heading}°, pitch {pitch}°, fov 90°...")

            fetch_params = {
                "api_key": API_KEY_FROM_ENV,
                "heading": heading,
                "pitch": pitch,
                "fov": 90,
                "width": width,
                "height": height
            }
            if historical_date_id:
                fetch_params["pano_id"] = historical_date_id
            else:
                fetch_params["location"] = location

            try:
                image_pil, metadata_url = fetch_streetview_image(**fetch_params)

                if image_pil:
                    # --- CRUCIAL ROTATIONS AND FLIPS for Street View API specific orientations ---
                    if face_name == "left":
                        image_pil = image_pil.transpose(Image.FLIP_LEFT_RIGHT)
                    elif face_name == "front":
                        image_pil = image_pil.transpose(Image.FLIP_LEFT_RIGHT)
                    elif face_name == "right":
                        image_pil = image_pil.transpose(Image.FLIP_TOP_BOTTOM)
                    elif face_name == "back":
                        image_pil = image_pil.transpose(Image.FLIP_TOP_BOTTOM)
                    elif face_name == "top":
                        image_pil = image_pil.transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.ROTATE_270)
                    elif face_name == "bottom":
                        image_pil = image_pil.transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.ROTATE_270)

                    # Upscale the image after applying rotations
                    if upscale_factor > 1:
                        # Map upscale method to PIL resampling algorithm
                        upscale_map = {
                            "LANCZOS": Image.LANCZOS,
                            "BICUBIC": Image.BICUBIC,
                            "BILINEAR": Image.BILINEAR,
                            "NEAREST": Image.NEAREST
                        }
                        resample_method = upscale_map.get(upscale_method, Image.LANCZOS)
                        image_pil = image_pil.resize((upscaled_width, upscaled_height), resample_method)

                if image_pil and self.is_valid_image(image_pil):
                    face_images_tensors[face_name] = self.pil_to_tensor(image_pil)
                    faces_pil_for_conversion[face_name] = image_pil
                    face_metadata.append(f"{face_name}: {metadata_url}")
                    successful_fetches += 1
                else:
                    print(f"  - Failed to fetch {face_name} face or received invalid image, using gray placeholder.")
                    gray_pil = Image.new('RGB', (upscaled_width, upscaled_height), color=(64, 64, 64))
                    face_images_tensors[face_name] = self.pil_to_tensor(gray_pil)
                    faces_pil_for_conversion[face_name] = gray_pil

            except Exception as e:
                print(f"  - Error fetching {face_name} face: {str(e)}")
                gray_pil = Image.new('RGB', (upscaled_width, upscaled_height), color=(64, 64, 64))
                face_images_tensors[face_name] = self.pil_to_tensor(gray_pil)
                faces_pil_for_conversion[face_name] = gray_pil

        if successful_fetches == 0:
            print("StreetView Equirectangular: Failed to fetch any valid cube faces.")
            empty_tensor = torch.zeros((1, upscaled_height, upscaled_width, 3), dtype=torch.float32)
            return (empty_tensor,) * 7 + ("Failed to fetch any cube faces.",)

        equirectangular_image_pil = self.cube_to_equirectangular(faces_pil_for_conversion, interpolation_mode)

        equirectangular_tensor = self.pil_to_tensor(equirectangular_image_pil)

        metadata = f"Successfully created equirectangular panorama. Fetched {successful_fetches}/6 faces. Cube face resolution: {width}x{height}, Upscaled to: {upscaled_width}x{upscaled_height}, Equirectangular resolution: {equirectangular_image_pil.width}x{equirectangular_image_pil.height}, FOV: 90°, Upscale factor: {upscale_factor}, Upscale method: {upscale_method}\n"
        metadata += "\n".join(face_metadata)

        return equirectangular_tensor, face_images_tensors["front"], face_images_tensors["back"], face_images_tensors["left"], face_images_tensors["right"], face_images_tensors["top"], face_images_tensors["bottom"], metadata