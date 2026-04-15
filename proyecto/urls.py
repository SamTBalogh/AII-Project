"""
URL configuration for proyecto project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
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

from django.contrib import admin
from django.urls import path

from main import views

urlpatterns = [
    path("", views.index),
    path("populate/", views.populateDB),
    
    # Recommendation System URLs
    path("loadRS/", views.loadRS, name="loadRS"),
    path("loadContentRS/", views.loadContentRS, name="loadContentRS"),
    path("loadWhooshIndex/", views.loadWhooshIndex, name="loadWhooshIndex"),
    path("recomendedDecks/", views.recommendedDecks, name="recommendedDecks"),
    path("recomendedDecksContent/", views.recommendedDecksContent, name="recommendedDecksContent"),
    
    # Deck URLs
    path("decks/", views.decks, name="decks"),
    path("decks/<int:deck_id>/", views.deck_detail, name="deck_detail"),
    path("decks/<int:deck_id>/optimize-price/", views.deck_optimize_price, name="deck_optimize_price"),
    path("decks/<int:deck_id>/optimize-shipping/", views.deck_optimize_shipping, name="deck_optimize_shipping"),
    
    # Card URLs
    path("cards/", views.cards, name="cards"),
    path("cards/<int:card_id>/", views.card_detail, name="card_detail"),
    
    # Seller URLs
    path("sellers/", views.sellers, name="sellers"),
    path("sellers/<int:seller_id>/", views.seller_detail, name="seller_detail"),
    
    path("admin/", admin.site.urls),
    
    # Data extraction URLs
    path("data/generate-set-urls/", views.data_generate_set_urls, name="data_generate_set_urls"),
    path("data/extract-card-links/", views.data_extract_card_links, name="data_extract_card_links"),
    path("data/rename-card-files/", views.data_rename_card_files, name="data_rename_card_files"),
    path("data/extract-card-data/", views.data_extract_card_data, name="data_extract_card_data"),
    path("data/extract-seller-links/", views.data_extract_seller_links, name="data_extract_seller_links"),
    path("data/extract-seller-data/", views.data_extract_seller_data, name="data_extract_seller_data"),
    path("data/extract-seller-card-data/", views.data_extract_seller_card_data, name="data_extract_seller_card_data"),
    
    # User ratings URL
    path("data/generate-ratings/", views.generate_ratings, name="generate_ratings"),
]
