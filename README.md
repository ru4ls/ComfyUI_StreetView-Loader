# ComfyUI Street View Loader Node

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)


A custom node for ComfyUI that allows you to load images directly from Google Street View to use as backgrounds, textures, or inputs in your workflows.

Instead of manually taking screenshots, this node programmatically fetches a clean, high-resolution image from any location on Earth with Street View coverage, giving you precise control over the camera angle, direction, and field of view.

![Street View Loader Node combine with NanoBanana in ComfyUI](media/preview.png)

---

## Why Use This Node? The Power of "Ground Truth"

While standard text-to-image models are incredible at *imagining* locations ("a charming street in Paris"), they struggle to recreate the **exact appearance and layout** of a specific, real-world place. Their output is an approximation, an artistic blend of countless images.

This node solves that problem by providing **photographic ground truth**. It pulls the real, pixel-for-pixel view of a location, ensuring your generations are anchored in reality.

This gives you the best of both worlds: the authenticity of a real photograph combined with the creative power of AI.

### Key Advantages & Use Cases

*   **Guaranteed Location Accuracy:** When you need the background to be recognizably *your* street, a specific landmark, or a favorite travel spot, this node is the only way to guarantee a 100% accurate representation. The composition, architecture, and lighting are real, not AI-generated guesswork.

*   **The Ultimate Base for `img2img` and ControlNet:** This is the most powerful use case. You can feed the real Street View image into your workflow as a base for:
    *   **Stylization:** Keep the exact composition of a place while transforming it into an oil painting, an anime scene, or a charcoal sketch.
    *   **Restoration/Re-imagining:** Take a view of an old neighborhood and use AI to add futuristic elements, or render it as it might have looked in a different historical period.
    *   **Precise Inpainting:** Add characters, objects, or fantastical elements into a real-world scene with a background that is perfectly stable and coherent.

*   **Virtual Location Scouting:** For concept artists, filmmakers, and game developers. You can instantly scout real-world locations from your desktop, pull them into ComfyUI, and experiment with different styles and moods for your project without ever leaving your chair.

*   **Personalized and Sentimental Art:** Create a unique piece of art based on a place with personal meaning—a childhood home, a proposal spot, or a favorite vacation view. This creates a connection that a generic prompt could never achieve.

*   **Consistent Backgrounds for Testing:** When testing LoRAs, IPAdapters, or character models, using a consistent, real-world background from this node ensures that you are only seeing the changes from your model, not the random variations of a `txt2img` background.

![Street View Loader Node combine with NanoBanana in ComfyUI](media/preview_2.png)

## Features
- **Direct API Integration:** Pulls images directly from the Google Street View Static API.
- **Full Camera Control:** Adjust Location, Heading (pan), Pitch (tilt), and Field of View (zoom).
- **Secure API Key Storage:** Uses a `.env` file to keep your API key safe and out of your workflow files.
- **Clean Output:** No UI overlays, just the pure image.
- **Easy Workflow Integration:** Outputs a standard `IMAGE` tensor and a metadata string (the fetch URL) for debugging.

---

## 1. Installation

1.  Navigate to your ComfyUI `custom_nodes` directory:
    ```bash
    cd ComfyUI/custom_nodes/
    ```

2.  Clone this repository:
    ```bash
    git clone https://github.com/ru4ls/ComfyUI_StreetView-Loader.git
    ```

3.  Install the required Python dependencies. Open a terminal, navigate to the new `ComfyUI_StreetView-Loader` folder, and run:
    ```bash
    pip install -r requirements.txt
    ```
    * this will install the `requests` and `python-dotenv` libraries, which are required for this node.*

4.  **Restart ComfyUI.**

---

## 2. Setup: Getting Your Google API Key (Crucial Step)

This node requires a Google Cloud API key to function. Google provides a generous **$200/month free credit**, which is more than enough for extensive personal use without any charge.

### Step-by-Step Guide

