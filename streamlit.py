import streamlit as st
import requests
import time
import random
import cloudinary
import cloudinary.uploader
import tempfile
from PIL import Image
from io import BytesIO

API_KEY = "67e3a2293a0da9a4f60d0a18"
BASE_URL = "https://api.reimaginehome.ai"
HEADERS = {
    "api-key": API_KEY,
    "Content-Type": "application/json"
}

CLOUD_NAME = "dj4uxgxqp"
UPLOAD_PRESET = "testunsigned"


def upload_to_cloudinary(image, filename):
    """Uploads a PIL image to Cloudinary and returns the public URL."""
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    buffer.seek(0)

    url = f"https://api.cloudinary.com/v1_1/{CLOUD_NAME}/image/upload"
    payload = {
        "upload_preset": UPLOAD_PRESET,
        "public_id": filename,
        "folder": "object_crops/"
    }
    files = {"file": ("image.jpg", buffer, "image/jpeg")}

    response = requests.post(url, data=payload, files=files, verify=False)
    
    if response.status_code == 200:
        return response.json().get("secure_url")
    else:
        st.error(f"Cloudinary Upload Error: {response.text}")
        return None

def create_mask(image_url):
    url = f"{BASE_URL}/v1/create_mask"
    payload = {"image_url": image_url}
    response = requests.post(url, json=payload, headers=HEADERS, verify=False)
    return response.json()

def get_mask_status(job_id):
    url = f"{BASE_URL}/v1/create_mask/{job_id}"
    response = requests.get(url, headers=HEADERS, verify=False)
    return response.json()

def get_design_theme_list():
    url = f"{BASE_URL}/v1/get-design-theme-list"
    return requests.get(url, headers=HEADERS, verify=False).json()

def get_color_preference_list():
    url = f"{BASE_URL}/v1/get-color-preference-list"
    return requests.get(url, headers=HEADERS, verify=False).json()

def get_landscaping_preference_list():
    url = f"{BASE_URL}/v1/get-landscaping-preference-list"
    return requests.get(url, headers=HEADERS, verify=False).json()

def generate_image(image_url, mask_urls, mask_categories, design_theme, color_preference, landscaping_preference):
    url = f"{BASE_URL}/v1/generate_image"
    payload = {
        "image_url": image_url,
        "mask_urls": mask_urls,
        "mask_category": "furnishing",  # Multiple categories combined
        "space_type": "ST-INT-003",
        "design_theme": "DT-INT-008",
        "masking_element": "",
        "color_preference": "green,yellow,black",
        "material_preference": "",
        "landscaping_preference": "",
        "generation_count": 3,
        "webhook_url": "https://example.com/mywebhook/endpoint"
    }
    response = requests.post(url, json=payload, headers=HEADERS, verify=False).json()
    return response.get("data", {}).get("job_id")

def get_generated_image(job_id):
    url = f"{BASE_URL}/v1/generate_image/{job_id}"
    while True:
        response = requests.get(url, headers=HEADERS, verify=False).json()
        job_status = response.get("data", {}).get("job_status")
        if job_status == "done":
            return response.get("data", {}).get("generated_images", [])
        elif job_status == "error":
            return []
        time.sleep(15)

# ------------------- Streamlit UI -------------------
st.title("🏠 Roomstory - Interior AI")
uploaded_file = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(uploaded_file, caption="Uploaded Image", use_container_width=True)

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(uploaded_file.read())
        temp_path = tmp.name

    st.info("Uploading image to imgbb...")
    image_url = upload_to_cloudinary(image, filename="reimagine_input")
    st.success("Image uploaded!")

    st.info("Creating mask...")
    mask_response = create_mask(image_url)

    if mask_response.get("status") == "success":
        job_id = mask_response["data"]["job_id"]

        with st.spinner("Waiting for mask processing..."):
            while True:
                status = get_mask_status(job_id)
                if status.get("data", {}).get("job_status") in ["done", "error"]:
                    break
                time.sleep(10)

        if status["data"]["job_status"] == "done":
            masks = status["data"]["masks"]
            mask_urls = [m["url"] for m in masks]
            mask_categories = list(set(cat for m in masks for cat in m["category"].split(",")))

            st.success("Mask created!")
            st.image(mask_urls[0], caption="First Mask", use_container_width=True)


            # if st.button("Generate Designs"):
            with st.spinner("Generating new designs..."):
                gen_job_id = generate_image(image_url, mask_urls, mask_categories, "", "", "")
                results = get_generated_image(gen_job_id)

            if results:
                st.success("Designs generated successfully!")
                for img_url in results:
                    st.image(img_url, use_container_width=True)
            else:
                st.error("Image generation failed.")
        else:
            st.error("Mask creation failed.")
