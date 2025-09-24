from __future__ import annotations
from mongoengine import fields, Document, EmbeddedDocument, EmbeddedDocumentField
from datetime import datetime
import pandas as pd
from mongoengine import connect
MONGODB_HOST = "mongodb+srv://techteam:Tech!123@dataextraction.h6crc.mongodb.net/"
MONGODB_NAME = "ai_assistant"
connect(
    db=MONGODB_NAME,
    host=MONGODB_HOST,
    alias="default"
)


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
    msrp = fields.FloatField(default=0.0)
    currency = fields.StringField(default="")
    was_price = fields.FloatField(default=0.0)
    list_price = fields.FloatField(default=0.0)
    discount = fields.FloatField(default=0.0)
    quantity_prices = fields.FloatField(default=0.0)
    quantity = fields.FloatField()
    availability = fields.BooleanField(default=True)
    return_applicable = fields.BooleanField(default=False)
    return_in_days = fields.StringField()
    visible = fields.BooleanField(default=True)
    brand_id = fields.ReferenceField(brand)
    vendor_id = fields.ReferenceField(vendor)
    category_id = fields.ReferenceField(product_category)
    quantity_price = fields.DictField(
        default={"1-100": 1, "100-1000": 2, "1000-10000": 3})
    rating_count = fields.IntField(default=0)
    rating_average = fields.FloatField(default=0.0)
    from_the_manufacture = fields.StringField()
    industry_id_str = fields.StringField()
    tax = fields.FloatField(default=0.0)
    manufacture_unit_id = fields.ReferenceField(manufacture_unit)
    old_names = fields.ListField(fields.StringField())
    old_description = fields.ListField(fields.StringField())
    old_features = fields.ListField(fields.ListField(fields.StringField()))
    ai_generated_title = fields.ListField(fields.DictField())
    ai_generated_description = fields.ListField(fields.DictField())
    ai_generated_features = fields.ListField(fields.DictField())


def save_products_from_excel(file_path):
    df = pd.read_excel(file_path)
    for _, row in df.iterrows():
        category_names = [c.strip() for c in str(
            row.get("Category Name / Sub Category", "")).split("/")]
        category_name = category_names[-1] if category_names else "Uncategorized"
        category_obj = product_category.objects(name=category_name).first()
        if not category_obj:
            category_obj = product_category(
                name=category_name,
                breadcrumb=" > ".join(category_names),
                level=len(category_names),
                end_level=True
            ).save()
        brand_name = str(row.get("From the Manufacture", "")).strip()
        brand_obj = brand.objects(name=brand_name).first()
        if not brand_obj:
            brand_obj = brand(name=brand_name).save()
        mu_name = str(row.get("Manufacture Unit Name", "")).strip()
        mu_obj = manufacture_unit.objects(name=mu_name).first()
        if not mu_obj:
            mu_obj = manufacture_unit(name=mu_name).save()
        features = [
            str(row.get(f"Feature {i}", "")).strip()
            for i in range(1, 11)
            if pd.notna(row.get(f"Feature {i}", None)) and str(row.get(f"Feature {i}")).strip()
        ]
        attributes = {}
        for i in range(1, 11):
            key = row.get(f"Attribute Name{i}")
            value = row.get(f"Attribute Value{i}")
            if pd.notna(key) and pd.notna(value):
                attributes[str(key).strip()] = str(value).strip()
        images = []
        for url_field in ["Wurth URL", "Brand URL"]:
            url = row.get(url_field)
            if pd.notna(url) and str(url).strip():
                images.append(str(url).strip())
        tags = [tag.strip()
                for tag in str(row.get("Tags", "")).split(",") if tag.strip()]
        return_applicable = str(
            row.get("Return Applicable", "")).strip().lower() == "yes"
        availability_str = str(row.get("Availability", "")).strip().lower()
        availability = True if availability_str == "in stock" else False
        product_obj = product(
            sku_number_product_code_item_number=str(row.get("SKU", "")),
            product_name=str(row.get("Product Title", "")),
            mpn=str(row.get("MPN", "")),
            brand_name=brand_name,
            brand_id=brand_obj.id,
            category_id=category_obj.id,
            breadcrumb=" > ".join(category_names),
            long_description=str(row.get("Long Description", "")),
            short_description=str(row.get("Short Description", "")),
            features=features,
            attributes=attributes,
            images=images,
            msrp=float(row.get("MSRP", 0)),
            currency=str(row.get("Currency", "")),
            was_price=float(row.get("Was Price", 0)),
            list_price=float(row.get("List Price", 0)),
            discount=float(row.get("Discount", 0)),
            quantity=float(row.get("Quantity", 0)),
            return_applicable=return_applicable,
            return_in_days=str(row.get("Return in Days", "")),
            tags=tags,
            from_the_manufacture=brand_name,
            industry_id_str=str(row.get("Industry", "")),
            tax=float(row.get("Tax", 0)),
            manufacture_unit_id=mu_obj.id,
            availability=availability
        )
        product_obj.save()
        print(f"Saved: {product_obj.product_name}")


class product_questions(Document):
    question = fields.StringField()
    answer = fields.StringField()
    question_type = fields.StringField()
    product_id = fields.ReferenceField(product)
    category_id = fields.ReferenceField(product_category)


class prompt_type(Document):
    name = fields.StringField()


class filter(Document):
    category_id = fields.ReferenceField(product_category, required=True)
    name = fields.StringField(required=True)
    filter_type = fields.StringField(
        required=True,
        choices=('select', 'range', 'multi-select', 'boolean')
    )
    display_order = fields.IntField(default=0)
    config = fields.DictField(default={})
