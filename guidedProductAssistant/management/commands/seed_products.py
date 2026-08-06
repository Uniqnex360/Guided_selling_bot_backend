from django.core.management.base import BaseCommand

from guidedProductAssistant.models import (
    product,
    product_category,
    brand,
)

from guidedProductAssistant.views import fetchAiContent

from django.test.client import RequestFactory
import json


PRODUCTS = [
    {
        "sku": "103152038",
        "category": "Power Tools",
        "name": "Metabo Portable Table Saw TKHS315C 240V",
        "brand": "Metabo",
    },
    {
        "sku": "AWA06060",
        "category": "Fasteners",
        "name": "JCP Through Bolt Clear Zinc Plated 6 x 60mm",
        "brand": "JCP",
    },
    {
        "sku": "3037",
        "category": "Welding",
        "name": "Black Auto-Darkening Welding Helmet",
        "brand": "Generic",
    },
]


class Command(BaseCommand):
    help = "Insert products and generate AI content"

    def handle(self, *args, **kwargs):

        rf = RequestFactory()

        for item in PRODUCTS:

            category = product_category.objects(name=item["category"]).first()

            if not category:
                category = product_category(
                    name=item["category"],
                    end_level=True,
                    level=1,
                    breadcrumb=item["category"],
                ).save()

            brand_obj = brand.objects(name=item["brand"]).first()

            if not brand_obj:
                brand_obj = brand(name=item["brand"]).save()

            prod = product.objects(
                sku_number_product_code_item_number=item["sku"]
            ).first()

            if not prod:
                prod = product(
                    sku_number_product_code_item_number=item["sku"],
                    product_name=item["name"],
                    brand_name=item["brand"],
                    brand_id=brand_obj,
                    category_id=category,
                ).save()

                self.stdout.write(f"Created {item['name']}")

            request = rf.post(
                "/fetchAiContent/",
                data=json.dumps({
                    "product_id": str(prod.id),
                    "title": True,
                    "description": True,
                    "features": True
                }),
                content_type="application/json",
            )

            fetchAiContent(request)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Generated AI content for {item['name']}"
                )
            )