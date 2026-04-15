# encoding:utf-8
"""
Whoosh Search Module for MTG Database.

This module provides full-text search capabilities using Whoosh
for Cards, Decks, Sellers, and SellerCards.
"""

import os
import shutil
from whoosh import index
from whoosh.fields import Schema, TEXT, ID, NUMERIC, KEYWORD, STORED, BOOLEAN
from whoosh.qparser import QueryParser, MultifieldParser, OrGroup
from whoosh.query import Term, And, Or, NumericRange, Every
from whoosh.analysis import StemmingAnalyzer, StandardAnalyzer
from django.conf import settings

# Directory for Whoosh indexes
WHOOSH_INDEX_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'whoosh_index')


# =============================================================================
# SCHEMA DEFINITIONS
# =============================================================================

# Schema for Cards
CARD_SCHEMA = Schema(
    id_card=ID(stored=True, unique=True),
    name=TEXT(stored=True, analyzer=StandardAnalyzer()),
    name_exact=ID(stored=True),  # For exact matching
    version=TEXT(stored=True),
    rarity=ID(stored=True),
    card_number=ID(stored=True),
    set_name=TEXT(stored=True, field_boost=1.5),  # 'set' is reserved
    set_exact=ID(stored=True),  # For exact matching
    image_url=STORED,
    available_items=NUMERIC(stored=True, numtype=int),
    price_from=NUMERIC(stored=True, numtype=float),
    price_trend=NUMERIC(stored=True, numtype=float),
    avg_30_days=NUMERIC(stored=True, numtype=float),
    avg_7_days=NUMERIC(stored=True, numtype=float),
    avg_1_day=NUMERIC(stored=True, numtype=float),
)

# Schema for Decks
DECK_SCHEMA = Schema(
    id_deck=ID(stored=True, unique=True),
    name=TEXT(stored=True, analyzer=StandardAnalyzer()),
    name_exact=ID(stored=True),
    alternative_name=TEXT(stored=True),
    archetype=ID(stored=True),
    color_identity=ID(stored=True),
    colors_used=TEXT(stored=True),  # Searchable colors
    meta_percentage=NUMERIC(stored=True, numtype=float),
)

# Schema for Sellers
SELLER_SCHEMA = Schema(
    id_seller=ID(stored=True, unique=True),
    name=TEXT(stored=True, analyzer=StandardAnalyzer()),
    name_exact=ID(stored=True),
    real_name=TEXT(stored=True),
    country=ID(stored=True),
    country_text=TEXT(stored=True),  # For partial matching
    sales_count=NUMERIC(stored=True, numtype=int),
    available_items=NUMERIC(stored=True, numtype=int),
    seller_type=ID(stored=True),
    rating=ID(stored=True),
    shipping_days=NUMERIC(stored=True, numtype=int),
    city=TEXT(stored=True),
    # Approval fields
    approval_very_good=ID(stored=True),
    approval_good=ID(stored=True),
    approval_neutral=ID(stored=True),
    approval_bad=ID(stored=True),
    # Address fields
    street_address=TEXT(stored=True),
    postal_code=ID(stored=True),
)

# Schema for SellerCards (seller-card relationships)
SELLER_CARD_SCHEMA = Schema(
    id_seller_card=ID(stored=True, unique=True),
    seller_id=ID(stored=True),
    seller_name=TEXT(stored=True),
    card_id=ID(stored=True),
    card_name=TEXT(stored=True),
    card_name_exact=ID(stored=True),
    card_set=ID(stored=True),
    card_rarity=ID(stored=True),
    quantity=NUMERIC(stored=True, numtype=int),
    price=NUMERIC(stored=True, numtype=float),
    currency=ID(stored=True),
    condition=ID(stored=True),
    language=ID(stored=True),
)

# Schema for DeckCards (deck-card relationships)
DECK_CARD_SCHEMA = Schema(
    id_deck_card=ID(stored=True, unique=True),
    deck_id=ID(stored=True),
    deck_name=TEXT(stored=True),
    card_id=ID(stored=True),
    card_name=TEXT(stored=True),
    card_name_exact=ID(stored=True),
    card_set=ID(stored=True),
    card_rarity=ID(stored=True),
    quantity=NUMERIC(stored=True, numtype=int),
    role=ID(stored=True),
)


# =============================================================================
# INDEX MANAGEMENT FUNCTIONS
# =============================================================================

