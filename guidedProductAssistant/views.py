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
import requests
from django.conf import settings
from openai import OpenAI
import openai
# Use the correct OpenAI client interface
client = OpenAI(api_key=settings.OPEN_AI_KEY)


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
    


def productList(request):
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
    data=dict()
    data['products']= product_list
    return data


def productDetail(request,product_id):
    product_list = productDetails(product_id)
    data=dict()
    data['product']= product_list
    return data


@csrf_exempt
def chatbotView(request):
    data =dict() 
    json_request = JSONParser().parse(request)
    user_query = json_request['message']
    product_id = json_request['product_id']
    response_text = get_product_assistant_response(user_query,product_id)
    data['response'] = response_text
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
        {"$limit" : 6}
    ]
    product_questions_list = list(product_questions.objects.aggregate(*(pipeline)))
    return product_questions_list


@csrf_exempt
def fetchAiContent(request):
    result = {}
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
    return result



@csrf_exempt
def updateProductContent(request):
    if request.method == "POST":
        data = json.loads(request.body)
        product_id = data.get("product_id")
        product_objs = data.get("product_obj")
        
        product_obj = product.objects.get(id=product_id)
        try:
            name = []
            name.append(product_obj.product_name)
            name.extend(product_obj.old_names)
            product_obj.product_name = product_objs['product_name']
            product_obj.old_names = name
        except KeyError:
            pass
        
        try:
            description = []
            description.append(product_obj.long_description)
            description.extend(product_obj.old_description)
            product_obj.long_description = product_objs['long_description']
            product_obj.old_description = description
        except KeyError:
            pass

        try:
            features = []
            features.append(product_obj.features)
            features.extend(product_obj.old_features)
            product_obj.old_features = features
            product_obj.features = product_objs['features']
        except KeyError:
            pass
        
        product_obj.save()
        
        return



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
        data = json.loads(request.body)

        selected_option = data.get("option")  # e.g., "Improve writing", "Make longer", etc.
        regenerate_title = data.get("title")  # This is the selected title to regenerate (optional)
        regenerate_features = data.get("features")  # List of selected features (optional)
        regenerate_description = data.get("description")  # This is the selected description (optional)

        result = {}

        def ask_chatgpt(prompt):
            try:
                response = openai.ChatCompletion.create(
                    model="gpt-4",  # or "gpt-3.5-turbo"
                    messages=[
                        {"role": "system", "content": "You are a helpful product content writer."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=500
                )
                return response.choices[0].message["content"].strip()
            except Exception as e:
                print("OpenAI Error:", e)
                return "Error generating content."

        if regenerate_title:
            prompt = f"""
            You are an expert product content writer.

            Given the product title below, please **{selected_option.lower()}**. Make sure the title is clear, professional, and suitable for ecommerce platforms in the US.

            🔧 Original Title:
            "{regenerate_title}"

            ✍️ Updated Title:
            """
            result["title"] = ask_chatgpt(prompt)

        if regenerate_features:
            original_features = "\n".join(f"- {f}" for f in regenerate_features)
            prompt = f"""
            You are an expert at rewriting product features.

            Given the list of bullet-point product features below, please **{selected_option.lower()}**. Keep the format as bullet points.

            🔧 Original Features:
            {original_features}

            ✍️ Updated Features:
            """
            response_text = ask_chatgpt(prompt)
            updated_lines = [
                line.strip("-•0123456789. ").strip()
                for line in response_text.split("\n")
                if line.strip()
            ]
            result["features"] = updated_lines

        if regenerate_description:
            prompt = f"""
            You are a product description expert.

            Given the product description below, please **{selected_option.lower()}**. Maintain a clear and professional tone suitable for ecommerce and distributor platforms.

            🔧 Original Description:
            {regenerate_description}

            ✍️ Updated Description:
            """
            result["description"] = ask_chatgpt(prompt)

        return result