**Part A: Create Project & Enable API**
1.  Go to the [Google Cloud Console](https://console.cloud.google.com/).
2.  If you don't have a project, create one. If you do, click the project selector at the top and click **"New Project"**. Give it a name like `ComfyUI-API`.
3.  Once the project is created, search for "API Library" in the top search bar.
4.  In the library, search for and select **"Street View Static API"**.
5.  Click the **"Enable"** button.

**Part B: Set Up Billing**
6.  You will be prompted to link a billing account. This is required, but you will **not be charged** unless you exceed the $200 free monthly credit (equivalent to tens of thousands of image requests).

**Part C: Create and Secure Your API Key**
7.  In the Cloud Console search bar, navigate to **"Credentials"**.
8.  Click **"+ Create Credentials"** and select **"API key"**.
9.  Your new API key will be displayed. **Copy this key immediately.**
10. **(IMPORTANT!)** Click the **"Edit API key"** button. Under "API restrictions," select **"Restrict key"**.
11. In the dropdown, find and check **"Street View Static API"**, then click "OK". This ensures your key can *only* be used for this purpose, protecting your account. Click **"Save"**.

**Part D: Configure the Node**
12. In your `ComfyUI/custom_nodes/ComfyUI_StreetView-Loader/` folder, create a new file named `.env`. or rename an existing `.env.example` file to `.env`.
13. Open this `.env` file and add your copied API key in the following format:
    ```
    GOOGLE_STREET_VIEW_API_KEY="your_actual_api_key_goes_here"
    ```
14. Save the file.

Your setup is now complete!

---

## 3. How to Use

1.  After restarting ComfyUI, double-click the canvas and search for **"Street View Loader"**.
2.  The node will appear with several input fields.

### Finding Your Parameters

The best way to get the exact `location`, `heading`, `pitch`, and `fov` is to use the Google Maps URL.

1.  Open [Google Maps](https://maps.google.com) and drop into Street View at your desired location.
2.  Pan, tilt, and zoom the camera until you frame the perfect shot.
3.  Look at the URL in your browser's address bar. It will look like this:
    `https://www.google.com/maps/@**40.74844,-73.98566**,3a,**75**y,**273.99**h,**85.73**t/data=...`

    -   `@**40.74844,-73.98566**`: This is the **`location`**.
    -   `**75**y`: This is the **`fov`** (Field of View / Zoom).
    -   `**273.99**h`: This is the **`heading`**.
    -   `**85.73**t`: This is related to the **`pitch`**. The API uses a range of -90 (straight down) to +90 (straight up) with 0 being the horizon. A `t` value of `90` in the URL is roughly a `pitch` of `0` for the API. Adjust as needed.

4.  Copy these values into the corresponding fields on the node and generate!

### **The Easy Way: Using the URL Parser Node**

As of version 2.0, the recommended workflow is to use the **Street View URL Parser** node. This node extracts all the camera parameters automatically from a single Google Maps URL.

1.  Add two nodes to your workflow:
    -   `Street View URL Parser` (found in `Ru4ls/StreetView/Utils`)
    -   `Street View Loader`

2.  Find the exact view you want in Google Street View on your browser.

3.  Copy the **entire URL** from your browser's address bar.

4.  Paste the URL into the `url` field of the **Parser** node.

5.  Connect the outputs of the Parser node to the inputs of the Loader node (`location` to `location`, `heading` to `heading`, etc.).


This method is faster, easier, and less error-prone than manually entering each parameter.

### Node Inputs
- `location`: The latitude and longitude (e.g., `40.74844,-73.98566`).
- `heading`: The compass direction [0 to 360]. 0 is North, 90 is East, 180 is South, 270 is West.
- `pitch`: The up/down tilt of the camera [-90 to 90]. 0 is the horizon.
- `fov`: The field of view, or zoom [10 to 120]. A lower number is more zoomed in.
- `width` / `height`: The dimensions of the output image (max 640x640 for the free API).

---

## 4. Troubleshooting

-   **Node throws a `ValueError: API key not found`:** Your `.env` file is missing, in the wrong location, or the variable name is not `GOOGLE_STREET_VIEW_API_KEY`. It must be in the `ComfyUI_StreetView-Loader` folder.
-   **The node outputs a black image:** This almost always means Google has no Street View imagery for that exact coordinate, or the API key is invalid/restricted. Check your key's restrictions in the Google Cloud Console and try a slightly different coordinate. The `metadata` output will contain an error message.
-   **The node doesn't appear in ComfyUI:** Ensure you have fully restarted the ComfyUI server after installation.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.