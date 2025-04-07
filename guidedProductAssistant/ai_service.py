from django.conf import settings
from guidedProductAssistant.utils import productDetails
from openai import OpenAI
import openai

# genai.configure(api_key="AIzaSyABnL_dU_kIQ0lRMyFy7BpgsdO5AK9DY6Q")  # techteam 

def get_product_assistant_response(user_query, product_id):
    openai.api_key = settings.OPEN_AI_KEY
    product_info = str(productDetails(product_id))

    prompt = f"""
    You are an AI assistant for an e-commerce website. Your task is to provide clear and relevant answers based on the given product details.

    ### Instructions:
    1. Answer concisely based only on the product details provided.
    2. If the requested detail is missing, say: "Sorry, this information is not available for the product."
    3. Avoid raw data dumps—only provide direct human-readable responses.
    4. If the question is unrelated to the product, say: "I can only provide product-related information."

    ---

    ### Product Information:
    {product_info}

    ---

    ### User Query:
    {user_query}

    ### AI Response:
    """

    try:
        completion = openai.ChatCompletion.create(
            model="gpt-4",  # or use "gpt-3.5-turbo" for faster/cheaper responses
            messages=[
                {"role": "system", "content": "You are a helpful product assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )
        return completion.choices[0].message["content"].strip()

    except Exception as e:
        print("OpenAI error:", e)
        return "Sorry, something went wrong while processing your request."
