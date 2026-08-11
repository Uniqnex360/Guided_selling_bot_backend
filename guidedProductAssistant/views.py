from guidedProductAssistant.models import product_category, filter
from math import isnan
import threading
from product_assistant.crud import DatabaseModel
from rest_framework.parsers import MultiPartParser
from rest_framework.decorators import api_view, parser_classes
from functools import wraps
from rest_framework import status
from rest_framework.response import Response
from mongoengine.errors import NotUniqueError
from datetime import datetime, timedelta
import jwt
from django.contrib.auth.hashers import make_password, check_password
from guidedProductAssistant.models import User
from django.shortcuts import render
from django.http import JsonResponse
from .ai_service import get_product_assistant_response
from guidedProductAssistant.models import brand, product, product_category, product_questions, prompt_type, save_products_from_excel
from guidedProductAssistant.utils import productDetails
from guidedProductAssistant.ai_content import (
    call_openai,
    product_prompt_info,
    GENERATE_SPECS,
    REWRITE_SPECS,
    REWRITE_SYSTEM_PROMPT
)
import json
import re
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
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import pandas as pd
import tempfile
from rest_framework.decorators import api_view
from bson import ObjectId
import os
client = OpenAI(api_key=settings.OPEN_AI_KEY)
MAX_REWRITE_COUNT = int(os.getenv("MAX_REWRITE_COUNT", "3"))
def handle_exceptions(func):
    @wraps(func)
    def _wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if args and hasattr(args[0], 'headers'):
                return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return {'error': str(e)}
    return _wrapped
