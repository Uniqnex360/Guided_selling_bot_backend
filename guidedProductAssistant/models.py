from mongoengine import fields,Document,EmbeddedDocument, EmbeddedDocumentField
from datetime import datetime


class brand(Document):
    name = fields.StringField(required=True)
    code = fields.StringField()
    product_sub_category_id_str = fields.StringField()
    logo = fields.StringField()
    manufacture_unit_id_str = fields.StringField()
    industry_id_str = fields.StringField()


class product_category(Document):
    name = fields.StringField(required=True)
    level = fields.IntField(default=0)
    parent_category_id = fields.ReferenceField('self', null=True)
    child_categories = fields.ListField(fields.ReferenceField('self'))
    breadcrumb = fields.StringField()
    manufacture_unit_id_str = fields.StringField()
    creation_date = fields.DateTimeField(default=datetime.now())
    description = fields.StringField()
    code = fields.StringField()
    end_level = fields.BooleanField(default=False)
    industry_id_str = fields.StringField()

class vendor(Document):
    name = fields.StringField(required=True)
    manufacture_unit_id_str = fields.StringField()

class manufacture_unit(Document):
    name = fields.StringField()
    description = fields.StringField()
    location = fields.StringField()
    logo = fields.StringField()
    industry = fields.StringField()
    is_active = fields.BooleanField(default=True)

class product(Document):
    sku_number_product_code_item_number = fields.StringField(default="")
    model = fields.StringField()
    mpn = fields.StringField(default="")
    upc_ean = fields.StringField()
    
    breadcrumb = fields.StringField()

    brand_name = fields.StringField(default="")
    product_name = fields.StringField(default="")
    long_description = fields.StringField(default="")
    short_description = fields.StringField()
    features = fields.ListField(fields.StringField())
    images = fields.ListField(fields.StringField())
    attributes = fields.DictField(default={})
    tags = fields.ListField(fields.StringField())
    msrp = fields.FloatField(default=0.0)              # Manufacturer's Suggested Retail Price
    currency = fields.StringField(default="")
    was_price = fields.FloatField(default=0.0)          # Previous price before discount
    list_price = fields.FloatField(default=0.0)         # List price of the product
    discount = fields.FloatField(default=0.0)          #Discount percentage or amount
    quantity_prices = fields.FloatField(default=0.0)     # Price per unit for a specified quantity
    quantity = fields.FloatField()          #Quantity available or minimum purchase quantity
    availability = fields.BooleanField(default=True)      # "in stock", "out of stock", "pre-order"
    return_applicable = fields.BooleanField(default=False)   # Whether returns are allowed or not
    return_in_days = fields.StringField()
    visible = fields.BooleanField(default=True)
    brand_id = fields.ReferenceField(brand)
    vendor_id = fields.ReferenceField(vendor)
    # Reference to the lowest category level (Level 6 in this example)
    category_id = fields.ReferenceField(product_category)
    quantity_price = fields.DictField(default={"1-100" : 1,"100-1000" : 2,"1000-10000" : 3})
    rating_count = fields.IntField(default=0)
    rating_average = fields.FloatField(default=0.0)
    from_the_manufacture = fields.StringField()
    industry_id_str = fields.StringField()
    tax = fields.FloatField(default=0.0)
    manufacture_unit_id = fields.ReferenceField(manufacture_unit)
    old_names = fields.ListField(fields.StringField())
    old_description = fields.ListField(fields.StringField())
    old_features = fields.ListField(fields.ListField(fields.StringField()))

# import pandas as pd


# def save_products_from_excel(file_path):
#     df = pd.read_excel(file_path)
#     i=0
#     for _, row in df.iterrows():

#         print("11111111111111111111",i)
#         category = product_category.objects(name=row.get("Sub Category")).first()
#         if category:
#             category_id = category.id
#         else:
#             category = product_category(name=row.get("Sub Category")).save()
#             category_id = category.id

#         brand_obj = brand.objects(name=row.get("Brand name")).first()
#         if brand_obj:
#             brand_id = brand_obj.id
#         else:
#             brand_obj = brand(name=row.get("Brand name")).save()
#             brand_id = brand_obj.id
#         product_obj = product(
#             sku_number_product_code_item_number=row.get("SKU", ""),
#             model=row.get("Product Title", ""),
#             mpn=str(row.get("MPN", "")),
#             brand_name=row.get("Brand name", ""),
#             product_name=row.get("Product Title", ""),
#             long_description=row.get("Description", ""),
#             features=[row.get(f"Feature {i}", "") for i in range(1, 13) if pd.notna(row.get(f"Feature {i}"))],
#             attributes={
#                 row.get(f"Attribute Name{i}", ""): row.get(f"Attribute Value{i}", "")
#                 for i in range(1, 46) if pd.notna(row.get(f"Attribute Name{i}"))
#             },
#             images=[row.get("Wurth URL", ""), row.get("Brand URL", "")],
#             availability=True if row.get("Availability", "in stock").lower() == "in stock" else False,
#             brand_id = brand_id,
#             category_id = category_id
#         )
        
#         product_obj.save()
#         print(f"Saved: {product.product_name}")
#         if i==20:
#             break
#         i+=1


# import random
# # Query the products, skipping the first 102
# products = product.objects.skip(102)

# # Process each product
# for product_ins in products:
#     # Randomly generate a float number from 50 to 100 for was_price
#     # was_price = round(random.uniform(50, 100), 2)
    
#     # # Randomly generate an integer from 1 to 50 for discount
#     # discount = random.randint(1, 50)
    
#     # # Calculate list_price
#     # list_price = round(was_price * (1 - discount / 100), 2)
#     images = [product_ins.images[0]]
    
#     # Update the product in the database
#     product.objects(id=product_ins.id).update_one(set__images=images)

# print("Database updated successfully.")



class product_questions(Document):
    question = fields.StringField()
    answer = fields.StringField()
    product_id = fields.ReferenceField(product)
    category_id = fields.ReferenceField(product_category)


class prompt_type(Document):
    name = fields.StringField()




class filter(Document):
    # Each filter is associated with a leaf category (i.e. level 4)
    category_id = fields.ReferenceField(product_category, required=True)
    name = fields.StringField(required=True)  # e.g., "color", "price", etc.
    filter_type = fields.StringField(
        required=True,
        choices=('select', 'range', 'multi-select', 'boolean')
    )
    display_order = fields.IntField(default=0)
    config = fields.DictField(default={})