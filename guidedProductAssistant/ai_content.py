"""
DRY refactor of fetchAiContent + regenerateAiContents.

Drop this into your Django app (e.g. ai_content.py) and import the two
views into urls.py:

    from .ai_content import fetchAiContent, regenerateAiContents
"""

import json
import re

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from openai import OpenAI, OpenAIError

from guidedProductAssistant.models import product
from product_assistant.crud import DatabaseModel


client = OpenAI(api_key=settings.OPEN_AI_KEY)


# ──────────────────────────────────────────────────────────────
# Shared system prompts
# ──────────────────────────────────────────────────────────────
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


# ──────────────────────────────────────────────────────────────
# One OpenAI helper used by both views
# ──────────────────────────────────────────────────────────────
def call_openai(prompt, system_prompt=EDITOR_SYSTEM_PROMPT,
                model="gpt-4", temperature=0.3, max_tokens=None):
    """Call ChatGPT and return the stripped content, or None on failure."""
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


# ──────────────────────────────────────────────────────────────
# Prompt builders
# ──────────────────────────────────────────────────────────────
def product_prompt_info(p):
    return f"""
            Product Name: {p.product_name}
            Brand: {p.brand_name}
            SKU: {p.sku_number_product_code_item_number}
            MPN: {getattr(p, 'mpn', '')}
            """


# -- Generate (fetchAiContent) prompts --
TITLE_PROMPT = """
            Generate one product title.

            Product Information:
{prompt_info}

            Requirements:
            - Create one SEO and GEO optimized product title.
            - Sound natural and human-written.
            - Include the product name naturally.
            - Include the brand and model when available.
            - Keep under 120 characters.
            - Use Title Case.
            - Do not invent specifications.
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


# -- Regenerate (regenerateAiContents) prompts --
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


# ──────────────────────────────────────────────────────────────
# Parsers — one per field, shared by generate & regenerate
# ──────────────────────────────────────────────────────────────
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


# Field spec: prompt template + parser + (optionally) model settings
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


# ──────────────────────────────────────────────────────────────
# Views
# ──────────────────────────────────────────────────────────────
@csrf_exempt
def fetchAiContent(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    data = json.loads(request.body)
    product_id = data.get("product_id")

    try:
        product_obj = product.objects.get(id=product_id)
    except product.DoesNotExist:
        return JsonResponse({"error": "Product not found"}, status=404)

    prompt_info = product_prompt_info(product_obj)
    result = {}
    update_obj = {}

    for field, spec in GENERATE_SPECS.items():
        if not data.get(field):
            continue

        fmt_kwargs = {"prompt_info": prompt_info}
        if spec.get("needs_existing"):
            fmt_kwargs["existing_features"] = getattr(product_obj, "features", "")
            fmt_kwargs["existing_description"] = getattr(product_obj, "long_description", "")

        raw = call_openai(spec["prompt"].format(**fmt_kwargs))
        if raw is None:
            return JsonResponse(
                {"error": f"Failed to generate {field}"}, status=502
            )

        print(f"{field}..............................", raw)

        result[field] = [{"value": spec["parse"](raw), "checked": False}]
        update_obj[f"ai_generated_{field}"] = result[field]

    if update_obj:
        print("update_obj..........", update_obj)
        DatabaseModel.update_documents(
            product.objects, {"id": product_id}, update_obj
        )

    return JsonResponse(result)


@csrf_exempt
def regenerateAiContents(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    data = json.loads(request.body)
    product_id = data.get("product_id")
    selected_option = data.get("option", "")

    result = {}
    update_obj = {}

    for field, spec in REWRITE_SPECS.items():
        items = data.get(field)
        if not items:
            continue

        for item in items:
            if not item.get("checked"):
                continue

            original = item["value"]
            if field == "features" and isinstance(original, list):
                original = "\n".join(f"- {f}" for f in original)

            raw = call_openai(
                spec["prompt"].format(
                    selected_option=selected_option, original=original
                ),
                system_prompt=REWRITE_SYSTEM_PROMPT,
                model="gpt-3.5-turbo",
                max_tokens=500,
            )
            if raw is None:
                return JsonResponse(
                    {"error": f"Failed to rewrite {field}"}, status=502
                )

            item["value"] = spec["parse"](raw)

        result[field] = items
        update_obj[f"ai_generated_{field}"] = items

    if update_obj:
        DatabaseModel.update_documents(
            product.objects, {"id": product_id}, update_obj
        )

    return JsonResponse(result)
