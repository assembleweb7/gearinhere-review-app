# Gearinhere AI Review Generator – Streamlit App

import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import openai
from requests.auth import HTTPBasicAuth

openai.api_key = "YOUR_OPENAI_API_KEY"
WP_URL = "https://yourwordpresssite.com/wp-json/wp/v2/posts"
WP_USER = "your_wp_username"
WP_APP_PASSWORD = "your_wp_app_password"

def scrape_kickstarter(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    title = soup.find('meta', property='og:title')
    description = soup.find('meta', property='og:description')
    image = soup.find('meta', property='og:image')
    return {
        "title": title['content'] if title else None,
        "description": description['content'] if description else None,
        "image": image['content'] if image else None,
        "url": url,
        "scraped_at": datetime.utcnow().isoformat()
    }

def scrape_amazon(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, "html.parser")
    title = soup.find(id='productTitle')
    description = soup.find(id='feature-bullets')
    image = soup.find('img', {'id': 'landingImage'})
    return {
        "title": title.get_text(strip=True) if title else "Amazon Product",
        "description": description.get_text(strip=True) if description else "",
        "image": image['src'] if image else None,
        "url": url,
        "scraped_at": datetime.utcnow().isoformat()
    }

def generate_prompt(product_data):
    prompt = f"""
You are Gear, the guide of Gearinhere. Here's a new product to review.

Product Title: {product_data['title']}
Product Description: {product_data['description']}
Product URL: {product_data['url']}

Generate a structured review with these personas:

1. Gear – intro & overview
2. Spark – highlight innovation
3. Clarity – performance & comparison
4. Gaia – sustainability
5. Echo – user/community sentiment

End with a recommendation and call to action.
Output in markdown.
"""
    return prompt

def generate_review(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a product review assistant for Gearinhere."},
            {"role": "user", "content": prompt}
        ]
    )
    return response['choices'][0]['message']['content']

def post_to_wordpress(title, content, category_id=None, tags=None, publish_now=True):
    data = {
        'title': title,
        'content': content,
        'status': 'publish' if publish_now else 'draft',
    }
    if category_id:
        data['categories'] = [category_id]
    if tags:
        data['tags'] = tags
    response = requests.post(WP_URL, json=data, auth=HTTPBasicAuth(WP_USER, WP_APP_PASSWORD))
    return response.status_code, response.json()

# --- Streamlit Interface ---
st.title("Gearinhere AI Review Generator")

url_input = st.text_input("Enter Product URL (Kickstarter or Amazon):")
source_option = st.selectbox("Select Source", ["kickstarter", "amazon"])
category = st.text_input("Set Category (e.g., crowdfunding, eco-gear):")
tags = st.text_input("Tags (comma-separated):")
save_as_draft = st.checkbox("Save as Draft instead of Publishing")
auto_refresh = st.checkbox("Enable Auto-Refresh for this product (daily)")

if st.button("Generate & Preview Review"):
    with st.spinner("Scraping product data..."):
        data = scrape_amazon(url_input) if source_option == "amazon" else scrape_kickstarter(url_input)

    if data['image']:
        try:
            st.image(data['image'], caption="Product Image Preview", use_container_width=True)
        except Exception as e:
            st.warning("Image preview failed to load.")
    else:
        st.info("No image found for this product.")

    st.subheader("Scraped Product Info")
    st.write(f"**Title:** {data['title']}")
    st.write(f"**Description:** {data['description'][:200]}...")

    with st.spinner("Generating AI Review..."):
        prompt = generate_prompt(data)
        full_review = generate_review(prompt)

    st.subheader("Generated Review")
    st.markdown(full_review, unsafe_allow_html=True)

    custom_edit = st.text_area("Edit Before Publishing:", full_review, height=300)

    if st.button("Publish to WordPress"):
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        status, result = post_to_wordpress(
            data['title'], custom_edit, category_id=None, tags=tag_list, publish_now=not save_as_draft)
        if status == 201:
            st.success(f"Published successfully! Post ID: {result['id']}")
        else:
            st.error("Failed to publish. Check credentials or connection.")

    if auto_refresh:
        st.info("Auto-refresh is enabled. (Backend scheduler setup required)")