def get_or_create_index(index_name, schema):
    """
    Get an existing index or create a new one.
    
    Args:
        index_name: Name of the index subdirectory
        schema: Whoosh Schema object
        
    Returns:
        Whoosh Index object
    """
    index_path = os.path.join(WHOOSH_INDEX_DIR, index_name)
    
    if not os.path.exists(index_path):
        os.makedirs(index_path)
        return index.create_in(index_path, schema)
    
    if index.exists_in(index_path):
        return index.open_dir(index_path)
    
    return index.create_in(index_path, schema)


def rebuild_index(index_name, schema):
    """
    Rebuild an index from scratch.
    
    Args:
        index_name: Name of the index subdirectory
        schema: Whoosh Schema object
        
    Returns:
        Whoosh Index object
    """
    index_path = os.path.join(WHOOSH_INDEX_DIR, index_name)
    
    if os.path.exists(index_path):
        shutil.rmtree(index_path)
    
    os.makedirs(index_path)
    return index.create_in(index_path, schema)


# =============================================================================
# CARD INDEX FUNCTIONS
# =============================================================================

def populate_card_index():
    """
    Populate the card index with all cards from the database.
    
    Returns:
        int: Number of cards indexed
    """
    from main.models import Card
    
    ix = rebuild_index('cards', CARD_SCHEMA)
    writer = ix.writer()
    
    count = 0
    for card in Card.objects.all():
        writer.add_document(
            id_card=str(card.id_card),
            name=card.name or '',
            name_exact=card.name or '',
            version=card.version or '',
            rarity=card.rarity or '',
            card_number=card.card_number or '',
            set_name=card.set or '',
            set_exact=card.set or '',
            image_url=card.image_url or '',
            available_items=card.available_items or 0,
            price_from=card.price_from or 0.0,
            price_trend=card.price_trend or 0.0,
            avg_30_days=card.avg_30_days or 0.0,
            avg_7_days=card.avg_7_days or 0.0,
            avg_1_day=card.avg_1_day or 0.0,
        )
        count += 1
    
    writer.commit()
    return count


def search_cards(name=None, set_name=None, rarity=None, price_min=None, price_max=None, limit=None):
    """
    Search cards in the Whoosh index.
    
    Args:
        name: Card name to search (partial match)
        set_name: Set name to filter by
        rarity: Rarity to filter by
        price_min: Minimum price_trend
        price_max: Maximum price_trend
        limit: Maximum results to return
        
    Returns:
        List of card dictionaries
    """
    ix = get_or_create_index('cards', CARD_SCHEMA)
    results_list = []
    
    with ix.searcher() as searcher:
        # Build query parts
        query_parts = []
        
        if name:
            name_parser = QueryParser("name", ix.schema)
            # Add wildcards for partial matching
            name_query = name_parser.parse(f"*{name}*")
            query_parts.append(name_query)
        
        if set_name:
            query_parts.append(Term("set_exact", set_name))
        
        if rarity:
            query_parts.append(Term("rarity", rarity))
        
        if price_min is not None or price_max is not None:
            min_val = price_min if price_min is not None else 0
            max_val = price_max if price_max is not None else 999999
            query_parts.append(NumericRange("price_trend", min_val, max_val))
        
        # Combine queries
        if query_parts:
            final_query = And(query_parts)
        else:
            final_query = Every()
        
        # Execute search
        max_results = limit or 1000
        results = searcher.search(final_query, limit=max_results, sortedby="price_trend", reverse=True)
        
        for hit in results:
            results_list.append({
                'id_card': int(hit['id_card']),
                'name': hit['name'],
                'version': hit.get('version'),
                'rarity': hit.get('rarity'),
                'card_number': hit.get('card_number'),
                'set': hit.get('set_name'),
                'image_url': hit.get('image_url'),
                'available_items': hit.get('available_items'),
                'price_from': hit.get('price_from'),
                'price_trend': hit.get('price_trend'),
                'avg_30_days': hit.get('avg_30_days'),
                'avg_7_days': hit.get('avg_7_days'),
                'avg_1_day': hit.get('avg_1_day'),
            })
    
    return results_list


