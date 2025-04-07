from guidedProductAssistant.models import product

def productDetails(product_id):
    product_id = product.objects.get(id=product_id)
    pipeline =[
        {
            "$match" : {
                "_id" : (product_id.id),
            }
        },
        {
                "$lookup": {
                    "from": "product_category",
                    "localField": "category_id",
                    "foreignField": "_id",
                    "as": "product_category_ins"
                }
            },
            {"$unwind" : "$product_category_ins"},
         {
            "$lookup": {
                "from": "brand",
                "localField": "brand_id",
                "foreignField": "_id",
                "as": "brand_ins"
            }
        },
        {
        "$unwind": {
            "path": "$brand_ins", 
            "preserveNullAndEmptyArrays": True
        }
        },
        {
           "$project" :{
            "_id":0,
            "id" : {"$toString" : "$_id"},
            "product_name" : {"$ifNull": ["$product_name", "N/A"]},
            "sku_number_product_code_item_number" : {"$ifNull": ["$sku_number_product_code_item_number", "N/A"]},
            "model" : {"$ifNull": ["$model", "N/A"]},
            "mpn" : {"$ifNull": ["$mpn", "N/A"]},
            "upc_ean" : {"$ifNull": ["$upc_ean", "N/A"]},
            "logo" : {"$ifNull" : [{"$first":"$images"},"http://example.com/"]},
            "long_description" : {"$ifNull": ["$long_description", "N/A"]},
            "short_description" : {"$ifNull": ["$short_description", "N/A"]},
            "list_price" : {"$ifNull": ["$list_price", 0.0]},
            "msrp" : {"$ifNull" : ["$msrp",0.0]},
            "was_price" : {"$ifNull" : ["$was_price",0.0]},
            "discount": { 
            "$concat": [
                { "$toString": { "$round": [{"$ifNull": ["$discount", 0]}, 2] } }, 
                "%" 
            ] 
            },
            "brand_name" : {"$ifNull": ["$brand_name", "N/A"]},
            "brand_logo" : {"$ifNull" : ["$brand_ins.logo",""]},
            "currency" : {"$ifNull": ["$currency", "N/A"]},
            "quantity" : {"$ifNull": ["$quantity", 0]},
            "availability" : {"$ifNull": ["$availability", False]},
            "images" : {"$ifNull": ["$images", []]},
            "attributes" : {"$ifNull": ["$attributes", {}]},
            "features" : {"$ifNull": ["$features", []]},
            "from_the_manufacture" : {"$ifNull": ["$from_the_manufacture", "N/A"]},
            "visible" : {"$ifNull": ["$visible", False]},
            "end_level_category" : {"$ifNull": ["$product_category_ins.name", "N/A"]},
           }
        }
    ]
    product_list = list(product.objects.aggregate(*(pipeline)))
    return product_list[0]