import json
import re
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from openai import OpenAI, OpenAIError
from guidedProductAssistant.models import product
from product_assistant.crud import DatabaseModel
client = OpenAI(api_key=settings.OPEN_AI_KEY)
EDITOR_SYSTEM_PROMPT = """You are a senior industrial ecommerce content editor.
Your content should be optimized for both Search Engine Optimization (SEO) and
Generative Engine Optimization (GEO). Write naturally as if prepared by an
experienced human catalog editor. Use factual, concise, trustworthy language.
Avoid AI-style writing patterns, repetitive phrasing, generic marketing
language, and exaggerated claims. Do not invent specifications or technical
details. Only use information supplied about the product. Before returning the
response, revise it once to make it read naturally and professionally."""
REWRITE_SYSTEM_PROMPT = """You are a senior industrial ecommerce content editor.
Rewrite content so it sounds naturally human-written. Improve Search Engine
Optimization (SEO) and Generative Engine Optimization (GEO). Preserve technical
accuracy. Do not invent specifications. Avoid AI-style wording, repetitive
phrasing, and promotional language."""
def call_openai(prompt, system_prompt=EDITOR_SYSTEM_PROMPT,
                model="gpt-4", temperature=0.3, max_tokens=None):
    try:
        kwargs = dict(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
        )
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content.strip()
    except OpenAIError as e:
        print("OpenAI Error:", e)
        return None
def product_prompt_info(p):
    return f"""
            Product Name: {p.product_name}
            Brand: {p.brand_name}
            SKU: {p.sku_number_product_code_item_number}
            MPN: {getattr(p, 'mpn', '')}
            """
TITLE_PROMPT = """
            Generate one product title.
            Product Information:
{prompt_info}
            Requirements:
            - Create one SEO and GEO optimized product title.
            - Sound natural and human-written.
            - Include the product name naturally.
            - Keep under 120 characters.
            - Use Title Case.
            - Do not invent specifications.
            - Include the brand when available.
            - Do NOT include the SKU, MPN, UPC/EAN, model number, or any internal product codes.
            - Do NOT add prices, quantities, or marketing words like "best", "cheap", "discount".
            - Do not use promotional language.
            Return only the title.
            """
FEATURES_PROMPT = """
            Generate one product feature list.
            Product Information:
{prompt_info}
            Existing Feature Text (if any): {existing_features}
            Requirements:
            - Produce one feature list.
            - Include 6-8 concise bullet points.
            - Optimize for SEO and GEO.
            - Write naturally.
            - Focus on factual product information.
            - Mention applications, materials, compatibility and specifications when available.
            - Do not invent information.
            - Avoid promotional language.
            - Avoid AI-style wording.
            Return only the bullet list.
            """
DESCRIPTION_PROMPT = """
            Generate one product description.
            Product Information:
{prompt_info}
            Existing Supplier Description (if any): {existing_description}
            Do NOT copy the supplier description. Treat it only as a factual
            reference. Generate a completely original, SEO ranking-level product
            description written for the Ireland market.
            The description must:
            - Be maximum 2 to 3 paragraphs (no more).
            - Be fully original — no mirrored sentence structure or phrasing from any source.
            - Preserve every factual detail found in the sources — no detail lost, no detail invented.
            - Read naturally for an eCommerce audience (tone, spelling, and market context suited to the Ireland audience).
            - Include primary and secondary product keywords naturally, in a way that supports search ranking.
            - Avoid keyword stuffing.
            - Avoid unsupported marketing claims or generic filler ("industry-leading", "best-in-class", etc.) unless explicitly sourced.
            - Be approximately 150–200 words total across the paragraphs, unless available source content is significantly shorter.
            - Contain only real product facts — no invented benefits, no invented use cases.
            - Optimize for SEO and Generative Engine Optimization (GEO).
            - Do not invent specifications.
            Avoid phrases such as:
            - Introducing...
            - Meet...
            - Whether you're...
            - Designed for...
            - Perfect for...
            - Unlock...
            - High-quality...
            - Reliable solution...
            Return only the description.
            """
REWRITE_TITLE_PROMPT = """
                        You are a senior industrial ecommerce content editor.
                        Rewrite the following product title.
                        Requested improvement:
{selected_option}
                        Original Title:
{original}
                        Goals:
                        - Improve readability.
                        - Sound naturally human-written.
                        - Improve SEO and GEO.
                        - Preserve technical accuracy.
                        - Do not invent specifications.
                        - Do NOT include the SKU, MPN, UPC/EAN, model number, or any internal product codes.
                        - Do NOT add prices, quantities, or marketing words like "best", "cheap", "discount".
                        - Avoid AI-style wording.
                        - Avoid promotional language.
                        Return only the rewritten title.
                        """
REWRITE_FEATURES_PROMPT = """
                        You are a senior ecommerce content editor.
                        Rewrite the following product features.
                        Requested improvement:
{selected_option}
                        Original Features:
{original}
                        Goals:
                        - Improve readability.
                        - Sound naturally human-written.
                        - Preserve technical accuracy.
                        - Improve SEO and GEO.
                        - Do not invent specifications.
                        Return only the rewritten bullet list.
                        """
REWRITE_DESCRIPTION_PROMPT = """
                    You are a senior ecommerce content editor.
                    Rewrite the following product description.
                    Requested improvement:
{selected_option}
                    Original Description:
{original}
                    Goals:
                    - Improve readability.
                    - Improve grammar.
                    - Sound naturally human-written.
                    - Preserve technical accuracy.
                    - Improve SEO and GEO.
                    - Remove repetitive wording.
                    - Do not invent specifications.
                    Return only the rewritten description.
                    """
def parse_title(text):
    return text.strip().strip('"').strip("'")
def parse_features(text):
    return [
        line.strip("-•*0123456789. ").strip()
        for line in text.splitlines()
        if line.strip()
        and (
            line.strip().startswith(("-", "•", "*"))
            or re.match(r"^\d+\.", line.strip())
        )
    ]
def parse_description(text):
    return text.strip()
GENERATE_SPECS = {
    "title": {
        "prompt": TITLE_PROMPT,
        "parse": parse_title,
        "needs_existing": False,
    },
    "features": {
        "prompt": FEATURES_PROMPT,
        "parse": parse_features,
        "needs_existing": True,
        "existing_field": "features",
    },
    "description": {
        "prompt": DESCRIPTION_PROMPT,
        "parse": parse_description,
        "needs_existing": True,
        "existing_field": "long_description",
    },
}
REWRITE_SPECS = {
    "title": {"prompt": REWRITE_TITLE_PROMPT, "parse": parse_title},
    "features": {"prompt": REWRITE_FEATURES_PROMPT, "parse": parse_features},
    "description": {"prompt": REWRITE_DESCRIPTION_PROMPT, "parse": parse_description},
}