def get_card_by_id(card_id):
    """Get a single card by ID from the index."""
    ix = get_or_create_index('cards', CARD_SCHEMA)
    
    with ix.searcher() as searcher:
        result = searcher.search(Term("id_card", str(card_id)), limit=1)
        if result:
            hit = result[0]
            return {
                'id_card': int(hit['id_card']),
                'name': hit['name'],
                'version': hit.get('version'),
                'rarity': hit.get('rarity'),
                'card_number': hit.get('card_number'),
                'set': hit.get('set_name'),
                'image_url': hit.get('image_url'),
                'available_items': hit.get('available_items'),
                'price_from': hit.get('price_from'),
                'price_trend': hit.get('price_trend'),
                'avg_30_days': hit.get('avg_30_days'),
                'avg_7_days': hit.get('avg_7_days'),
                'avg_1_day': hit.get('avg_1_day'),
            }
    return None


def get_unique_card_sets():
    """Get all unique set names from the card index."""
    ix = get_or_create_index('cards', CARD_SCHEMA)
    sets = set()
    
    with ix.searcher() as searcher:
        for doc in searcher.all_stored_fields():
            if doc.get('set_name'):
                sets.add(doc['set_name'])
    
    return sorted(list(sets))


def get_unique_card_rarities():
    """Get all unique rarities from the card index."""
    ix = get_or_create_index('cards', CARD_SCHEMA)
    rarities = set()
    
    with ix.searcher() as searcher:
        for doc in searcher.all_stored_fields():
            if doc.get('rarity'):
                rarities.add(doc['rarity'])
    
    return sorted([r for r in rarities if r])


# =============================================================================
# DECK INDEX FUNCTIONS
# =============================================================================

def populate_deck_index():
    """
    Populate the deck index with all decks from the database.
    
    Returns:
        int: Number of decks indexed
    """
    from main.models import Deck
    
    ix = rebuild_index('decks', DECK_SCHEMA)
    writer = ix.writer()
    
    count = 0
    for deck in Deck.objects.all():
        writer.add_document(
            id_deck=str(deck.id_deck),
            name=deck.name or '',
            name_exact=deck.name or '',
            alternative_name=deck.alternative_name or '',
            archetype=deck.archetype or '',
            color_identity=deck.color_identity or '',
            colors_used=deck.colors_used or '',
            meta_percentage=deck.meta_percentage or 0.0,
        )
        count += 1
    
    writer.commit()
    return count


def search_decks(name=None, color_identity=None, archetype=None, meta_min=None, colors=None, limit=None):
    """
    Search decks in the Whoosh index.
    
    Args:
        name: Deck name to search (partial match)
        color_identity: Exact color identity
        archetype: Exact archetype
        meta_min: Minimum meta percentage
        colors: List of colors that must be present
        limit: Maximum results to return
        
    Returns:
        List of deck dictionaries
    """
    ix = get_or_create_index('decks', DECK_SCHEMA)
    results_list = []
    
    with ix.searcher() as searcher:
        # Build query parts
        query_parts = []
        
        if name:
            name_parser = QueryParser("name", ix.schema)
            name_query = name_parser.parse(f"*{name}*")
            query_parts.append(name_query)
        
        if color_identity:
            query_parts.append(Term("color_identity", color_identity))
        
        if archetype:
            query_parts.append(Term("archetype", archetype))
        
        if meta_min is not None:
            query_parts.append(NumericRange("meta_percentage", meta_min, None))
        
        if colors:
            # Each color must be present in colors_used
            for color in colors:
                color_parser = QueryParser("colors_used", ix.schema)
                query_parts.append(color_parser.parse(color))
        
        # Combine queries
        if query_parts:
            final_query = And(query_parts)
        else:
            final_query = Every()
        
        # Execute search
        max_results = limit or 1000
        results = searcher.search(final_query, limit=max_results, sortedby="meta_percentage", reverse=True)
        
        for hit in results:
            results_list.append({
                'id_deck': int(hit['id_deck']),
                'name': hit['name'],
                'alternative_name': hit.get('alternative_name'),
                'archetype': hit.get('archetype'),
                'color_identity': hit.get('color_identity'),
                'colors_used': hit.get('colors_used'),
                'meta_percentage': hit.get('meta_percentage'),
            })
    
    return results_list


def get_deck_by_id(deck_id):
    """Get a single deck by ID from the index."""
    ix = get_or_create_index('decks', DECK_SCHEMA)
    
    with ix.searcher() as searcher:
        result = searcher.search(Term("id_deck", str(deck_id)), limit=1)
        if result:
            hit = result[0]
            return {
                'id_deck': int(hit['id_deck']),
                'name': hit['name'],
                'alternative_name': hit.get('alternative_name'),
                'archetype': hit.get('archetype'),
                'color_identity': hit.get('color_identity'),
                'colors_used': hit.get('colors_used'),
                'meta_percentage': hit.get('meta_percentage'),
            }
    return None