def jwt_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return Response({'error': 'Authorization header missing or invalid'}, status=status.HTTP_401_UNAUTHORIZED)
        token = auth_header.split(' ')[1]
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=['HS256'])
            request.user_payload = payload
        except jwt.ExpiredSignatureError:
            return Response({'error': 'Token expired'}, status=status.HTTP_401_UNAUTHORIZED)
        except jwt.InvalidTokenError:
            return Response({'error': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)
        return view_func(request, *args, **kwargs)
    return _wrapped_view
@handle_exceptions
@api_view(['POST'])
@parser_classes([MultiPartParser])
def import_products_from_excel(request):
    excel_file = request.FILES.get('file')
    if not excel_file:
        return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
            for chunk in excel_file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name
        save_products_from_excel(tmp_path)
        return Response({"status": "success", "message": "Products imported successfully"}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
@handle_exceptions
@csrf_exempt
@api_view(['DELETE'])
def delete_product(request, product_id):
    try:
        prod = product.objects(id=product_id).first()
        if not prod:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)
        prod.delete()
        return Response({"message": "Product deleted successfully"}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
@handle_exceptions
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
@handle_exceptions
@csrf_exempt
@api_view(['POST'])
def login(request):
    email = request.data.get('email')
    print("email", email)
    password = request.data.get('password')
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
    if not check_password(password, user.password):
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
    payload = {
        'user_id': str(user.id),
        'email': user.email,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
    return Response({'token': token})
@handle_exceptions
def chatbot_view(request):
    if request.method == "POST":
        data = json.loads(request.body)
        user_query = data['message']
        product_id = data['product_id']
        response_text = get_product_assistant_response(user_query, product_id)
        return JsonResponse({"response": response_text})
    return render(request, "chatbot/chat.html")
@handle_exceptions
def product_list(request):
    pipeline = [
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
    ]
    product_list = list(product.objects.aggregate(*(pipeline)))
    return render(request, "chatbot/products.html", {"products": product_list})
@handle_exceptions
def product_detail(request, product_id):
    product_list = productDetails(product_id)
    return render(request, "chatbot/product_detail.html", {"product": product_list})
@handle_exceptions
@csrf_exempt
def update_product_content(request):
    if request.method == "POST":
        data = json.loads(request.body)
        product_id = data.get("product_id")
        selected_content = data.get("content")
        product_obj = product.objects.get(id=product_id)
        product_obj.description = selected_content
        product_obj.save()
        return JsonResponse({"status": "success"})
@handle_exceptions
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
        search_query = ' '.join([spell.correction(word)
                                for word in search_query.split()])
    except:
        pass
    if category_id is not None and category_id != "":
        match["category_id"] = ObjectId(category_id)
    if attributes and isinstance(attributes, dict):
        for attribute_name, attribute_values in attributes.items():
            if attribute_values and isinstance(attribute_values, list):
                match[f"attributes.{attribute_name}"] = {
                    "$in": attribute_values}
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
                    {"product_category_ins.name": {
                        "$regex": search_query, "$options": "i"}},
                    {"sku_number_product_code_item_number": {
                        "$regex": search_query, "$options": "i"}},
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
                                            "input": {"$objectToArray": "$attributes"},
                                            "cond": {
                                                "$or": [
                                                    {
                                                        "$and": [
                                                            {"$eq": [
                                                                {"$type": "$$this.k"}, "string"]},
                                                            {"$regexMatch": {
                                                                "input": "$$this.k", "regex": search_query, "options": "i"}}
                                                        ]
                                                    },
                                                    {
                                                        "$and": [
                                                            {"$eq": [
                                                                {"$type": "$$this.v"}, "string"]},
                                                            {"$regexMatch": {
                                                                "input": "$$this.v", "regex": search_query, "options": "i"}}
                                                        ]
                                                    },
                                                    {
                                                        "$and": [
                                                            {"$in": [{"$type": "$$this.v"}, [
                                                                "int", "long", "double", "decimal"]]},
                                                            {"$regexMatch": {
                                                                "input": {"$toString": "$$this.v"}, "regex": search_query, "options": "i"}}
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
@handle_exceptions
def convertToTrue(data):
    updated_list = list()
    for ins in data:
        if ins['checked'] == True:
            ins['checked'] = False
            updated_list.append(ins)
        else:
            updated_list.append(ins)
    return updated_list
@handle_exceptions
@csrf_exempt
@api_view(['GET'])
def fetch_categories(request):
    search_query = request.GET.get(
        'q', '').strip() if request.GET.get('q') else ''
    pipeline = [
        {
            "$lookup": {
                "from": "product_category",
                "localField": "category_id",
                "foreignField": "_id",
                "as": "category_info"
            }
        },
        {"$unwind": "$category_info"},
        {
            "$match": {
                "category_info.name": {"$regex": search_query, "$options": "i"} if search_query else {"$exists": True}
            }
        },
        {
            "$group": {
                "_id": "$category_info._id",
                "name": {"$first": "$category_info.name"},
                "count": {"$sum": 1}
            }
        },
        {
            "$project": {
                "id": {"$toString": "$_id"},
                "name": 1,
                "count": 1,
                "_id": 0
            }
        },
        {"$sort": {"name": 1}}
    ]
    categories = list(product.objects.aggregate(*pipeline))
    return Response({"categories": categories})
@handle_exceptions
@csrf_exempt
@api_view(['GET'])
def fetch_brands(request):
    search_query = request.GET.get(
        'q', '').strip() if request.GET.get('q') else ''
    pipeline = [
        {
            "$match": {
                "brand_name": {"$regex": search_query, "$options": "i"} if search_query else {"$exists": True}
            }
        },
        {
            "$group": {
                "_id": "$brand_name",
                "count": {"$sum": 1}
            }
        },
        {
            "$project": {
                "id": "$_id",
                "name": "$_id",
                "count": 1,
                "_id": 0
            }
        },
        {
            "$sort": {"name": 1}
        }
    ]
    brands = list(product.objects.aggregate(*pipeline))
    return Response({"brands": brands})
@handle_exceptions
@csrf_exempt
@api_view(['GET'])
def fetch_price_range(request):
    category_id = request.GET.get('category_id')
    brand_name = request.GET.get('brand')
    match_stage = {}
    if category_id:
        match_stage["category_id"] = ObjectId(category_id)
    if brand_name:
        match_stage["brand_name"] = {"$regex": brand_name, "$options": "i"}
    pipeline = []
    if match_stage:
        pipeline.append({"$match": match_stage})
    pipeline.append({
        "$group": {
            "_id": None,
            "min_price": {"$min": "$list_price"},
            "max_price": {"$max": "$list_price"}
        }
    })
    pipeline.append({
        "$project": {
            "_id": 0,
            "min_price": {"$ifNull": ["$min_price", 0]},
            "max_price": {"$ifNull": ["$max_price", 0]}
        }
    })
    price_range = list(product.objects.aggregate(*pipeline))
    return Response(price_range[0] if price_range else {"min_price": 0, "max_price": 0})
@handle_exceptions
@csrf_exempt
@api_view(['GET'])
def brand_search(request):
    search_query = request.GET.get('q', '').strip()
    pipeline = [
        {
            "$match": {
                "brand_name": {"$regex": search_query, "$options": "i"}
            }
        },
        {
            "$group": {
                "_id": "$brand_name",
                "count": {"$sum": 1}
            }
        },
        {
            "$project": {
                "id": "$_id",
                "name": "$_id",
                "count": 1,
                "_id": 0
            }
        },
        {
            "$sort": {"count": -1}
        }
    ]
    brands = list(product.objects.aggregate(*pipeline))
    return Response({"brands": brands})
@handle_exceptions
@csrf_exempt
@api_view(['GET'])
def category_search(request):
    search_query = request.GET.get('q', '').strip()
    pipeline = [
        {
            "$lookup": {
                "from": "product_category",
                "localField": "category_id",
                "foreignField": "_id",
                "as": "category"
            }
        },
        {"$unwind": "$category"},
        {
            "$match": {
                "category.name": {"$regex": search_query, "$options": "i"}
            }
        },
        {
            "$group": {
                "_id": "$category.name",
                "count": {"$sum": 1}
            }
        },
        {
            "$project": {
                "id": "$_id",
                "name": "$_id",
                "count": 1,
                "_id": 0
            }
        },
        {
            "$sort": {"count": -1}
        }
    ]
    categories = list(product.objects.aggregate(*pipeline))
    return Response({"categories": categories})
@handle_exceptions
def strip_html_tags(text):
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)
@handle_exceptions
@csrf_exempt
def productDetail(request, product_id):
    product_list = productDetails(product_id)
    product_list['ai_generated_title'] = product_list['ai_generated_title']
    product_list['ai_generated_description'] = product_list['ai_generated_description']
    product_list['ai_generated_features'] = product_list['ai_generated_features']
    if 'features' in product_list and isinstance(product_list['features'], list):
        product_list['features'] = [strip_html_tags(
            f) for f in product_list['features']]
    data = dict()
    data['product'] = product_list
    return data
@handle_exceptions
def normalize_query(query: str) -> str:
    query = query.strip().lower()
    query = re.sub(r'\s+', ' ', query)
    query = re.sub(r'[?!.]+$', '', query)
    return query
@handle_exceptions
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
        user_query = escape(user_query)
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
        existing_answer = product_questions.objects(
            question=normalized_query).first()
        if existing_answer and (existing_answer, 'answer', None):
            if existing_answer.answer.strip():
                data['response'] = existing_answer.answer
                return data
        response_text = get_product_assistant_response(user_query, product_id)
        product_questions(question=user_query, answer=response_text,
                          category_id=product_category_id, product_id=ObjectId(product_id)).save()
        data['response'] = response_text
        return data
    except Exception as e:
        data['response'] = f"An unexpected error occurred: {str(e)}"
        return data
@handle_exceptions
def fetchProductQuestions(request, product_id):
    product_obj = product.objects.get(id=product_id)
    pipeline = [
        {
            "$match": {
                "category_id": product_obj.category_id.id
            }
        },
        {
            "$project": {
                "_id": 0,
                "id": {"$toString": "$_id"},
                "question": 1
            }
        },
    ]
    product_questions_list = list(
        product_questions.objects.aggregate(*(pipeline)))
    return product_questions_list
@handle_exceptions
@csrf_exempt
def fetchAiContent(request):
    if request.method != "POST":
        return {"error": "Method not allowed"}
    data = json.loads(request.body)
    product_id = data.get("product_id")
    try:
        product_obj = product.objects.get(id=product_id)
    except product.DoesNotExist:
        return {"error": "Product not found"}
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
            return {"error": f"Failed to generate {field}"}
        print(f"{field}..............................", raw)
        parsed = spec["parse"](raw)
        append_ai_history(
            product_obj=product_obj,
            field=field,
            value=parsed,
            entry_type="generate",
            source="fetchAiContent",
        )
        result[field] = [{"value": parsed, "checked": False}]
        update_obj[f"ai_generated_{field}"] = result[field]
    if update_obj:
        DatabaseModel.update_documents(product.objects, {"id": product_id}, update_obj)
        product_obj.save()  
    return result
def append_ai_history(
    product_obj,
    field: str,
    value,
    entry_type: str,
    source: str,
    option: str | None = None,
):
    entry = {
        "value": value,
        "created_at": datetime.utcnow(),
        "type": entry_type,
        "source": source,
    }
    if option:
        entry["option"] = option
    if field == "title":
        product_obj.ai_title_history.append(entry)
    elif field == "features":
        product_obj.ai_features_history.append(entry)
    elif field == "description":
        product_obj.ai_description_history.append(entry)
        
@handle_exceptions
@csrf_exempt
def regenerateAiContents(request):
    if request.method != "POST":
        return {"error": "Method not allowed"}
    data = json.loads(request.body)
    product_id = data.get("product_id")
    selected_option = data.get("option", "")
    try:
        product_obj = product.objects.get(id=product_id)
    except product.DoesNotExist:
        return {"error": "Product not found"}
    title_count = getattr(product_obj, "ai_title_rewrite_count", 0) or 0
    features_count = getattr(product_obj, "ai_features_rewrite_count", 0) or 0
    description_count = getattr(
        product_obj, "ai_description_rewrite_count", 0) or 0
    def is_at_limit(field_name: str) -> bool:
        if field_name == "title":
            return title_count >= MAX_REWRITE_COUNT
        if field_name == "features":
            return features_count >= MAX_REWRITE_COUNT
        if field_name == "description":
            return description_count >= MAX_REWRITE_COUNT
        return False
    result = {}
    update_obj = {}
    counters_to_update = {}
    blocked = []

    for field, spec in REWRITE_SPECS.items():
        items = data.get(field)
        if not items:
            continue
        if is_at_limit(field):
            blocked.append(field)
            continue
        rework_any = False
        for item in items:
            if not item.get("checked"):
                continue
            original = item["value"]
            if field == "features" and isinstance(original, list):
                original = "\n".join(f"- {f}" for f in original)
            raw = call_openai(
                spec["prompt"].format(
                    selected_option=selected_option,
                    original=original
                ),
                system_prompt=REWRITE_SYSTEM_PROMPT,
                model="gpt-3.5-turbo",
                max_tokens=500,
            )
            if raw is None:
                return {"error": f"Failed to rewrite {field}"}
            item["value"] = spec["parse"](raw)
            rework_any = True
            append_ai_history(
                product_obj=product_obj,
                field=field,
                value=item["value"],
                entry_type="rewrite",
                source="regenerateAiContents",
                option=selected_option,
            )
        if rework_any:
            result[field] = items
            update_obj[f"ai_generated_{field}"] = items
            if field == "title":
                title_count += 1
                counters_to_update["ai_title_rewrite_count"] = title_count
            elif field == "features":
                features_count += 1
                counters_to_update["ai_features_rewrite_count"] = features_count
            elif field == "description":
                description_count += 1
                counters_to_update["ai_description_rewrite_count"] = description_count
    
    if blocked and not update_obj:
        return {
            "error": "Rewrite limit reached. Each field can only be rewritten 3 times."
        }
    
    for attr, value in update_obj.items():
        setattr(product_obj, attr, value)
    for attr, value in counters_to_update.items():
        setattr(product_obj, attr, value)
    product_obj.save()
    return result
@handle_exceptions
@csrf_exempt
def fetchAiHistory(request, product_id):
    prod = product.objects.get(id=product_id)
    return {
        "title_history": prod.ai_title_history,
        "features_history": prod.ai_features_history,
        "description_history": prod.ai_description_history,
    }
@handle_exceptions
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
@handle_exceptions
def fetchPromptList(request):
    pipeline = [
        {
            "$project": {
                "_id": 0,
                "id": {"$toString": "$_id"},
                "name": 1,
            }
        }
    ]
    prompt_list = list(prompt_type.objects.aggregate(*(pipeline)))
    return prompt_list
@handle_exceptions
def process_category(category, category_idx):
    print(f"Processing category {category_idx}: {category.name}")
    products = product.objects(category_id=category.id)
    product_idx = 0
    for product_obj in products:
        product_idx += 1
        print(f"Processing product {product_idx}: {product_obj.product_name}")
        for attribute_name, attribute_value in product_obj.attributes.items():
            existing_filter = DatabaseModel.get_document(
                filter.objects, {"category_id": category.id, "name": attribute_name})
            if existing_filter:
                if 'options' not in existing_filter.config:
                    existing_filter.config['options'] = []
                if attribute_value not in existing_filter.config['options']:
                    existing_filter.config['options'].append(attribute_value)
                    existing_filter.save()
            else:
                new_filter = filter(
                    category_id=category.id,
                    name=attribute_name,
                    filter_type='select',
                    config={'options': [attribute_value]}
                )
                new_filter.save()
@handle_exceptions
def script(request):
    end_level_categories = product_category.objects(end_level=True)
    threads = []
    category_idx = 0
    for category in end_level_categories:
        category_idx += 1
        thread = threading.Thread(
            target=process_category, args=(category, category_idx))
        threads.append(thread)
        thread.start()
    for thread in threads:
        thread.join()
    return True
@handle_exceptions
def remove_nan_from_filters():
    filters = filter.objects()
    for filter_obj in filters:
        if 'options' in filter_obj.config:
            cleaned_options = [
                option for option in filter_obj.config['options']
                if not (isinstance(option, float) and isnan(option))
            ]
            if len(cleaned_options) != len(filter_obj.config['options']):
                filter_obj.config['options'] = cleaned_options
                filter_obj.save()
    return True
@handle_exceptions
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
