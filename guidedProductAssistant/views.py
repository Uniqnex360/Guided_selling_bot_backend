from django.shortcuts import render
from django.http import JsonResponse
from .ai_service import get_product_assistant_response
from guidedProductAssistant.models import product, product_questions, prompt_type
from guidedProductAssistant.utils import productDetails
import json
from rest_framework.parsers import JSONParser
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from markupsafe import escape
import requests
from django.conf import settings
from openai import OpenAI
from openai import OpenAIError
from spellchecker import SpellChecker
client = OpenAI(api_key=settings.OPEN_AI_KEY)

from guidedProductAssistant.models import User
from django.contrib.auth.hashers import make_password, check_password
import jwt
from datetime import datetime, timedelta
from django.conf import settings
from mongoengine.errors import NotUniqueError
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import jwt
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status
from functools import wraps


def jwt_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return Response({'error': 'Authorization header missing or invalid'}, status=status.HTTP_401_UNAUTHORIZED)
        token = auth_header.split(' ')[1]
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            request.user_payload = payload  # You can access user info in your view
        except jwt.ExpiredSignatureError:
            return Response({'error': 'Token expired'}, status=status.HTTP_401_UNAUTHORIZED)
        except jwt.InvalidTokenError:
            return Response({'error': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@csrf_exempt
@api_view(['POST'])
def register(request):
    email = request.data.get('email')
    password = request.data.get('password')
    if not email or not password:
        return Response({'error': 'Email and password required'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        user = User(
            email=email,
            password=make_password(password)
        )
        user.save()
        return Response({'message': 'User registered successfully'}, status=status.HTTP_201_CREATED)
    except NotUniqueError:
        return Response({'error': 'Email already exists'}, status=status.HTTP_400_BAD_REQUEST)

@csrf_exempt
@api_view(['POST'])
def login(request):
    email = request.data.get('email')
    print("email",email)
    password = request.data.get('password')
    try:
        user = User.objects.get(email=email)
        if not check_password(password, user.password):
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        payload = {
            'user_id': str(user.id),
            'email': user.email,
            'exp': datetime.utcnow() + timedelta(hours=24)
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
        return Response({'token': token})
    except User.DoesNotExist:
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

def chatbot_view(request):
    if request.method == "POST":
        data=json.loads(request.body)  
        user_query = data['message']
        product_id = data['product_id']
        response_text = get_product_assistant_response(user_query,product_id)
        return JsonResponse({"response": response_text})
    return render(request, "chatbot/chat.html")

def product_list(request):
    pipeline = [
        {
            "$lookup" : {
                "from" : "product_category",
                "localField" : "category_id",
                "foreignField" : "_id",
                "as" : "product_category_ins"
            }
        },
        {
            "$unwind" : "$product_category_ins"
        },
        {
            "$project" : {
                "_id" : 0,
                "id" : {"$toString" : "$_id"},
                "image_url" : {"$ifNull": [{"$first": "$images"}, "http://example.com/"]},
                "sku": {"$ifNull": ["$sku_number_product_code_item_number", "N/A"]},
                "name": {"$ifNull": ["$product_name", "N/A"]},
                "category" : "$product_category_ins.name",
                "price": {"$ifNull": [{"$round": ["$list_price", 2]}, 0.0]},
                "mpn" : {"$ifNull": ["$mpn", "N/A"]},
                "brand_name" : {"$ifNull": ["$brand_name", "N/A"]},
            }
        },
    ]
    product_list = list(product.objects.aggregate(*(pipeline)))
    return render(request, "chatbot/products.html", {"products": product_list})

def product_detail(request, product_id):
    product_list = productDetails(product_id)
    return render(request, "chatbot/product_detail.html", {"product": product_list})

@csrf_exempt
def fetch_ai_content(request):
    if request.method == "POST":
        data = json.loads(request.body)
        product_id = data.get("product_id")
        fetch_title = data.get("title")
        fetch_features = data.get("features")
        fetch_description = data.get("description")
        product_obj = product.objects.get(id=product_id)
        brand_name = product_obj.brand_name
        product_name = product_obj.product_name
        sku = product_obj.sku_number_product_code_item_number
        mpn = getattr(product_obj, 'mpn', '')
        result = {}
        def chatgpt_response(prompt):
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            return response.choices[0].message.content
        if fetch_title:
            prompt_info = f"""
            Product Name: {product_name}
            Brand: {brand_name}
            SKU: {sku}
            MPN: {mpn}
            """
            prompt = f"""
            Generate exactly 3 catchy, professional, and engaging product titles for the product below. Each title should be on its own line and the title should contain key characteristics of product, & it should contain around 150-170 characters, & also brand name, model  should be included. Use a friendly US marketing tone.
            {prompt_info}
            """
            response_text = chatgpt_response(prompt)
            result["title"] = [
                line.strip("-•1234567890. ").strip()
                for line in response_text.strip().split("\n")
                if line.strip()
            ][:3]
        if fetch_features:
            prompt_info = f"""
            Product Name: {product_name}
            Brand: {brand_name}
            SKU: {sku}
            MPN: {mpn}
            Existing Feature Text (if any): {product_obj.features}
            """
            prompt = f"""
            You are a product content specialist helping to generate high-quality product feature bullet points.
            Based on the information below, generate **three distinct variations** of the product's feature list. Each variation should be written as a clean bullet list, containing **a minimum of 3 and a maximum of 8 unique features**.
            📝 **Guidelines:**
            - Start each variation with: "Variation 1:", "Variation 2:", and "Variation 3:"
            - Each bullet point should highlight a **specific product benefit**, **key functionality**, **physical attribute**, or **typical application**.
            - **Avoid repeating** phrasing or points between variations. Each variation should feel unique.
            - Use clear, professional US-English language with a tone suitable for ecommerce platforms like Amazon, Grainger, and Home Depot.
            - Focus on helpful, actionable details that help the user understand what makes this product valuable.
            - If existing features are provided, feel free to refine or rephrase them for clarity and usefulness.
            You are a product content expert tasked with writing a concise and technically accurate product description.
            Based on the following product data, generate a product description of **200-220 words** that highlights the product's **core functionality, technical specifications, typical use cases, and key attributes**
            🛑 Do NOT include:
            - Any marketing buzzwords or promotional claims (e.g., "best-in-class", "game-changer", "top-rated").
            - Any packaging details (e.g., pack size, box contents, number of units).
            - Any customer testimonials, offers, or pricing information.
            ✅ Do INCLUDE:
            - Clear, factual information useful to a buyer or technician.
            - How and where the product is typically used (if applicable).
            - Unique technical features or specifications that differentiate this product.
            Write in a **neutral, professional US-English tone**, suitable for ecommerce platforms and distributor catalogs like Grainger, Fastenal, or MSC.{prompt_info}
            """
            response_text = chatgpt_response(prompt)
            variations_raw = response_text.strip().split("Variation")
            variations = []
            for block in variations_raw[1:]:
                lines = block.strip().split("\n")
                feature_lines = [line.strip("-•0123456789. ").strip() for line in lines if line.strip().startswith("-")]
                if feature_lines:
                    variations.append(feature_lines)
            result["features"] = variations[:3]
        if fetch_description:
            prompt_info = f"""
            Product Name: {product_name}
            Brand: {brand_name}
            SKU: {sku}
            MPN: {mpn}
            Existing Description (if any): {product_obj.long_description}
            """
            prompt = f"""
            Generate exactly 3 product descriptions for the product below.
            Each variation should:
            - Be 2 paragraphs
            - Have 80–100 words total
            - Focus on product benefits, usage, features
            - Be clear, professional, and marketing-friendly (US tone)
            - Avoid generic fluff or repeated points
            Clearly label each variation like:
            Variation 1:
            [Paragraph 1]
            [Paragraph 2]
            {prompt_info}
            """
            response_text = chatgpt_response(prompt)
            blocks = response_text.strip().split("Variation")
            descriptions = []
            for block in blocks[1:]:
                parts = block.strip().split("\n\n")
                paragraph_texts = [p.strip() for p in parts if p.strip()]
                if len(paragraph_texts) >= 2:
                    descriptions.append("\n\n".join(paragraph_texts[:2]))
            result["description"] = descriptions[:3]
        return JsonResponse(result, safe=False)
    
@csrf_exempt
def update_product_content(request):
    if request.method == "POST":
        data = json.loads(request.body)
        product_id = data.get("product_id")
        selected_content = data.get("content")
        product_obj = product.objects.get(id=product_id)
        product_obj.description = selected_content  # or product.features based on selection
        product_obj.save()
        return JsonResponse({"status": "success"})
    

@csrf_exempt

def productList(request):
    match = {}
    pipeline = []
    json_request = JSONParser().parse(request)
    search_query = json_request.get("search_query")
    category_id = json_request.get("category_id")
    attributes = json_request.get("attributes", {})
    search_query = search_query.strip()
    try:
        spell = SpellChecker()
        search_query = ' '.join([spell.correction(word) for word in search_query.split()])
    except:
        pass
    if category_id is not None and category_id != "":
        match["category_id"] = ObjectId(category_id)
    if attributes and isinstance(attributes, dict):
        for attribute_name, attribute_values in attributes.items():
            if attribute_values and isinstance(attribute_values, list):  # Ensure attribute_values is a list
                match[f"attributes.{attribute_name}"] = {"$in": attribute_values}  # Use $in for list matching
    pipeline.append({
        "$match": match
    })
    pipeline.extend([
        {
            "$lookup": {
                "from": "product_category",
                "localField": "category_id",
                "foreignField": "_id",
                "as": "product_category_ins"
            }
        },
        {
            "$unwind": "$product_category_ins"
        },
        {
            "$match": {
                "$or": [
                    {"brand_name": {"$regex": search_query, "$options": "i"}},
                    {"product_category_ins.name": {"$regex": search_query, "$options": "i"}},
                    {"sku_number_product_code_item_number": {"$regex": search_query, "$options": "i"}},
                    {"mpn": {"$regex": search_query, "$options": "i"}},
                    {"model": {"$regex": search_query, "$options": "i"}},
                    {"upc_ean": {"$regex": search_query, "$options": "i"}},
                    {"product_name": {"$regex": f'^{search_query}$', "$options": "i"}},
                    {
                        "$expr": {
                            "$gt": [
                                {
                                    "$size": {
                                        "$filter": {
                                            "input": { "$objectToArray": "$attributes" },
                                            "cond": {
                                                "$or": [
                                                    # Check if key matches the search query
                                                    {
                                                        "$and": [
                                                            { "$eq": [{ "$type": "$$this.k" }, "string"] },
                                                            { "$regexMatch": { "input": "$$this.k", "regex": search_query, "options": "i" } }
                                                        ]
                                                    },
                                                    # Check if string values match the search query
                                                    {
                                                        "$and": [
                                                            { "$eq": [{ "$type": "$$this.v" }, "string"] },
                                                            { "$regexMatch": { "input": "$$this.v", "regex": search_query, "options": "i" } }
                                                        ]
                                                    },
                                                    # Check if numeric values match the search query (by converting to string)
                                                    {
                                                        "$and": [
                                                            { "$in": [{ "$type": "$$this.v" }, ["int", "long", "double", "decimal"]] },
                                                            { "$regexMatch": { "input": { "$toString": "$$this.v" }, "regex": search_query, "options": "i" } }
                                                        ]
                                                    }
                                                ]
                                            }
                                        }
                                    }
                                },
                                0
                            ]
                        }
                    },
                    {"long_description": {"$regex": search_query, "$options": "i"}},
                    {"features": {"$regex": search_query, "$options": "i"}},                    
                ]
            }
        },
        {
            "$project": {
                "_id": 0,
                "id": {"$toString": "$_id"},
                "image_url": {"$ifNull": [{"$first": "$images"}, "http://example.com/"]},
                "sku": {"$ifNull": ["$sku_number_product_code_item_number", "N/A"]},
                "name": {"$ifNull": ["$product_name", "N/A"]},
                "category": "$product_category_ins.name",
                "price": {"$ifNull": [{"$round": ["$list_price", 2]}, 0.0]},
                "mpn": {"$ifNull": ["$mpn", "N/A"]},
                "brand_name": {"$ifNull": ["$brand_name", "N/A"]},
            }
        },
    ])
    product_list = list(product.objects.aggregate(*(pipeline)))
    data = dict()
    data['products'] = product_list
    return data
def convertToTrue(data):
    updated_list = list()
    for ins in data:
        if ins['checked'] == True:
            ins['checked'] = False
            updated_list.append(ins)
        else:
            updated_list.append(ins)
    return updated_list

import re

def strip_html_tags(text):
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

def productDetail(request, product_id):
    product_list = productDetails(product_id)
    product_list['ai_generated_title'] = convertToTrue(product_list['ai_generated_title'])
    product_list['ai_generated_description'] = convertToTrue(product_list['ai_generated_description'])
    product_list['ai_generated_features'] = convertToTrue(product_list['ai_generated_features'])

    # Remove HTML tags from features
    if 'features' in product_list and isinstance(product_list['features'], list):
        product_list['features'] = [strip_html_tags(f) for f in product_list['features']]

    data = dict()
    data['product'] = product_list
    return data
def normalize_query(query:str)-> str:
    query=query.strip().lower()
    query = re.sub(r'\s+', ' ', query)
    query = re.sub(r'[?!.]+$', '', query)
    return query
    
@csrf_exempt
def chatbotView(request):
    data = dict() 
    try:
        json_request = JSONParser().parse(request)
        user_query = json_request['message']
        product_id = json_request['product_id']
        if not user_query and not product_id:
            data['response'] = "Both message and product_id are required"
            return data
        user_query=escape(user_query)
        product = productDetails(product_id)
        if not product:
            data['response'] = 'Product not found'
            return data
        product_category_id = product.get('category_id')
        
        if isinstance(product_category_id, str):
            try:
                product_category_id = ObjectId(product_category_id)
            except Exception:
                data['response'] = "Invalid category ID format"
                return data
        normalized_query = user_query.strip()
        existing_answer = product_questions.objects(question=normalized_query).first()
        # print(existing_answer.to_mongo()) 
        
        # CORRECT: Simple check and access for StringField
        if existing_answer and (existing_answer,'answer',None):
            if existing_answer.answer.strip():
                data['response'] = existing_answer.answer
                return data
            
        response_text = get_product_assistant_response(user_query, product_id)
        product_questions(question=user_query,answer=response_text,category_id=product_category_id,product_id=ObjectId(product_id)).save()
        data['response'] = response_text
        return data
    except Exception as e:
        data['response'] = f"An unexpected error occurred: {str(e)}"
        return data
    
def fetchProductQuestions(request,product_id):
    product_obj = product.objects.get(id=product_id)
    pipeline = [
        {
            "$match" : {
                "category_id" : product_obj.category_id.id
            }
        },
        {
            "$project" : {
                "_id" : 0,
                "id" : {"$toString" : "$_id"},
                "question" : 1
            }
        },
        # {"$limit" : 6}
    ]
    product_questions_list = list(product_questions.objects.aggregate(*(pipeline)))
    return product_questions_list

import re
@csrf_exempt
def fetchAiContent(request):
    result = {}
    if request.method == "POST":
        update_obj = {}
        data = json.loads(request.body)
        product_id = data.get("product_id")
        fetch_title = data.get("title")
        fetch_features = data.get("features")
        fetch_description = data.get("description")
        product_obj = product.objects.get(id=product_id)
        brand_name = product_obj.brand_name
        product_name = product_obj.product_name
        sku = product_obj.sku_number_product_code_item_number
        mpn = getattr(product_obj, 'mpn', '')
        def chatgpt_response(prompt):
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            return response.choices[0].message.content
        if fetch_title:
            prompt_info = f"""
            Product Name: {product_name}
            Brand: {brand_name}
            SKU: {sku}
            MPN: {mpn}
            """
            prompt = f"""
            Generate Product Content Based on Specific Sources and instruction
            Product:
            {prompt_info}
            Objective: Create product descriptions and features using data primarily sourced from Würth Baer Supply Company (www.baersupply.com) and other specified websites (Brand website – Manufacturer's official site, Grainger.com, Homedepot.com, MSCdirect.com,  Globalindustrial.com). Ensure all attributes are formatted appropriately and align with the structure provided below.
            Product Content Requirements
            Product Title:
            Follow this structure:
            [Brand Name] [Model Number] [Product Type] [2-3 Key Specifications] - [Primary Benefit]
            Use Title Case (Capitalize Each Major Word)
            Do not use punctuation marks (commas, hyphens, colons, etc.)
            Avoid all caps
            Include the primary keyword near the beginning
            Limit to 120 characters maximum
            End with a clear, concise benefit or distinctive feature when appropriate (optional)
            Match the style like this:
                Makita 6407 3/8 Inch Drill 4.9 Amp Variable Speed Quiet Operation
                Makita 6407 3/8 Inch Corded Drill 4.9 Amp 2500 Rpm Ergonomic Design
                Makita 6407 3/8 Inch Variable Speed Drill 4.9 Amp Reversible Motor
            Instructions for Content Creation
            Provide 3 concise variations of the chosen content type (product title).
            Collect detailed product specifications, dimensions, materials, and benefits from Würth Baer Supply Company first.
            Supplement missing details using other listed sources while maintaining consistency across all content.
            Provide three concise variations of the chosen content type (product title).
            Ensure each variation is clear, human-friendly, and formatted as per guidelines.
            """
            response_text = chatgpt_response(prompt)
            print("title..............................", response_text)
            lines = [
                line.strip("•-0123456789. ").strip()
                for line in response_text.strip().split("\n")
                if line.strip()
            ]
            variations = [line for line in lines if len(line.split()) > 2][:3]
            result["title"] = [{"value": t, "checked": False} for t in variations]
            update_obj["ai_generated_title"] = result["title"]
        if fetch_features:
            prompt_info = f"""
            Product Name: {product_name}
            Brand: {brand_name}
            SKU: {sku}
            MPN: {mpn}
            Existing Feature Text (if any): {product_obj.features}
            """
            prompt = f"""
            Generate Product Content Based on Specific Sources and instruction
            Product:
            {prompt_info}
            Objective: Create product descriptions and features using data primarily sourced from Würth Baer Supply Company (www.baersupply.com) and other specified websites (Brand website – Manufacturer's official site, Grainger.com, Homedepot.com, MSCdirect.com,  Globalindustrial.com). Ensure all attributes are formatted appropriately and align with the structure provided below.
            Product Content Requirements
            Features:
            List 8-10 key product features in bullet point format:
            Lead with the benefit, then explain the feature.
            Begin each bullet with an action verb or highlight a specific metric.
            Include compatibility, dimensions, materials, and performance metrics when relevant.
            Limit each bullet to 1-2 concise sentences.
            Instructions for Content Creation
            Provide 3 concise variations of the chosen content type (features).
            Collect detailed product specifications, dimensions, materials, and benefits from Würth Baer Supply Company first.
            Supplement missing details using other listed sources while maintaining consistency across all content.
            Provide three concise variations of the chosen content type (features).
            Ensure each variation is clear, human-friendly, and formatted as per guidelines.
            """
            response_text = chatgpt_response(prompt)
            print("variations_raw Features............................", response_text)
            raw_blocks = response_text.strip().split("Variation")
            variations = []
            for block in raw_blocks[1:]:
                lines = block.strip().split("\n")
                features = [
                    line.strip("•-0123456789. ").strip()
                    for line in lines if line.strip().startswith(("-", "•"))
                ]
                if features:
                    variations.append(features)
            result["features"] = [
                {"value": features, "checked": False} for features in variations[:3]
            ]
            update_obj["ai_generated_features"] = result["features"]
        if fetch_description:
            prompt_info = f"""
            Product Name: {product_name}
            Brand: {brand_name}
            SKU: {sku}
            MPN: {mpn}
            Existing Description (if any): {product_obj.long_description}
            """
            prompt = f"""
            Generate Product Content Based on Specific Sources and instruction
            Product:
            {prompt_info}
            Objective: Create product descriptions and features using data primarily sourced from Würth Baer Supply Company (www.baersupply.com) and other specified websites (Brand website – Manufacturer's official site, Grainger.com, Homedepot.com, MSCdirect.com, Globalindustrial.com). Ensure all attributes are formatted appropriately and align with the structure provided below.
            Product Content Requirements:
            Description:
            Create exactly 3 variations. Each variation must have 2 paragraphs.
            - Paragraph 1: Introduce the product, its primary purpose, and main benefit to the user.
            - Paragraph 2: Highlight 2-3 standout features and explain how they solve specific user problems.
            Use active voice and direct addressing ("you" language). Include primary and secondary keywords naturally. Focus on benefits rather than specifications.
            ⚠️ Output Format (strictly follow this):
            Variation 1:
            <paragraph 1>
            <paragraph 2>
            Variation 2:
            <paragraph 1>
            <paragraph 2>
            Variation 3:
            <paragraph 1>
            <paragraph 2>
            DO NOT use headings like "Description:" or "Paragraph 1:". Just use the format above exactly.
            """
            response_text = chatgpt_response(prompt)
            print("blocks description............................", response_text)
            # Match blocks like 'Variation 1:\n<text>\n\n<text>'
            matches = re.findall(r"Variation\s+\d+:\s*(.*?)(?=\nVariation|\Z)", response_text, re.DOTALL)
            descriptions = []
            for match in matches:
                paragraphs = [p.strip() for p in match.strip().split("\n\n") if p.strip()]
                if len(paragraphs) >= 2:
                    descriptions.append("\n\n".join(paragraphs[:2]))
                else:
                    descriptions.append("\n\n".join(paragraphs))
            result["description"] = [
                {"value": desc, "checked": False} for desc in descriptions[:3]
            ]
            update_obj["ai_generated_description"] = result["description"]
        if update_obj:
            print("update_obj..........",update_obj)
            DatabaseModel.update_documents(product.objects, {"id": product_id}, update_obj)
    return result
@csrf_exempt
def updateProductContent(request):
    if request.method == "POST":
        data = json.loads(request.body)
        print("data", data)
        product_id = data.get("product_id")
        product_objs = data.get("product_obj")
        product_obj = product.objects.get(id=product_id)
        try:
            name = []
            if product_objs['product_name']:
                name.append(product_obj.product_name)
                name.extend(product_obj.old_names)
                product_obj.product_name = product_objs['product_name']
                product_obj.old_names = name
        except KeyError:
            pass
        try:
            description = []
            if product_objs['long_description']:
                description.append(product_obj.long_description)
                description.extend(product_obj.old_description)
                product_obj.long_description = product_objs['long_description']
                product_obj.old_description = description
        except KeyError:
            pass
        try:
            features = []
            if product_objs['features'] != []:
                features.append(product_obj.features)
                features.extend(product_obj.old_features)
                product_obj.old_features = features
                product_obj.features = product_objs['features']
        except KeyError:
            pass
        product_obj.save()
        return True
def fetchPromptList(request):
    pipeline = [         
        {
            "$project" : {
                "_id" : 0,
                "id" : {"$toString" : "$_id"},
                "name" : 1,
            }
        }
    ]
    prompt_list = list(prompt_type.objects.aggregate(*(pipeline)))
    return prompt_list 
@csrf_exempt
def regenerateAiContents(request):
    if request.method == "POST":
        update_obj = dict()
        data = json.loads(request.body)
        product_id = data.get("product_id")
        selected_option = data.get("option")  # e.g., "Improve writing", "Make longer", etc.
        regenerate_title = data.get("title")  # This is the selected title to regenerate (optional)
        regenerate_features = data.get("features")  # List of selected features (optional)
        regenerate_description = data.get("description")  # This is the selected description (optional)
        result = {}
        def ask_chatgpt(prompt):
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",  # or "gpt-3.5-turbo"
                    messages=[
                        {"role": "system", "content": "You are a helpful product content writer."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=500
                )
                return response.choices[0].message.content.strip()
            except OpenAIError as e:
                print("OpenAI Error:", e)
                return "Error generating content."
        if regenerate_title:
            for ins in regenerate_title:
                if ins['checked'] == True:
                    prompt = f"""
                    You are an expert product content writer.
                    Given the product title below, please **{selected_option.lower()}**. Make sure the title is clear, professional, and suitable for ecommerce platforms in the US.
                    🔧 Original Title:
                    "{ins['value']}"
                    ✍️ Updated Title:
                    """
                    titles = ask_chatgpt(prompt)
                    ins['value'] =  titles
            result["title"] = regenerate_title
            update_obj['ai_generated_title'] = result["title"]
        if regenerate_features:
            for ins in regenerate_features:
                if ins['checked'] == True:
                    original_features = "\n".join(f"- {f}" for f in ins['value'])
                    prompt = f"""
                    You are an expert at rewriting ecommerce product features.
                    Please {selected_option.lower()} the following list of product features. Return only **one revised version** as a clean bullet-point list. Each bullet should be on its own line. Do not include any extra notes, explanations, or markdown formatting.
                    Original Features:
                    {original_features}
                    Updated Features:
                    """
                    response_text = ask_chatgpt(prompt)
                    # Clean and extract bullet points
                    updated_lines = [
                        line.strip("-•*0123456789. ").strip()
                        for line in response_text.splitlines()
                        if line.strip()
                    ]
                    ins["value"] = updated_lines
            result["features"] = regenerate_features
            update_obj['ai_generated_features'] = result["features"]
        if regenerate_description:
            for ins in regenerate_description:
                if ins['checked'] == True:
                    prompt = f"""
                    You are a product description expert.
                    Given the product description below, please **{selected_option.lower()}**. Maintain a clear and professional tone suitable for ecommerce and distributor platforms.
                    🔧 Original Description:
                    {ins['value']}
                    ✍️ Updated Description:
                    """
                    result_description = ask_chatgpt(prompt)
                    ins["value"] = result_description
            result['description'] = regenerate_description
            update_obj['ai_generated_description'] = result["description"]
        if update_obj != {}:
            DatabaseModel.update_documents(product.objects,{"id" : product_id},update_obj)
        return result
from guidedProductAssistant.models import product_category,filter
from product_assistant.crud import DatabaseModel
import threading
from bson import ObjectId
from math import isnan
def process_category(category, category_idx):
    print(f"Processing category {category_idx}: {category.name}")
    # Fetch all products associated with the category
    products = product.objects(category_id=category.id)
    product_idx = 0
    for product_obj in products:
        product_idx += 1
        print(f"Processing product {product_idx}: {product_obj.product_name}")
        # Iterate through the attributes of the product
        for attribute_name, attribute_value in product_obj.attributes.items():
            # Check if a filter with the same name and category_id already exists
            existing_filter = DatabaseModel.get_document(filter.objects, {"category_id": category.id, "name": attribute_name})
            if existing_filter:
                # If the filter exists, update the config['options'] field
                if 'options' not in existing_filter.config:
                    existing_filter.config['options'] = []
                if attribute_value not in existing_filter.config['options']:
                    existing_filter.config['options'].append(attribute_value)
                    existing_filter.save()
            else:
                # If the filter does not exist, create a new filter
                new_filter = filter(
                    category_id=category.id,
                    name=attribute_name,
                    filter_type='select',  # Assuming 'select' as default filter type
                    config={'options': [attribute_value]}
                )
                new_filter.save()
def script(request):
    # Fetch all categories where end_level is True
    end_level_categories = product_category.objects(end_level=True)
    threads = []
    category_idx = 0
    for category in end_level_categories:
        category_idx += 1
        thread = threading.Thread(target=process_category, args=(category, category_idx))
        threads.append(thread)
        thread.start()
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    return True
def remove_nan_from_filters():
    # Fetch all filter documents
    filters = filter.objects()
    for filter_obj in filters:
        if 'options' in filter_obj.config:
            # Remove NaN values from the options list
            cleaned_options = [
                option for option in filter_obj.config['options']
                if not (isinstance(option, float) and isnan(option))
            ]
            # Update the filter document if changes were made
            if len(cleaned_options) != len(filter_obj.config['options']):
                filter_obj.config['options'] = cleaned_options
                filter_obj.save()
    return True
@csrf_exempt
def updategeneratedContent(request):
    data = dict()
    json_request = JSONParser().parse(request)
    product_id = json_request.get("product_id")
    title = json_request.get("title")
    features = json_request.get("features")
    description = json_request.get("description")
    product_obj = product.objects.get(id=product_id)
    if title != None:
        product_obj.ai_generated_title = title
    if features != None:
        product_obj.ai_generated_features = features
    if description != None:
        product_obj.ai_generated_description = description
    product_obj.save()
    return data