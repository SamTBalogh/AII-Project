from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.http import Http404
from main.populate import populate_database
from main.models import Deck, Card, Seller, SellerCard, DeckCard
from main.forms import CardFilterForm

# Import Whoosh utilities
from main.whoosh_utils import (
    search_cards, search_decks, search_sellers,
    search_seller_cards_by_card, search_seller_cards_by_seller,
    search_seller_cards_by_card_name, search_deck_cards_by_deck,
    get_card_by_id, get_deck_by_id, get_seller_by_id,
    get_unique_card_sets, get_unique_card_rarities,
    get_unique_deck_archetypes, get_unique_deck_color_identities,
    get_unique_seller_countries, get_unique_seller_types,
    populate_all_indexes
)


# =============================================================================
# HELPER CLASS FOR WHOOSH RESULTS
# =============================================================================

class WhooshResultProxy:
    """
    Proxy class to make Whoosh results behave like Django model instances.
    This allows templates to access fields using dot notation.
    """
    def __init__(self, data_dict):
        for key, value in data_dict.items():
            setattr(self, key, value)
    
    def __repr__(self):
        return f"<WhooshResultProxy: {self.__dict__}>"


def dict_to_proxy(data):
    """Convert a dict or list of dicts to WhooshResultProxy objects."""
    if isinstance(data, list):
        return [WhooshResultProxy(d) for d in data]
    return WhooshResultProxy(data)


# =============================================================================
# BASIC VIEWS
# =============================================================================

def index(request):
    return render(request, "index.html")


def populateDB(request):
    counts = populate_database()
    return render(request, "populatesuccess.html", {
        'cards': counts['cards'],
        'sellers': counts['sellers'],
        'decks': counts['decks'],
        'users': counts['users'],
        'ratings': counts['ratings'],
    })


def loadWhooshIndex(request):
    """Populate all Whoosh indexes from the database."""
    counts = populate_all_indexes()
    return render(request, "data_result.html", {
        'title': 'Load Whoosh Indexes',
        'description': 'Populated Whoosh indexes for full-text search.',
        'result_count': sum(counts.values()),
        'output_file': 'whoosh_index/',
        'sample_results': [
            f"Cards indexed: {counts['cards']}",
            f"Decks indexed: {counts['decks']}",
            f"Sellers indexed: {counts['sellers']}",
            f"Seller-Card relationships indexed: {counts['seller_cards']}",
            f"Deck-Card relationships indexed: {counts['deck_cards']}",
        ],
    })


# =============================================================================
# DECK VIEWS - USING WHOOSH
# =============================================================================

def decks(request):
    """
    View to display all decks with search filters.
    Uses Whoosh for searching.
    """
    # Get unique values for filters from Whoosh index
    color_identities = get_unique_deck_color_identities()
    archetypes = get_unique_deck_archetypes()
    
    # Get filter parameters from URL
    filter_name = request.GET.get('nombre', '').strip()
    filter_identity = request.GET.get('identidad_color', '').strip()
    filter_archetype = request.GET.get('arquetipo', '').strip()
    filter_meta_min = request.GET.get('meta_min', '').strip()
    filter_colors = request.GET.getlist('color')
    
    # Parse meta_min
    meta_min = None
    if filter_meta_min:
        try:
            meta_min = float(filter_meta_min)
        except ValueError:
            pass
    
    # Search using Whoosh
    deck_results = search_decks(
        name=filter_name or None,
        color_identity=filter_identity or None,
        archetype=filter_archetype or None,
        meta_min=meta_min,
        colors=filter_colors if filter_colors else None
    )
    
    # Convert to proxy objects for template compatibility
    decks_list = dict_to_proxy(deck_results)
    
    # Pagination - 50 decks per page
    paginator = Paginator(decks_list, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'mazos': page_obj,
        'identidades_color': color_identities,
        'arquetipos': archetypes,
        'filtro_nombre': filter_name,
        'filtro_identidad': filter_identity,
        'filtro_arquetipo': filter_archetype,
        'filtro_meta_min': filter_meta_min,
        'filtro_colores': filter_colors,
    }
    
    return render(request, "decks.html", context)


