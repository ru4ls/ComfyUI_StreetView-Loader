# file: ComfyUI_StreetView-Loader\utils\connect_api_utils.py

import requests
from PIL import Image
from io import BytesIO

def fetch_streetview_image(api_key, location, heading, pitch, fov, width, height, pano_id=""):
    """
    Connects to the Google Street View API and fetches an image.

    Returns:
        A tuple containing (PIL.Image, metadata_url_string) on success,
        or (error_image, error_message_string) on failure.
    """
    base_url = "https://maps.googleapis.com/maps/api/streetview"

    params = {
        "size": f"{width}x{height}",
        "heading": heading,
        "pitch": pitch,
        "fov": fov,
        "key": api_key,
        "return_error_codes": "true"
    }

    # CRITICAL LOGIC:
    # If a Pano ID is provided, use it. It overrides the location.
    if pano_id and pano_id.strip() != "":
        params["pano"] = pano_id
    else:
        params["location"] = location

    try:
        response = requests.get(base_url, params=params, timeout=20)
        response.raise_for_status()

        # Check for "ZERO_RESULTS" or other API errors which still return a 200 OK status.
        # A valid JPEG starts with bytes FF D8. A valid PNG starts with 89 50 4E 47.
        is_valid_image = response.content.startswith(b'\xff\xd8') or response.content.startswith(b'\x89PNG')

        if not is_valid_image:
            error_message = "API returned no image for this location. It might not be available."
            print(f"StreetView Info: {error_message}")
            error_img = Image.new('RGB', (width, height), color='black')
            return (error_img, error_message)

        # Success case
        image_pil = Image.open(BytesIO(response.content)).convert("RGB")
        metadata_url = requests.Request('GET', base_url, params=params).prepare().url
        print(f"StreetView URL: {metadata_url}")
        return (image_pil, metadata_url)

    except requests.exceptions.RequestException as e:
        error_message = f"An API request error occurred: {e}"
        print(error_message)
        error_img = Image.new('RGB', (width, height), color='black')
        return (error_img, error_message)