def get_unique_deck_archetypes():
    """Get all unique archetypes from the deck index."""
    ix = get_or_create_index('decks', DECK_SCHEMA)
    archetypes = set()
    
    with ix.searcher() as searcher:
        for doc in searcher.all_stored_fields():
            if doc.get('archetype'):
                archetypes.add(doc['archetype'])
    
    return sorted(list(archetypes))


def get_unique_deck_color_identities():
    """Get all unique color identities from the deck index."""
    ix = get_or_create_index('decks', DECK_SCHEMA)
    identities = set()
    
    with ix.searcher() as searcher:
        for doc in searcher.all_stored_fields():
            if doc.get('color_identity'):
                identities.add(doc['color_identity'])
    
    return sorted(list(identities))


# =============================================================================
# SELLER INDEX FUNCTIONS
# =============================================================================

def populate_seller_index():
    """
    Populate the seller index with all sellers from the database.
    
    Returns:
        int: Number of sellers indexed
    """
    from main.models import Seller
    
    ix = rebuild_index('sellers', SELLER_SCHEMA)
    writer = ix.writer()
    
    count = 0
    for seller in Seller.objects.all():
        writer.add_document(
            id_seller=str(seller.id_seller),
            name=seller.name or '',
            name_exact=seller.name or '',
            real_name=seller.real_name or '',
            country=seller.country or '',
            country_text=seller.country or '',
            sales_count=seller.sales_count or 0,
            available_items=seller.available_items or 0,
            seller_type=seller.seller_type or '',
            rating=seller.rating or '',
            shipping_days=seller.shipping_days if seller.shipping_days is not None else -1,
            city=seller.city or '',
            # Approval fields
            approval_very_good=seller.approval_very_good or '',
            approval_good=seller.approval_good or '',
            approval_neutral=seller.approval_neutral or '',
            approval_bad=seller.approval_bad or '',
            # Address fields
            street_address=seller.street_address or '',
            postal_code=seller.postal_code or '',
        )
        count += 1
    
    writer.commit()
    return count


def search_sellers(name=None, country=None, seller_type=None, limit=None):
    """
    Search sellers in the Whoosh index.
    
    Args:
        name: Seller name to search (partial match)
        country: Exact country
        seller_type: Exact seller type
        limit: Maximum results to return
        
    Returns:
        List of seller dictionaries
    """
    ix = get_or_create_index('sellers', SELLER_SCHEMA)
    results_list = []
    
    with ix.searcher() as searcher:
        # Build query parts
        query_parts = []
        
        if name:
            name_parser = QueryParser("name", ix.schema)
            name_query = name_parser.parse(f"*{name}*")
            query_parts.append(name_query)
        
        if country:
            query_parts.append(Term("country", country))
        
        if seller_type:
            query_parts.append(Term("seller_type", seller_type))
        
        # Combine queries
        if query_parts:
            final_query = And(query_parts)
        else:
            final_query = Every()
        
        # Execute search
        max_results = limit or 1000
        results = searcher.search(final_query, limit=max_results, sortedby="sales_count", reverse=True)
        
        for hit in results:
            shipping = hit.get('shipping_days') if hit.get('shipping_days', -1) >= 0 else None
            results_list.append({
                'id_seller': int(hit['id_seller']),
                'name': hit['name'],
                'real_name': hit.get('real_name'),
                'country': hit.get('country'),
                'sales_count': hit.get('sales_count'),
                'available_items': hit.get('available_items'),
                'seller_type': hit.get('seller_type'),
                'rating': hit.get('rating'),
                'shipping_days': shipping,
                'on_vacation': shipping is None,
                'city': hit.get('city'),
                # Approval fields
                'approval_very_good': hit.get('approval_very_good') or None,
                'approval_good': hit.get('approval_good') or None,
                'approval_neutral': hit.get('approval_neutral') or None,
                'approval_bad': hit.get('approval_bad') or None,
                # Address fields
                'street_address': hit.get('street_address') or None,
                'postal_code': hit.get('postal_code') or None,
            })
    
    return results_list


