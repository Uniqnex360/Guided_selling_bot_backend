"""
URL configuration for product_assistant project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from guidedProductAssistant.views import product_list, product_detail, chatbot_view,fetch_ai_content,update_product_content, productList, productDetail,chatbotView, fetchAiContent, fetchProductQuestions, updateProductContent, fetchPromptList, regenerateAiContents

urlpatterns = [
    path("", product_list, name="product_list"),  # Home page
    path("product/<product_id>/", product_detail, name="product_detail"),  # Product details
    path("chat/", chatbot_view, name="chatbot_view"),  # Chatbot API
    path("fetch_ai_content/", fetch_ai_content, name="fetch_ai_content"),  # Product details
    path("update_product_content/", update_product_content, name="update_product_content"),  # Chatbot API

    path("productList/", productList, name="productList"),  # Chatbot API
    path("productDetail/<product_id>/", productDetail, name="productDetail"),  # Product details
    path("chatbotView/", chatbotView, name="chatbotView"),  # Chatbot API

    path("fetchAiContent/", fetchAiContent, name="fetchAiContent"),  # Product details
    path("fetchProductQuestions/<product_id>/", fetchProductQuestions, name="fetchProductQuestions"),  # Product details

    path("updateProductContent/", updateProductContent, name="updateProductContent"),  # Chatbot API
    path("fetchPromptList/", fetchPromptList, name="fetchPromptList"),  # Chatbot API
    path("regenerateAiContents/", regenerateAiContents, name="regenerateAiContents"),  # Chatbot API
]