def deck_detail(request, deck_id):
    """
    View to display a single deck with all its cards.
    Uses Whoosh to get deck data, but Django ORM for the complex card relationships.
    """
    # Get deck from Whoosh
    deck_data = get_deck_by_id(deck_id)
    if not deck_data:
        raise Http404("Deck not found")
    
    deck = dict_to_proxy(deck_data)
    
    # Get deck cards from Whoosh
    deck_cards_data = search_deck_cards_by_deck(deck_id)
    
    # Define rarity order for sorting
    RARITY_ORDER = {
        'Mythic Rare': 1,
        'Mythic': 1,
        'Rare': 2,
        'Uncommon': 3,
        'Common': 4,
        'Special': 0,
        'Land': 5,
        None: 6,
        '': 6,
    }
    
    # Sort deck cards by role (non-sideboard first), then rarity, then name
    deck_cards_data.sort(key=lambda dc: (
        0 if dc.get('role') != 'Sideboard' else 1,
        RARITY_ORDER.get(dc.get('card_rarity'), 6),
        dc.get('card_name', '')
    ))
    
    # Enrich with card details from Whoosh
    deck_cards = []
    for dc in deck_cards_data:
        card_data = get_card_by_id(dc['card_id'])
        if card_data:
            dc_proxy = WhooshResultProxy(dc)
            dc_proxy.card = WhooshResultProxy(card_data)
            deck_cards.append(dc_proxy)
    
    # Calculate statistics
    total_cards = sum(dc.quantity for dc in deck_cards)
    total_price = 0.0
    card_count_by_role = {}
    
    for dc in deck_cards:
        # Count cards by role
        if dc.role not in card_count_by_role:
            card_count_by_role[dc.role] = 0
        card_count_by_role[dc.role] += dc.quantity
        
        # Calculate total price
        if dc.card.price_from:
            total_price += dc.card.price_from * dc.quantity
    
    # Calculate average price per card
    avg_price = total_price / total_cards if total_cards > 0 else 0.0
    
    context = {
        'deck': deck,
        'deck_cards': deck_cards,
        'total_cards': total_cards,
        'total_price': total_price,
        'avg_price': avg_price,
        'card_count_by_role': card_count_by_role,
    }
    
    return render(request, "deck_detail.html", context)


# =============================================================================
# CARD VIEWS - USING WHOOSH
# =============================================================================