def get_seller_by_id(seller_id):
    """Get a single seller by ID from the index."""
    ix = get_or_create_index('sellers', SELLER_SCHEMA)
    
    with ix.searcher() as searcher:
        result = searcher.search(Term("id_seller", str(seller_id)), limit=1)
        if result:
            hit = result[0]
            shipping = hit.get('shipping_days') if hit.get('shipping_days', -1) >= 0 else None
            return {
                'id_seller': int(hit['id_seller']),
                'name': hit['name'],
                'real_name': hit.get('real_name'),
                'country': hit.get('country'),
                'sales_count': hit.get('sales_count'),
                'available_items': hit.get('available_items'),
                'seller_type': hit.get('seller_type'),
                'rating': hit.get('rating'),
                'shipping_days': shipping,
                'on_vacation': shipping is None,
                'city': hit.get('city'),
                # Approval fields
                'approval_very_good': hit.get('approval_very_good') or None,
                'approval_good': hit.get('approval_good') or None,
                'approval_neutral': hit.get('approval_neutral') or None,
                'approval_bad': hit.get('approval_bad') or None,
                # Address fields
                'street_address': hit.get('street_address') or None,
                'postal_code': hit.get('postal_code') or None,
            }
    return None


def get_unique_seller_countries():
    """Get all unique countries from the seller index."""
    ix = get_or_create_index('sellers', SELLER_SCHEMA)
    countries = set()
    
    with ix.searcher() as searcher:
        for doc in searcher.all_stored_fields():
            if doc.get('country'):
                countries.add(doc['country'])
    
    return sorted(list(countries))


def get_unique_seller_types():
    """Get all unique seller types from the seller index."""
    ix = get_or_create_index('sellers', SELLER_SCHEMA)
    types = set()
    
    with ix.searcher() as searcher:
        for doc in searcher.all_stored_fields():
            if doc.get('seller_type'):
                types.add(doc['seller_type'])
    
    return sorted(list(types))


# =============================================================================
# SELLER CARD INDEX FUNCTIONS
# =============================================================================

def populate_seller_card_index():
    """
    Populate the seller-card index with all relationships from the database.
    
    Returns:
        int: Number of seller-card relationships indexed
    """
    from main.models import SellerCard
    
    ix = rebuild_index('seller_cards', SELLER_CARD_SCHEMA)
    writer = ix.writer()
    
    count = 0
    for sc in SellerCard.objects.select_related('seller', 'card').all():
        writer.add_document(
            id_seller_card=str(sc.id_seller_card),
            seller_id=str(sc.seller_id),
            seller_name=sc.seller.name or '',
            card_id=str(sc.card_id),
            card_name=sc.card.name or '',
            card_name_exact=sc.card.name or '',
            card_set=sc.card.set or '',
            card_rarity=sc.card.rarity or '',
            quantity=sc.quantity or 0,
            price=sc.price or 0.0,
            currency=sc.currency or 'EUR',
            condition=sc.condition or '',
            language=sc.language or '',
        )
        count += 1
    
    writer.commit()
    return count


def search_seller_cards_by_card(card_id, limit=None):
    """
    Search seller cards by card ID.
    
    Returns:
        List of seller-card dictionaries, sorted by price ascending
    """
    ix = get_or_create_index('seller_cards', SELLER_CARD_SCHEMA)
    results_list = []
    
    with ix.searcher() as searcher:
        query = Term("card_id", str(card_id))
        max_results = limit or 1000
        results = searcher.search(query, limit=max_results, sortedby="price")
        
        for hit in results:
            results_list.append({
                'id_seller_card': int(hit['id_seller_card']),
                'seller_id': int(hit['seller_id']),
                'seller_name': hit.get('seller_name'),
                'card_id': int(hit['card_id']),
                'card_name': hit.get('card_name'),
                'card_set': hit.get('card_set'),
                'card_rarity': hit.get('card_rarity'),
                'quantity': hit.get('quantity'),
                'price': hit.get('price'),
                'currency': hit.get('currency'),
                'condition': hit.get('condition'),
                'language': hit.get('language'),
            })
    
    return results_list


