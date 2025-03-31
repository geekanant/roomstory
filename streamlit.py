import streamlit as st
import requests
import time
import random
import tempfile
from PIL import Image

API_KEY = "67e3a2293a0da9a4f60d0a18"
BASE_URL = "https://api.reimaginehome.ai"
HEADERS = {
    "api-key": API_KEY,
    "Content-Type": "application/json"
}

def upload_image_to_imgbb(image_path):
    # You can use any image hosting API here, or serve locally
    with open(image_path, "rb") as file:
        response = requests.post(
            "https://api.imgbb.com/1/upload",
            params={"key": "193a62a7113a66b4a6e931b29fd5d605"},
            files={"image": file},
            verify=False
        )
    return response.json()["data"]["url"]

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
        "mask_category": "furnishing",
        "space_type": "ST-INT-003",
        "design_theme": design_theme,
        "masking_element": "",
        "color_preference": color_preference,
        "material_preference": "",
        "landscaping_preference": landscaping_preference,
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
    st.image(uploaded_file, caption="Uploaded Image", use_column_width=True)

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(uploaded_file.read())
        temp_path = tmp.name

    st.info("Uploading image to imgbb...")
    image_url = upload_image_to_imgbb(temp_path)
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
            st.image(mask_urls[0], caption="First Mask", use_column_width=True)

            # Get Preferences
            design_theme = random.choice(get_design_theme_list()["data"]["interior_themes"][0].values())
            color_pref = random.choice(get_color_preference_list()["data"]["color"])
            landscaping = random.choice(get_landscaping_preference_list()["data"]["pathways"])

            st.write(f"🎨 Theme: {design_theme}")
            st.write(f"🖌️ Colors: {color_pref}")
            st.write(f"🌿 Landscaping: {landscaping}")

            if st.button("Generate Designs"):
                with st.spinner("Generating new designs..."):
                    gen_job_id = generate_image(image_url, mask_urls, mask_categories, design_theme, color_pref, landscaping)
                    results = get_generated_image(gen_job_id)

                if results:
                    st.success("Designs generated successfully!")
                    for img_url in results:
                        st.image(img_url, use_column_width=True)
                else:
                    st.error("Image generation failed.")
        else:
            st.error("Mask creation failed.")
