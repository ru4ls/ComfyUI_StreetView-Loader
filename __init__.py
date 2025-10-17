# file: ComfyUI_StreetView-Loader\__init__.py

from .nodes.streetview_loader import StreetViewLoader
from .nodes.streetview_url_parser import StreetViewURLParser
from .nodes.streetview_pano_loader import StreetViewPanoLoader

NODE_CLASS_MAPPINGS = {
    "StreetViewLoader": StreetViewLoader,
    "StreetViewURLParser": StreetViewURLParser,
    "StreetViewPanoLoader": StreetViewPanoLoader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "StreetViewLoader": "Street View Loader",
    "StreetViewURLParser": "Street View URL Parser",
    "StreetViewPanoLoader": "Street View Pano Loader",
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']

print("------------------------------------------")
print("ComfyUI Street View Loader Node: Loaded.")
print("------------------------------------------")