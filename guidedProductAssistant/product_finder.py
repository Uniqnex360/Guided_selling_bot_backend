from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from product_assistant.crud import DatabaseModel
from rest_framework.decorators import api_view, permission_classes
from .models import  filter,product_category
import pandas as pd
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from bson import ObjectId
import requests
from rest_framework.parsers import JSONParser
import ast

def get_or_create_category(name, level, client_id_str,parent=None):
    category_obj = product_category.objects(name=name, level=level, parent_category_id=parent,client_id_str=client_id_str).first()
    if not category_obj:
        category_obj = product_category(name=name, level=level, parent_category_id=parent,client_id_str=client_id_str)
        category_obj.save()
    return category_obj


# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
@csrf_exempt
def import_data(request):
    # Determine file type and load data
    file = request.FILES['file']
    client_id_str = request.POST.get('client_id_str')
    if file.name.endswith('.csv'):
        df = pd.read_csv(file)
    elif file.name.endswith(('.xls', '.xlsx')):
        df = pd.read_excel(file)
    else:
        return {"error": "Unsupported file format. Please provide a CSV or Excel file."}

    # Fixed category columns
    category_columns = [f'Category-{i}' for i in range(1, 6)]

    # Iterate through the DataFrame
    for index, row in df.iterrows():
        parent = None
        breadcrumb = []
        
        # Create categories
        for level in range(1, 6):
            category_name = row.get(f'Category-{level}')
            if pd.notna(category_name):
                category_obj = get_or_create_category(category_name, level, client_id_str, parent)
                breadcrumb.append(category_name)
                parent = category_obj
        
        # Mark the end level category
        if parent:
            parent.end_level = True
            parent.breadcrumb = ' > '.join(breadcrumb)
            parent.save()
        
        # Create filters for the end level category
        if parent and parent.end_level:
            # Identify filter columns dynamically
            filter_columns = [col for col in df.columns if col not in category_columns]
            for filter_name in filter_columns:
                filter_value = str(row.get(filter_name))
                if pd.notna(filter_value):
                    # Check if filter already exists for the category
                    existing_filter = filter.objects(category_id=parent, name=filter_name).first()
                    if existing_filter:
                        # Append new values to existing filter options
                        existing_options = set(existing_filter.config.get('options', []))
                        new_options = set(filter_value.split('|')) if '|' in filter_value else {filter_value}
                        combined_options = existing_options.union(new_options)
                        existing_filter.config['options'] = list(combined_options)
                        existing_filter.save()
                    else:
                        # Create new filter document
                        filter_doc = filter(
                            category_id=parent,
                            name=filter_name,
                            filter_type='select',  # Adjust filter type as needed
                            config={'options': filter_value.split('|') if '|' in filter_value else [filter_value]}
                        )
                        filter_doc.save()

    return {"message": "Data imported successfully."}

@csrf_exempt
def fourth_level_categories_view(request):
    categories_cursor = DatabaseModel.list_documents(product_category.objects, filter={"end_level": True})
    categories_list = []
    for ins in categories_cursor:
        cat = {
            "id" : str(ins.id),
            "name": ins.name,
        }
        categories_list.append(cat)
    return {"categories": categories_list}
 


def category_filters_view(request):
    category_id = request.GET.get('category_id')
    print(category_id)
    category_name = product_category.objects.get(id=category_id).name
    filters_cursor = DatabaseModel.list_documents(filter.objects, filter={"category_id": category_id})
    filters_list = []
    for ins in filters_cursor:
        f = ins.to_mongo().to_dict()
        f.pop('_id')
        f.pop('category_id')
        # Check if config['options'] is not empty
        if f.get('config', {}).get('options', []):
            # Replace NaN values with None to make the data JSON serializable
            for key, value in f.items():
                if pd.isna(value) or value == float('nan'):
                    f[key] = None
            filters_list.append(f)
    # Sort filters_list by name in ascending order
    filters_list = sorted(filters_list, key=lambda x: x.get('name', '').lower())
    return {"category_id": category_id, "category_name": category_name, "filters": filters_list}
    