def cards(request):
    """
    View to display all cards with search filters.
    Uses Whoosh for searching.
    """
    # Get filter parameters
    name = request.GET.get('name', '').strip()
    set_name = request.GET.get('set', '').strip()
    rarity = request.GET.get('rarity', '').strip()
    
    price_min = None
    price_max = None
    
    price_min_str = request.GET.get('price_min', '').strip()
    price_max_str = request.GET.get('price_max', '').strip()
    
    if price_min_str:
        try:
            price_min = float(price_min_str)
        except ValueError:
            pass
    
    if price_max_str:
        try:
            price_max = float(price_max_str)
        except ValueError:
            pass
    
    # Search using Whoosh
    card_results = search_cards(
        name=name or None,
        set_name=set_name or None,
        rarity=rarity or None,
        price_min=price_min,
        price_max=price_max
    )
    
    # Convert to proxy objects
    cards_list = dict_to_proxy(card_results)
    
    # Pagination - 50 cards per page
    paginator = Paginator(cards_list, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter choices from Whoosh
    sets = get_unique_card_sets()
    rarities = get_unique_card_rarities()
    
    # Create a form-like object for template compatibility
    form = WhooshResultProxy({
        'name': WhooshResultProxy({'value': name}),
        'set': WhooshResultProxy({'value': set_name, 'choices': [('', '-- All --')] + [(s, s) for s in sets]}),
        'price_min': WhooshResultProxy({'value': price_min_str}),
        'price_max': WhooshResultProxy({'value': price_max_str}),
        'rarity': WhooshResultProxy({'value': rarity, 'choices': [('', '-- All --')] + [(r, r) for r in rarities]}),
    })
    
    context = {
        'form': form,
        'cards': page_obj,
        'sets': sets,
        'rarities': rarities,
        'filter_name': name,
        'filter_set': set_name,
        'filter_rarity': rarity,
        'filter_price_min': price_min_str,
        'filter_price_max': price_max_str,
    }
    
    return render(request, "cards.html", context)


def card_detail(request, card_id):
    """
    View to display a single card and all sellers offering it.
    Uses Whoosh for searching.
    """
    # Get card from Whoosh
    card_data = get_card_by_id(card_id)
    if not card_data:
        raise Http404("Card not found")
    
    card = dict_to_proxy(card_data)
    
    # Get seller cards from Whoosh (already sorted by price)
    seller_cards_data = search_seller_cards_by_card(card_id)
    
    # Enrich with seller details
    seller_cards = []
    for sc in seller_cards_data:
        seller_data = get_seller_by_id(sc['seller_id'])
        if seller_data:
            sc_proxy = WhooshResultProxy(sc)
            sc_proxy.seller = WhooshResultProxy(seller_data)
            seller_cards.append(sc_proxy)
    
    context = {
        'card': card,
        'seller_cards': seller_cards,
    }
    
    return render(request, "card_detail.html", context)


# =============================================================================
# SELLER VIEWS - USING WHOOSH
# =============================================================================

def sellers(request):
    """
    View to display all sellers with search filters.
    Uses Whoosh for searching.
    """
    # Get unique values for filters from Whoosh
    countries = get_unique_seller_countries()
    seller_types = get_unique_seller_types()
    
    # Get filter parameters from URL
    filter_name = request.GET.get('name', '').strip()
    filter_country = request.GET.get('country', '').strip()
    filter_type = request.GET.get('seller_type', '').strip()
    
    # Search using Whoosh
    seller_results = search_sellers(
        name=filter_name or None,
        country=filter_country or None,
        seller_type=filter_type or None
    )
    
    # Convert to proxy objects
    sellers_list = dict_to_proxy(seller_results)
    
    # Pagination - 50 sellers per page
    paginator = Paginator(sellers_list, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'sellers': page_obj,
        'countries': countries,
        'seller_types': seller_types,
        'filter_name': filter_name,
        'filter_country': filter_country,
        'filter_type': filter_type,
    }
    
    return render(request, "sellers.html", context)


def seller_detail(request, seller_id):
    """
    View to display a single seller and all cards they offer.
    Uses Whoosh for searching.
    """
    # Get seller from Whoosh
    seller_data = get_seller_by_id(seller_id)
    if not seller_data:
        raise Http404("Seller not found")
    
    seller = dict_to_proxy(seller_data)
    
    # Get seller cards from Whoosh (already sorted by card name)
    seller_cards_data = search_seller_cards_by_seller(seller_id)
    
    # Enrich with card details
    seller_cards = []
    for sc in seller_cards_data:
        card_data = get_card_by_id(sc['card_id'])
        if card_data:
            sc_proxy = WhooshResultProxy(sc)
            sc_proxy.card = WhooshResultProxy(card_data)
            seller_cards.append(sc_proxy)
    
    context = {
        'seller': seller,
        'seller_cards': seller_cards,
    }
    
    return render(request, "seller_detail.html", context)


# =============================================================================
# SHIPPING COSTS CONFIGURATION
# =============================================================================

CARD_WEIGHT_GRAMS = 1.8

SHIPPING_RATES = {
    'Spain': [
        (20, 0.70), (50, 1.15), (100, 1.55), (250, 2.50),
        (500, 3.80), (1000, 5.50), (2000, 7.50),
    ],
    'Portugal': [
        (20, 1.20), (50, 1.80), (100, 2.40), (250, 3.50),
        (500, 5.00), (1000, 7.00), (2000, 9.50),
    ],
    'France': [
        (20, 1.50), (50, 2.20), (100, 3.00), (250, 4.50),
        (500, 6.50), (1000, 9.00), (2000, 12.00),
    ],
    'Germany': [
        (20, 1.60), (50, 2.40), (100, 3.20), (250, 5.00),
        (500, 7.00), (1000, 10.00), (2000, 14.00),
    ],
    'Italy': [
        (20, 1.60), (50, 2.50), (100, 3.40), (250, 5.20),
        (500, 7.50), (1000, 10.50), (2000, 14.50),
    ],
    'Netherlands': [
        (20, 1.70), (50, 2.60), (100, 3.50), (250, 5.50),
        (500, 8.00), (1000, 11.00), (2000, 15.00),
    ],
    'Belgium': [
        (20, 1.65), (50, 2.50), (100, 3.40), (250, 5.30),
        (500, 7.80), (1000, 10.80), (2000, 14.80),
    ],
    'Austria': [
        (20, 1.80), (50, 2.80), (100, 3.80), (250, 6.00),
        (500, 8.50), (1000, 12.00), (2000, 16.00),
    ],
    'United Kingdom': [
        (20, 2.50), (50, 3.50), (100, 5.00), (250, 8.00),
        (500, 12.00), (1000, 16.00), (2000, 22.00),
    ],
    'Poland': [
        (20, 1.90), (50, 2.90), (100, 4.00), (250, 6.50),
        (500, 9.00), (1000, 13.00), (2000, 17.50),
    ],
    'Czech Republic': [
        (20, 1.85), (50, 2.85), (100, 3.90), (250, 6.30),
        (500, 8.80), (1000, 12.50), (2000, 17.00),
    ],
    'Switzerland': [
        (20, 2.80), (50, 4.00), (100, 5.50), (250, 9.00),
        (500, 13.00), (1000, 18.00), (2000, 25.00),
    ],
    'Greece': [
        (20, 2.00), (50, 3.00), (100, 4.20), (250, 6.80),
        (500, 9.50), (1000, 13.50), (2000, 18.00),
    ],
    'Sweden': [
        (20, 2.20), (50, 3.30), (100, 4.60), (250, 7.50),
        (500, 10.50), (1000, 15.00), (2000, 20.00),
    ],
    'Finland': [
        (20, 2.40), (50, 3.60), (100, 5.00), (250, 8.00),
        (500, 11.50), (1000, 16.00), (2000, 22.00),
    ],
    'Denmark': [
        (20, 2.10), (50, 3.20), (100, 4.40), (250, 7.20),
        (500, 10.00), (1000, 14.50), (2000, 19.50),
    ],
    'Norway': [
        (20, 2.80), (50, 4.20), (100, 5.80), (250, 9.50),
        (500, 13.50), (1000, 19.00), (2000, 26.00),
    ],
    'Ireland': [
        (20, 2.00), (50, 3.00), (100, 4.20), (250, 7.00),
        (500, 10.00), (1000, 14.00), (2000, 19.00),
    ],
    'Hungary': [
        (20, 1.80), (50, 2.80), (100, 3.80), (250, 6.00),
        (500, 8.50), (1000, 12.00), (2000, 16.50),
    ],
    'Bulgaria': [
        (20, 1.70), (50, 2.60), (100, 3.60), (250, 5.80),
        (500, 8.00), (1000, 11.50), (2000, 15.50),
    ],
    'Croatia': [
        (20, 1.85), (50, 2.80), (100, 3.80), (250, 6.20),
        (500, 8.70), (1000, 12.20), (2000, 16.70),
    ],
    'Cyprus': [
        (20, 2.20), (50, 3.40), (100, 4.80), (250, 7.80),
        (500, 11.00), (1000, 15.50), (2000, 21.00),
    ],
    'Estonia': [
        (20, 2.00), (50, 3.10), (100, 4.30), (250, 7.00),
        (500, 10.00), (1000, 14.00), (2000, 19.00),
    ],
    'Latvia': [
        (20, 1.95), (50, 3.00), (100, 4.20), (250, 6.80),
        (500, 9.50), (1000, 13.50), (2000, 18.50),
    ],
    'Luxembourg': [
        (20, 1.60), (50, 2.50), (100, 3.40), (250, 5.50),
        (500, 8.00), (1000, 11.00), (2000, 15.00),
    ],
    'Slovakia': [
        (20, 1.85), (50, 2.85), (100, 3.90), (250, 6.30),
        (500, 8.80), (1000, 12.50), (2000, 17.00),
    ],
    'Slovenia': [
        (20, 1.80), (50, 2.80), (100, 3.80), (250, 6.10),
        (500, 8.60), (1000, 12.10), (2000, 16.60),
    ],
}

DEFAULT_SHIPPING_RATES = [
    (20, 2.50), (50, 3.80), (100, 5.20), (250, 8.50),
    (500, 12.00), (1000, 17.00), (2000, 23.00),
]


def calculate_shipping_cost(country, num_cards):
    """Calculate estimated shipping cost from a country to Spain based on weight."""
    total_weight = (num_cards * CARD_WEIGHT_GRAMS) + 5
    rates = SHIPPING_RATES.get(country, DEFAULT_SHIPPING_RATES)
    
    for max_weight, cost in rates:
        if total_weight <= max_weight:
            return cost
    
    return rates[-1][1]


# =============================================================================
# DECK OPTIMIZATION VIEWS - USING WHOOSH
# =============================================================================

def deck_optimize_price(request, deck_id):
    """
    View to show the best price optimization for a deck.
    Uses Whoosh to find sellers and prices.
    """
    # Get deck from Whoosh
    deck_data = get_deck_by_id(deck_id)
    if not deck_data:
        raise Http404("Deck not found")
    
    deck = dict_to_proxy(deck_data)
    
    # Get deck cards from Whoosh
    deck_cards_data = search_deck_cards_by_deck(deck_id)
    
    # Build the purchase plan
    purchase_plan = []
    cards_not_found = []
    
    for dc in deck_cards_data:
        card_id = dc['card_id']
        card_name = dc['card_name']
        card_set = dc['card_set']
        card_rarity = dc.get('card_rarity', '')
        quantity_needed = dc['quantity']
        role = dc.get('role', '')
        
        # Get card details
        card_data = get_card_by_id(card_id)
        if not card_data:
            continue
        
        card = WhooshResultProxy(card_data)
        
        # For lands, search by name across all expansions
        # For non-lands, search by name and set
        if card_rarity == 'Land':
            offers = search_seller_cards_by_card_name(card_name)
        else:
            offers = search_seller_cards_by_card_name(card_name, card_set)
        
        if not offers:
            cards_not_found.append({
                'card': card,
                'quantity': quantity_needed,
                'role': role,
            })
            continue
        
        # Allocate from cheapest sellers until we have enough
        quantity_remaining = quantity_needed
        for offer in offers:
            if quantity_remaining <= 0:
                break
            
            qty_to_buy = min(quantity_remaining, offer['quantity'])
            
            # Get seller details
            seller_data = get_seller_by_id(offer['seller_id'])
            if not seller_data:
                continue
            
            seller = WhooshResultProxy(seller_data)
            offer_card_data = get_card_by_id(offer['card_id'])
            offer_card = WhooshResultProxy(offer_card_data) if offer_card_data else card
            
            purchase_plan.append({
                'card': offer_card,
                'original_card': card,
                'seller': seller,
                'quantity': qty_to_buy,
                'unit_price': offer['price'],
                'subtotal': offer['price'] * qty_to_buy,
                'currency': offer.get('currency', 'EUR'),
                'condition': offer.get('condition', ''),
                'role': role,
            })
            
            quantity_remaining -= qty_to_buy
        
        if quantity_remaining > 0:
            cards_not_found.append({
                'card': card,
                'quantity': quantity_remaining,
                'role': role,
                'partial': True,
            })
    
    # Calculate totals and group by seller
    total_cards_price = sum(p['subtotal'] for p in purchase_plan)
    
    sellers_summary = {}
    for p in purchase_plan:
        seller_id = p['seller'].id_seller
        if seller_id not in sellers_summary:
            sellers_summary[seller_id] = {
                'seller': p['seller'],
                'cards_count': 0,
                'subtotal': 0,
            }
        sellers_summary[seller_id]['cards_count'] += p['quantity']
        sellers_summary[seller_id]['subtotal'] += p['subtotal']
    
    # Calculate shipping
    total_shipping = 0
    for seller_id, data in sellers_summary.items():
        shipping = calculate_shipping_cost(data['seller'].country, data['cards_count'])
        data['shipping'] = shipping
        total_shipping += shipping
    
    total_price = total_cards_price + total_shipping
    
    context = {
        'deck': deck,
        'purchase_plan': purchase_plan,
        'cards_not_found': cards_not_found,
        'sellers_summary': list(sellers_summary.values()),
        'total_cards_price': total_cards_price,
        'total_shipping': total_shipping,
        'total_price': total_price,
        'num_sellers': len(sellers_summary),
    }
    
    return render(request, "deck_optimize_price.html", context)


def deck_optimize_shipping(request, deck_id):
    """
    View to show the best shipping optimization for a deck.
    Minimizes the number of different sellers using a greedy algorithm.
    Uses Whoosh for searching.
    """
    # Get deck from Whoosh
    deck_data = get_deck_by_id(deck_id)
    if not deck_data:
        raise Http404("Deck not found")
    
    deck = dict_to_proxy(deck_data)
    
    # Get deck cards from Whoosh
    deck_cards_data = search_deck_cards_by_deck(deck_id)
    
    # Build cards_needed dict
    cards_needed = {}
    land_names = set()
    non_land_card_keys = {}
    
    for dc in deck_cards_data:
        card_data = get_card_by_id(dc['card_id'])
        if not card_data:
            continue
        
        card = WhooshResultProxy(card_data)
        card_rarity = dc.get('card_rarity', '')
        
        if card_rarity == 'Land':
            land_key = f"land_{dc['card_name']}"
            land_names.add(dc['card_name'])
            if land_key in cards_needed:
                cards_needed[land_key]['quantity'] += dc['quantity']
            else:
                cards_needed[land_key] = {
                    'card': card,
                    'quantity': dc['quantity'],
                    'role': dc.get('role', ''),
                    'is_land': True,
                    'name': dc['card_name'],
                    'set': dc.get('card_set', ''),
                }
        else:
            card_key = f"card_{dc['card_name']}_{dc.get('card_set', '')}"
            if card_key in cards_needed:
                cards_needed[card_key]['quantity'] += dc['quantity']
            else:
                cards_needed[card_key] = {
                    'card': card,
                    'quantity': dc['quantity'],
                    'role': dc.get('role', ''),
                    'is_land': False,
                    'name': dc['card_name'],
                    'set': dc.get('card_set', ''),
                }
            non_land_card_keys[(dc['card_name'], dc.get('card_set', ''))] = card_key
    
    # Get all offers
    all_offers = []
    for (name, card_set), card_key in non_land_card_keys.items():
        offers = search_seller_cards_by_card_name(name, card_set)
        for offer in offers:
            offer['_card_key'] = card_key
        all_offers.extend(offers)
    
    for land_name in land_names:
        offers = search_seller_cards_by_card_name(land_name)
        for offer in offers:
            offer['_card_key'] = f"land_{land_name}"
        all_offers.extend(offers)
    
    # Build seller_offers dict
    seller_offers = {}
    for offer in all_offers:
        seller_id = offer['seller_id']
        if seller_id not in seller_offers:
            seller_data = get_seller_by_id(seller_id)
            seller_offers[seller_id] = {
                'seller': WhooshResultProxy(seller_data) if seller_data else None,
                'offers': {}
            }
        
        card_key = offer['_card_key']
        if card_key not in seller_offers[seller_id]['offers']:
            seller_offers[seller_id]['offers'][card_key] = []
        seller_offers[seller_id]['offers'][card_key].append(offer)
    
    # Remove sellers without valid data
    seller_offers = {k: v for k, v in seller_offers.items() if v['seller'] is not None}
    
    # Greedy algorithm
    purchase_plan = []
    cards_not_found = []
    
    while any(v['quantity'] > 0 for v in cards_needed.values()) and seller_offers:
        best_seller_id = None
        best_score = 0
        best_purchase = []
        
        for seller_id, seller_data in seller_offers.items():
            score = 0
            temp_purchase = []
            
            for card_key, card_info in cards_needed.items():
                if card_info['quantity'] <= 0:
                    continue
                
                if card_key in seller_data['offers']:
                    offers = sorted(seller_data['offers'][card_key], key=lambda x: x['price'])
                    for offer in offers:
                        qty_to_buy = min(card_info['quantity'], offer['quantity'])
                        if qty_to_buy > 0:
                            offer_card_data = get_card_by_id(offer['card_id'])
                            offer_card = WhooshResultProxy(offer_card_data) if offer_card_data else card_info['card']
                            
                            score += qty_to_buy
                            temp_purchase.append({
                                'card': offer_card,
                                'original_card': card_info['card'],
                                'seller': seller_data['seller'],
                                'quantity': qty_to_buy,
                                'unit_price': offer['price'],
                                'subtotal': offer['price'] * qty_to_buy,
                                'currency': offer.get('currency', 'EUR'),
                                'condition': offer.get('condition', ''),
                                'role': card_info['role'],
                                'card_key': card_key,
                            })
                            break
            
            if score > best_score:
                best_score = score
                best_seller_id = seller_id
                best_purchase = temp_purchase
        
        if best_score == 0:
            break
        
        purchase_plan.extend(best_purchase)
        
        for purchase in best_purchase:
            card_key = purchase['card_key']
            cards_needed[card_key]['quantity'] -= purchase['quantity']
        
        del seller_offers[best_seller_id]
    
    # Check for remaining cards
    for card_key, card_info in cards_needed.items():
        if card_info['quantity'] > 0:
            cards_not_found.append({
                'card': card_info['card'],
                'quantity': card_info['quantity'],
                'role': card_info['role'],
            })
    
    # Calculate totals
    total_cards_price = sum(p['subtotal'] for p in purchase_plan)
    
    sellers_summary = {}
    for p in purchase_plan:
        seller_id = p['seller'].id_seller
        if seller_id not in sellers_summary:
            sellers_summary[seller_id] = {
                'seller': p['seller'],
                'cards_count': 0,
                'subtotal': 0,
            }
        sellers_summary[seller_id]['cards_count'] += p['quantity']
        sellers_summary[seller_id]['subtotal'] += p['subtotal']
    
    total_shipping = 0
    for seller_id, data in sellers_summary.items():
        shipping = calculate_shipping_cost(data['seller'].country, data['cards_count'])
        data['shipping'] = shipping
        total_shipping += shipping
    
    total_price = total_cards_price + total_shipping
    
    context = {
        'deck': deck,
        'purchase_plan': purchase_plan,
        'cards_not_found': cards_not_found,
        'sellers_summary': list(sellers_summary.values()),
        'total_cards_price': total_cards_price,
        'total_shipping': total_shipping,
        'total_price': total_price,
        'num_sellers': len(sellers_summary),
    }
    
    return render(request, "deck_optimize_shipping.html", context)


# =============================================================================
# DATA EXTRACTION VIEWS
# =============================================================================

import os
import sys

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
sys.path.insert(0, DATA_DIR)

from main.data import (
    generate_set_urls,
    extract_card_links,
    extract_card_data,
    extract_seller_links,
    extract_seller_data,
    extract_seller_card_data,
    rename_card_html_files
)


def data_generate_set_urls(request):
    """Generate CardMarket URLs for all Standard sets."""
    output_file = os.path.join(DATA_DIR, 'links', 'sets.txt')
    urls = generate_set_urls(output_file)
    
    return render(request, "data_result.html", {
        'title': 'Generate Set URLs',
        'description': 'Generated CardMarket URLs for all Standard format sets.',
        'result_count': len(urls),
        'output_file': output_file,
        'sample_results': urls[:20] if urls else [],
    })


def data_extract_card_links(request):
    """Extract card links from set HTML files."""
    html_folder = os.path.join(DATA_DIR, 'html', 'sets')
    output_file = os.path.join(DATA_DIR, 'links', 'cards.txt')
    links = extract_card_links(html_folder, output_file)
    
    return render(request, "data_result.html", {
        'title': 'Extract Card Links',
        'description': 'Extracted card links from set HTML files.',
        'result_count': len(links),
        'output_file': output_file,
        'sample_results': links[:20] if links else [],
    })


def data_extract_card_data(request):
    """Extract card data from card HTML files."""
    html_folder = os.path.join(DATA_DIR, 'html', 'cards')
    output_file = os.path.join(DATA_DIR, 'csv', 'cards.csv')
    cards = extract_card_data(html_folder, output_file)
    
    return render(request, "data_result.html", {
        'title': 'Extract Card Data',
        'description': 'Extracted card data from card HTML files.',
        'result_count': len(cards),
        'output_file': output_file,
        'sample_results': [
            f"{c['name']} ({c['set']}) - {c['rarity']}" 
            for c in cards[:20]
        ] if cards else [],
    })


def data_extract_seller_links(request):
    """Extract seller links from card HTML files."""
    html_folder = os.path.join(DATA_DIR, 'html', 'cards')
    output_file = os.path.join(DATA_DIR, 'links', 'sellers.txt')
    links = extract_seller_links(html_folder, output_file)
    
    return render(request, "data_result.html", {
        'title': 'Extract Seller Links',
        'description': 'Extracted seller links from card HTML files.',
        'result_count': len(links),
        'output_file': output_file,
        'sample_results': links[:20] if links else [],
    })


def data_extract_seller_data(request):
    """Extract seller data from seller HTML files."""
    html_folder = os.path.join(DATA_DIR, 'html', 'sellers')
    output_file = os.path.join(DATA_DIR, 'csv', 'sellers.csv')
    sellers = extract_seller_data(html_folder, output_file)
    
    return render(request, "data_result.html", {
        'title': 'Extract Seller Data',
        'description': 'Extracted seller data from seller HTML files.',
        'result_count': len(sellers),
        'output_file': output_file,
        'sample_results': [
            f"{s['name']} ({s['country']}) - {s['sales_count']} sales" 
            for s in sellers[:20]
        ] if sellers else [],
    })


def data_extract_seller_card_data(request):
    """Extract seller card data from card HTML files."""
    html_folder = os.path.join(DATA_DIR, 'html', 'cards')
    output_file = os.path.join(DATA_DIR, 'csv', 'seller_cards.csv')
    seller_cards = extract_seller_card_data(html_folder, output_file)
    
    return render(request, "data_result.html", {
        'title': 'Extract Seller Card Data',
        'description': 'Extracted seller card availability from card HTML files.',
        'result_count': len(seller_cards),
        'output_file': output_file,
        'sample_results': [
            f"{sc['seller_name']}: {sc['card_name']} - €{sc['price']}" 
            for sc in seller_cards[:20]
        ] if seller_cards else [],
    })


def data_rename_card_files(request):
    """Rename card HTML files based on their line number in cards.txt."""
    html_folder = os.path.join(DATA_DIR, 'html', 'cards')
    links_file = os.path.join(DATA_DIR, 'links', 'cards.txt')
    result = rename_card_html_files(html_folder, links_file)
    
    return render(request, "data_result.html", {
        'title': 'Rename Card Files',
        'description': f"Renamed card HTML files based on cards.txt line numbers. Renamed: {result['renamed']}, Skipped: {result['skipped']}, Errors: {result['errors']}",
        'result_count': result['renamed'],
        'output_file': html_folder,
        'sample_results': [
            f"Format: NNNN_CardName_SetName.html (e.g., 0001_Aatchik-Emerald-Radian_Aetherdrift.html)"
        ],
    })


# =============================================================================
# USER RATINGS VIEWS
# =============================================================================

from main.data import generate_user_ratings
from main.recommendations import load_recsys_data, get_recommended_decks, get_similar_users
from main.recommendations_content import (
    load_content_recsys_data, 
    get_content_recommended_decks, 
    get_similar_decks,
    get_user_preferred_features
)
from main.models import User
from main.forms import UserIdForm, GenerateRatingsForm


def generate_ratings(request):
    """Generate synthetic user ratings for the recommendation system."""
    form = GenerateRatingsForm(request.POST or None)
    
    if request.method == 'POST' and form.is_valid():
        num_users = form.cleaned_data['num_users']
        output_file = os.path.join(DATA_DIR, 'csv', 'user_ratings.csv')
        result = generate_user_ratings(num_users=num_users, output_file=output_file)
        
        return render(request, "data_result.html", {
            'title': 'Generate User Ratings',
            'description': f"Generated {result['users']} users and {result['ratings']} ratings for the recommendation system.",
            'result_count': result['ratings'],
            'output_file': output_file,
            'sample_results': [
                f"{r['username']} -> {r['deck_name']}: {r['rating']:.2f}" 
                for r in result.get('csv_data', [])[:20]
            ] if result.get('csv_data') else [],
        })
    
    return render(request, "generate_ratings_form.html", {
        'form': form,
    })


# =============================================================================
# RECOMMENDATION SYSTEM VIEWS
# =============================================================================

def loadRS(request):
    """Load the collaborative filtering recommendation system data."""
    num_users = load_recsys_data()
    return render(request, "loadRS.html", {
        'num_users': num_users
    })


def loadContentRS(request):
    """Load the content-based recommendation system data."""
    num_decks = load_content_recsys_data()
    return render(request, "data_result.html", {
        'title': 'Load Content-Based RS',
        'description': 'Loaded content-based recommendation system data.',
        'result_count': num_decks,
        'output_file': 'dataRS_content.dat',
        'sample_results': [
            f"Deck profiles created: {num_decks}",
            "Features indexed: archetype, color_identity, colors, cards",
        ],
    })


def recommendedDecks(request):
    """
    Display recommended decks for a user ID input.
    Uses collaborative filtering based on user ratings.
    """
    form = UserIdForm(request.GET or None)
    
    recommendations = []
    similar_users = []
    selected_user = None
    error_message = None
    
    if request.GET.get('user_id'):
        if form.is_valid():
            user_id = form.cleaned_data['user_id']
            try:
                selected_user = User.objects.get(id_user=user_id)
                recommendations = get_recommended_decks(user_id, n=10)
                similar_users = get_similar_users(user_id, n=5)
            except User.DoesNotExist:
                error_message = f"User with ID {user_id} not found in the database."
        else:
            error_message = "Please enter a valid user ID (positive integer)."
    
    context = {
        'form': form,
        'selected_user': selected_user,
        'recommendations': recommendations,
        'similar_users': similar_users,
        'error_message': error_message,
    }
    
    return render(request, "recommended_decks.html", context)


def recommendedDecksContent(request):
    """
    Display recommended decks for a user ID input.
    Uses content-based filtering based on deck characteristics.
    """
    form = UserIdForm(request.GET or None)
    
    recommendations = []
    similar_decks = []
    user_preferences = None
    selected_user = None
    error_message = None
    
    if request.GET.get('user_id'):
        if form.is_valid():
            user_id = form.cleaned_data['user_id']
            try:
                selected_user = User.objects.get(id_user=user_id)
                
                # Get content-based recommendations
                recommendations = get_content_recommended_decks(user_id, n=10)
                
                # Get user preferences analysis
                user_preferences = get_user_preferred_features(user_id)
                
                # Get similar decks to the user's highest rated deck
                from main.models import DeckRating
                top_rating = DeckRating.objects.filter(user_id=user_id).order_by('-rating').first()
                if top_rating:
                    similar_decks = get_similar_decks(top_rating.deck_id, n=5)
                    # Convert similarity to percentage
                    similar_decks = [(sim * 100, deck) for sim, deck in similar_decks]
                
            except User.DoesNotExist:
                error_message = f"User with ID {user_id} not found in the database."
        else:
            error_message = "Please enter a valid user ID (positive integer)."
    
    context = {
        'form': form,
        'selected_user': selected_user,
        'recommendations': recommendations,
        'similar_decks': similar_decks,
        'user_preferences': user_preferences,
        'error_message': error_message,
    }
    
    return render(request, "recommended_decks_content.html", context)
