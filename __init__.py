# file: ComfyUI_StreetView-Loader\__init__.py

from .nodes.streetview_loader import StreetViewLoader
from .nodes.streetview_url_parser import StreetViewURLParser
from .nodes.streetview_pano_loader import StreetViewPanoLoader
from .nodes.streetview_animator import StreetViewAnimator
from .nodes.streetview_cubemap_loader import StreetViewCubemapLoader
from .nodes.streetview_equirectangular_loader import StreetViewEquirectangularLoader

NODE_CLASS_MAPPINGS = {
    "StreetViewLoader": StreetViewLoader,
    "StreetViewURLParser": StreetViewURLParser,
    "StreetViewPanoLoader": StreetViewPanoLoader,
    "StreetViewAnimator": StreetViewAnimator,
    "StreetViewCubemapLoader": StreetViewCubemapLoader,
    "StreetViewEquirectangularLoader": StreetViewEquirectangularLoader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "StreetViewLoader": "Street View Loader",
    "StreetViewURLParser": "Street View URL Parser",
    "StreetViewPanoLoader": "Street View Pano Loader",
    "StreetViewAnimator": "Street View Animator",
    "StreetViewCubemapLoader": "Street View Cubemap Loader",
    "StreetViewEquirectangularLoader": "Street View Equirectangular Loader",
}

print("------------------------------------------")
print("ComfyUI Street View Loader Node: Loaded.")
print("------------------------------------------")