from django.conf import settings
from guidedProductAssistant.utils import productDetails
from openai import OpenAI
from openai import OpenAIError
from openai.types.chat import ChatCompletionMessage
import os
client = OpenAI(api_key=settings.OPEN_AI_KEY)
GOOGLE_GEMINI_KEY = os.getenv("GOOGLE_GEMINI_API_KEY")
import google.generativeai as genai
client = OpenAI(api_key=settings.OPEN_AI_KEY)
if GOOGLE_GEMINI_KEY:
    genai.configure(api_key=GOOGLE_GEMINI_KEY)
else:
    print("WARNING: GOOGLE_GEMINI_API_KEY not set. Gemini fallback will not work.")
    
def ask_gemini(prompt):
    print("IN ASK GEMINI")
    if not GOOGLE_GEMINI_KEY:
        return "Gemini API error: API key not configured"
    try:
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        response = model.generate_content(prompt)
        print("RESPONSE:", response.text[:200])
        return response.text
    except Exception as e:
        print(f"Gemini error: {str(e)}")
        return f"Gemini API error: {str(e)}"
    
def get_product_assistant_response(user_query, product_id):
    products = productDetails(product_id)
    del products["ai_generated_description"]
    del products["ai_generated_title"]
    del products["ai_generated_features"]
    product_info = str(products)
    prompt = f"""
    You are an AI assistant for an e-commerce website. Your task is to provide clear and relevant answers based on the given product details.
    1. Answer concisely based only on the product details provided.
    2. If the requested detail is missing, say: "Sorry, this information is not available for the product."
    3. Avoid raw data dumps—only provide direct human-readable responses.
    4. If the question is unrelated to the product, say: "I can only provide product-related information."
    ---
    {product_info}
    ---
    {user_query}
    """
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful product assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )
        return response.choices[0].message.content.strip()
    except OpenAIError as e:
        print(f"An error occurred: {str(e)}" )
        return ask_gemini(prompt)
        
