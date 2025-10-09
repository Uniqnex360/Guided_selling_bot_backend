from django.urls import path
from guidedProductAssistant.views import (
    product_list, product_detail, chatbot_view, fetch_ai_content, update_product_content,
    productList, productDetail, chatbotView, fetchAiContent, fetchProductQuestions,
    updateProductContent, fetchPromptList, regenerateAiContents, script, updategeneratedContent,
    register, login, brand_search, category_search,fetch_brands,fetch_price_range,fetch_categories,import_products_from_excel,delete_product
)
from guidedProductAssistant.product_finder import fourth_level_categories_view, category_filters_view

urlpatterns = [
    path("", product_list, name="product_list"),
    path("product/<product_id>/", product_detail, name="product_detail"),
    path("chat/", chatbot_view, name="chatbot_view"),
    path("fetch_ai_content/", fetch_ai_content, name="fetch_ai_content"),
    path("update_product_content/", update_product_content, name="update_product_content"),
    path("productList/", productList, name="productList"),
    path("productDetail/<product_id>/", productDetail, name="productDetail"),
    path("chatbotView/", chatbotView, name="chatbotView"),
    path("fetchAiContent/", fetchAiContent, name="fetchAiContent"),
    path("fetchProductQuestions/<product_id>/", fetchProductQuestions, name="fetchProductQuestions"),
    path("updateProductContent/", updateProductContent, name="updateProductContent"),
    path("fetchPromptList/", fetchPromptList, name="fetchPromptList"),
    path("regenerateAiContents/", regenerateAiContents, name="regenerateAiContents"),
    path("updategeneratedContent/", updategeneratedContent, name="updategeneratedContent"),
    # Product Finder
    path("fourth_level_categories/", fourth_level_categories_view, name="fourth_level_categories"),
    path("category_filters/", category_filters_view, name="category_filters"),
    path("script/", script, name="script"),
    # Auth endpoints
    path('register/', register, name='register'),
    path('login/', login, name='login'),
    path('brand_search/', brand_search, name='brand_search'),
    path('category_search/', category_search, name='category_search'),  # Reusing category_filters_view for category_search
    path('fetch_brands/', fetch_brands, name='fetch_brands'),  # Reusing brand_search for fetch_brands
    path('fetch_categories/',fetch_categories, name= "fetch_categories"),
    path('fetch_price_range/',fetch_price_range, name="fetch_price_range"),
    path('import_products_from_excel/', import_products_from_excel, name='import_products_from_excel'),
    path("delete_product/<product_id>/", delete_product, name="delete_product"),
]