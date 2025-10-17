import re

class StreetViewURLParser:
    """
    A ComfyUI node that takes a Google Maps Street View URL and parses it
    into its constituent parts: location, heading, pitch, and fov.
    """
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "url": ("STRING", {
                    "multiline": True, 
                    "default": "Paste a Google Maps Street View URL here"
                }),
            }
        }

    RETURN_TYPES = ("STRING", "FLOAT", "FLOAT", "INT")
    RETURN_NAMES = ("location", "heading", "pitch", "fov")
    FUNCTION = "parse_url"
    CATEGORY = "Ru4ls/StreetView/Utils" # A sub-category for utilities

    def parse_url(self, url):
        # Default values in case parsing fails
        location = "40.720032,-73.988354"
        heading = 151.78
        pitch = -0.76
        fov = 90

        if not url or "google.com/maps" not in url:
            print("Invalid URL provided. Using default values.")
            return (location, heading, pitch, fov)

        # --- Use Regular Expressions to find the parameters ---

        # 1. Parse Location (latitude,longitude)
        # Looks for the @ symbol followed by two numbers separated by a comma
        loc_match = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", url)
        if loc_match:
            lat = loc_match.group(1)
            lon = loc_match.group(2)
            location = f"{lat},{lon}"

        # 2. Parse Heading, Pitch, and FOV
        # Looks for the data block like ",3a,75y,273.99h,85.73t"
        params_match = re.search(r",(\d+\.?\d*)y,(\d+\.?\d*)h,(\d+\.?\d*)t", url)
        if params_match:
            # FOV is the number before 'y'
            fov = int(float(params_match.group(1)))
            
            # Heading is the number before 'h'
            heading = float(params_match.group(2))
            
            # Pitch from URL needs conversion for the API
            # URL pitch (t): 90 is horizontal.
            # API pitch: 0 is horizontal.
            # Conversion: API_pitch = URL_t - 90
            url_pitch = float(params_match.group(3))
            pitch = url_pitch - 90.0

        print(f"Parsed URL: Location={location}, Heading={heading}, Pitch={pitch}, FOV={fov}")
        
        return (location, heading, pitch, fov)