def search_seller_cards_by_seller(seller_id, limit=None):
    """
    Search seller cards by seller ID.
    
    Returns:
        List of seller-card dictionaries, sorted by card name
    """
    ix = get_or_create_index('seller_cards', SELLER_CARD_SCHEMA)
    results_list = []
    
    with ix.searcher() as searcher:
        query = Term("seller_id", str(seller_id))
        max_results = limit or 1000
        results = searcher.search(query, limit=max_results)
        
        for hit in results:
            results_list.append({
                'id_seller_card': int(hit['id_seller_card']),
                'seller_id': int(hit['seller_id']),
                'seller_name': hit.get('seller_name'),
                'card_id': int(hit['card_id']),
                'card_name': hit.get('card_name'),
                'card_set': hit.get('card_set'),
                'card_rarity': hit.get('card_rarity'),
                'quantity': hit.get('quantity'),
                'price': hit.get('price'),
                'currency': hit.get('currency'),
                'condition': hit.get('condition'),
                'language': hit.get('language'),
            })
    
    # Sort by card name
    results_list.sort(key=lambda x: x.get('card_name', ''))
    return results_list


def search_seller_cards_by_card_name(card_name, card_set=None, limit=None):
    """
    Search seller cards by card name (for finding all versions/editions).
    Useful for land cards that are interchangeable across sets.
    
    Args:
        card_name: Exact card name
        card_set: Optional set filter
        limit: Maximum results
        
    Returns:
        List of seller-card dictionaries, sorted by price ascending
    """
    ix = get_or_create_index('seller_cards', SELLER_CARD_SCHEMA)
    results_list = []
    
    with ix.searcher() as searcher:
        query_parts = [Term("card_name_exact", card_name)]
        
        if card_set:
            query_parts.append(Term("card_set", card_set))
        
        final_query = And(query_parts) if len(query_parts) > 1 else query_parts[0]
        max_results = limit or 1000
        results = searcher.search(final_query, limit=max_results, sortedby="price")
        
        for hit in results:
            results_list.append({
                'id_seller_card': int(hit['id_seller_card']),
                'seller_id': int(hit['seller_id']),
                'seller_name': hit.get('seller_name'),
                'card_id': int(hit['card_id']),
                'card_name': hit.get('card_name'),
                'card_set': hit.get('card_set'),
                'card_rarity': hit.get('card_rarity'),
                'quantity': hit.get('quantity'),
                'price': hit.get('price'),
                'currency': hit.get('currency'),
                'condition': hit.get('condition'),
                'language': hit.get('language'),
            })
    
    return results_list


# =============================================================================
# DECK CARD INDEX FUNCTIONS
# =============================================================================

def populate_deck_card_index():
    """
    Populate the deck-card index with all relationships from the database.
    
    Returns:
        int: Number of deck-card relationships indexed
    """
    from main.models import DeckCard
    
    ix = rebuild_index('deck_cards', DECK_CARD_SCHEMA)
    writer = ix.writer()
    
    count = 0
    for dc in DeckCard.objects.select_related('deck', 'card').all():
        writer.add_document(
            id_deck_card=str(dc.id_deck_card),
            deck_id=str(dc.deck_id),
            deck_name=dc.deck.name or '',
            card_id=str(dc.card_id),
            card_name=dc.card.name or '',
            card_name_exact=dc.card.name or '',
            card_set=dc.card.set or '',
            card_rarity=dc.card.rarity or '',
            quantity=dc.quantity or 0,
            role=dc.role or '',
        )
        count += 1
    
    writer.commit()
    return count


def search_deck_cards_by_deck(deck_id, limit=None):
    """
    Search deck cards by deck ID.
    
    Returns:
        List of deck-card dictionaries
    """
    ix = get_or_create_index('deck_cards', DECK_CARD_SCHEMA)
    results_list = []
    
    with ix.searcher() as searcher:
        query = Term("deck_id", str(deck_id))
        max_results = limit or 1000
        results = searcher.search(query, limit=max_results)
        
        for hit in results:
            results_list.append({
                'id_deck_card': int(hit['id_deck_card']),
                'deck_id': int(hit['deck_id']),
                'deck_name': hit.get('deck_name'),
                'card_id': int(hit['card_id']),
                'card_name': hit.get('card_name'),
                'card_set': hit.get('card_set'),
                'card_rarity': hit.get('card_rarity'),
                'quantity': hit.get('quantity'),
                'role': hit.get('role'),
            })
    
    return results_list


# =============================================================================
# FULL INDEX REBUILD
# =============================================================================

def populate_all_indexes():
    """
    Rebuild all Whoosh indexes from the database.
    
    Returns:
        dict: Count of items indexed for each entity type
    """
    return {
        'cards': populate_card_index(),
        'decks': populate_deck_index(),
        'sellers': populate_seller_index(),
        'seller_cards': populate_seller_card_index(),
        'deck_cards': populate_deck_card_index(),
    }
