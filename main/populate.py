import csv
import re
import os
from urllib.request import urlopen
from bs4 import BeautifulSoup
from main.models import Card, Seller, SellerCard, Deck, DeckCard, User, DeckRating

# Path to CSV files
CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "csv")
BASE_URL = "https://www.mtggoldfish.com"


def populate_database(num_users=500):
    """
    Main function to populate the database from CSV files and web scraping.
    Returns the count of cards, sellers, decks, users and ratings created.
    
    Args:
        num_users: Number of synthetic users to create for the rating system (default 500)
    """
    delete_tables()
    cards_count = populate_cards()
    sellers_count = populate_sellers()
    populate_seller_cards()
    decks_count = populate_decks()
    
    # Populate users and ratings for the recommendation system
    users_count, ratings_count = populate_user_ratings(num_users)
    
    return {
        'cards': cards_count, 
        'sellers': sellers_count, 
        'decks': decks_count,
        'users': users_count,
        'ratings': ratings_count
    }

def delete_tables():
    """
    Delete all records from all tables.
    """
    SellerCard.objects.all().delete()
    DeckCard.objects.all().delete()
    Seller.objects.all().delete()
    Card.objects.all().delete()
    Deck.objects.all().delete()
    User.objects.all().delete()
    DeckRating.objects.all().delete()


def parse_price(price_str, default_currency="EUR"):
    """
    Parse a price string like "0,05 €" or "£0.02" or "$5.99" to a float.
    Returns tuple (price, currency) or (None, default_currency) if cannot be parsed.
    """
    if not price_str:
        return None, default_currency
    
    price_str = price_str.strip()
    
    # Detect currency
    currency = default_currency
    if '€' in price_str:
        currency = "EUR"
    elif '£' in price_str:
        currency = "GBP"
    elif '$' in price_str:
        currency = "USD"
    
    # Remove currency symbols and whitespace
    price_str = re.sub(r'[€£$]', '', price_str).strip()
    
    # Replace comma with dot for decimal
    price_str = price_str.replace(',', '.')
    
    try:
        return float(price_str), currency
    except ValueError:
        return None, currency


def parse_price_simple(price_str):
    """
    Parse a price string to a float only (for backward compatibility).
    Returns None if the price cannot be parsed.
    """
    price, _ = parse_price(price_str)
    return price


def parse_int(value_str):
    """
    Parse an integer string, handling potential formatting.
    Returns 0 if the value cannot be parsed.
    """
    if not value_str:
        return 0
    
    # Remove any whitespace and non-numeric characters except digits
    value_str = re.sub(r'[^\d]', '', str(value_str))
    
    try:
        return int(value_str) if value_str else 0
    except ValueError:
        return 0


def populate_cards():
    """
    Populate the Card table from cards.csv.
    Returns the number of cards created.
    """
    cards_count = 0
    csv_file = os.path.join(CSV_PATH, "cards.csv")
    
    if not os.path.exists(csv_file):
        print(f"Error: {csv_file} not found")
        return 0
    
    # Count total lines to calculate progress reporting interval
    total_lines = sum(1 for _ in open(csv_file, 'r', encoding='utf-8')) - 1  # Exclude header
    progress_interval = max(100, total_lines // 10)  # Report max 10 times
    
    print(f"Populating cards from {total_lines} records...")
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row_num, row in enumerate(reader, 1):
            try:
                # Get version, use None if empty
                version = row.get('version', '').strip() or None
                
                card = Card(
                    name=row.get('name', ''),
                    version=version,
                    rarity=row.get('rarity'),
                    card_number=row.get('card_number'),
                    set=row.get('set', ''),
                    image_url=row.get('image_url'),
                    available_items=parse_int(row.get('available_items', '0')),
                    price_from=parse_price_simple(row.get('price_from')),
                    price_trend=parse_price_simple(row.get('price_trend')),
                    avg_30_days=parse_price_simple(row.get('avg_30_days')),
                    avg_7_days=parse_price_simple(row.get('avg_7_days')),
                    avg_1_day=parse_price_simple(row.get('avg_1_day'))
                )
                card.save()
                cards_count += 1
                
                # Show progress
                if row_num % progress_interval == 0:
                    percentage = (row_num / total_lines) * 100
                    print(f"  Progress: {row_num}/{total_lines} ({percentage:.1f}%) - {cards_count} cards created")
            except Exception as e:
                print(f"Error creating card {row.get('name', 'unknown')}: {e}")
                continue
    
    print(f"✓ Created {cards_count} cards")
    return cards_count


def populate_sellers():
    """
    Populate the Seller table from sellers.csv.
    Returns the number of sellers created.
    """
    sellers_count = 0
    csv_file = os.path.join(CSV_PATH, "sellers.csv")
    
    if not os.path.exists(csv_file):
        print(f"Error: {csv_file} not found")
        return 0
    
    # Count total lines to calculate progress reporting interval
    total_lines = sum(1 for _ in open(csv_file, 'r', encoding='utf-8')) - 1  # Exclude header
    progress_interval = max(100, total_lines // 10)  # Report max 10 times
    
    print(f"Populating sellers from {total_lines} records...")
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row_num, row in enumerate(reader, 1):
            try:
                # Parse shipping_days - can be empty
                shipping_days = None
                if row.get('shipping_days'):
                    try:
                        shipping_days = int(row.get('shipping_days'))
                    except ValueError:
                        shipping_days = None
                
                seller = Seller(
                    name=row.get('name', ''),
                    real_name=row.get('real_name'),
                    country=row.get('country', ''),
                    seller_type=row.get('seller_type', ''),
                    sales_count=parse_int(row.get('sales_count', '0')),
                    available_items=parse_int(row.get('available_items', '0')),
                    rating=row.get('rating', ''),
                    approval_very_good=row.get('approval_very_good'),
                    approval_good=row.get('approval_good'),
                    approval_neutral=row.get('approval_neutral'),
                    approval_bad=row.get('approval_bad'),
                    shipping_days=shipping_days,
                    street_address=row.get('street_address'),
                    postal_code=row.get('postal_code'),
                    city=row.get('city')
                )
                seller.save()
                sellers_count += 1
                
                # Show progress
                if row_num % progress_interval == 0:
                    percentage = (row_num / total_lines) * 100
                    print(f"  Progress: {row_num}/{total_lines} ({percentage:.1f}%) - {sellers_count} sellers created")
            except Exception as e:
                print(f"Error creating seller {row.get('name', 'unknown')}: {e}")
                continue
    
    print(f"✓ Created {sellers_count} sellers")
    return sellers_count


def populate_seller_cards():
    """
    Populate the SellerCard table from seller_cards.csv.
    Links sellers and cards with quantity, price, condition, language and currency.
    Uses card name, set and version for matching.
    Returns the number of seller-card relationships created.
    """
    seller_cards_count = 0
    csv_file = os.path.join(CSV_PATH, "seller_cards.csv")
    
    if not os.path.exists(csv_file):
        print(f"Error: {csv_file} not found")
        return 0
    
    # Count total lines to calculate progress reporting interval
    total_lines = sum(1 for _ in open(csv_file, 'r', encoding='utf-8')) - 1  # Exclude header
    progress_interval = max(100, total_lines // 10)  # Report max 10 times
    
    print(f"Populating seller-card relationships from {total_lines} records...")
    
    # Create lookup dictionaries for faster access
    sellers_dict = {seller.name: seller for seller in Seller.objects.all()}
    # Include version in card lookup key (name, set, version)
    cards_dict = {}
    for card in Card.objects.all():
        # Key with version
        key_with_version = (card.name, card.set, card.version)
        cards_dict[key_with_version] = card
        # Also add key without version for fallback
        key_without_version = (card.name, card.set, None)
        if key_without_version not in cards_dict:
            cards_dict[key_without_version] = card
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row_num, row in enumerate(reader, 1):
            try:
                card_name = row.get('card_name', '')
                set = row.get('set', '')
                seller_name = row.get('seller_name', '')
                version = row.get('version', '').strip() or None
                
                # Find the seller and card
                seller = sellers_dict.get(seller_name)
                
                # Try to find card with version first, then without
                card = cards_dict.get((card_name, set, version))
                if not card:
                    card = cards_dict.get((card_name, set, None))
                
                if not seller:
                    continue
                if not card:
                    continue
                
                # Parse quantity and price
                quantity = parse_int(row.get('quantity', '1'))
                if quantity < 1:
                    quantity = 1
                
                price, currency = parse_price(row.get('price'), "EUR")
                if price is None:
                    price = 0.0
                
                seller_card = SellerCard(
                    seller=seller,
                    card=card,
                    quantity=quantity,
                    price=price,
                    currency=currency,
                    condition=row.get('condition', ''),
                    language=row.get('language', '')
                )
                seller_card.save()
                seller_cards_count += 1
                
                # Show progress
                if row_num % progress_interval == 0:
                    percentage = (row_num / total_lines) * 100
                    print(f"  Progress: {row_num}/{total_lines} ({percentage:.1f}%) - {seller_cards_count} relationships created")
                
            except Exception as e:
                print(f"Error creating seller-card relationship: {e}")
                continue
    
    print(f"✓ Created {seller_cards_count} seller-card relationships")
    return seller_cards_count


# ============================================================================
# DECK SCRAPING FUNCTIONS
# ============================================================================

def populate_decks():
    """
    Populate the Deck table by scraping MTGGoldfish metagame pages.
    Also populates DeckCard intermediate table.
    Returns the number of decks created.
    """
    decks_count = 0
    url_base = f"{BASE_URL}/metagame/standard/full"
    
    try:
        # Get the first page to extract total number of pages
        html = urlopen(f"{url_base}#paper")
        soup = BeautifulSoup(html, "html.parser")
        
        # Extract number of available pages from pagination
        num_pages = extract_page_count(soup)
        print(f"Number of pages found: {num_pages}")
        
        # Iterate over all pages
        for page in range(1, num_pages + 1):
            if page == 1:
                page_url = f"{url_base}#paper"
            else:
                page_url = f"{url_base}?page={page}#paper"
            
            print(f"Processing page {page}: {page_url}")
            
            try:
                html_page = urlopen(page_url)
                soup_page = BeautifulSoup(html_page, "html.parser")
                
                # Extract archetype URLs from the current page (now includes meta percentage)
                archetype_data = extract_decks_from_page(soup_page)
                print(f"  Found {len(archetype_data)} archetypes on page {page}")
                
                # Process all archetypes from this page
                for archetype_url, archetype_meta in archetype_data:
                    try:
                        print(f"  Processing archetype: {archetype_url} (META: {archetype_meta}%)")
                        
                        # Extract individual deck URLs from this archetype
                        deck_urls = extract_individual_decks_from_archetype(archetype_url)
                        print(f"    Found {len(deck_urls)} individual decks")
                        
                        # Process all decks from this archetype
                        for deck_url in deck_urls:
                            try:
                                # Visit the specific deck page to get deck name, archetype, and cards
                                # Pass the meta percentage from the metagame page
                                deck_name, alternative_name, archetype, color_identity, colors_used, _, deck_cards = get_deck_details(deck_url)
                                meta_percentage = archetype_meta  # Use the meta from the metagame page
                                
                                if not deck_name:
                                    print(f"      Skipping deck with no name from {deck_url}")
                                    continue
                                
                                # Handle duplicate deck names by appending a number
                                base_name = deck_name
                                final_deck_name = base_name
                                counter = 1
                                while Deck.objects.filter(name=final_deck_name).exists():
                                    counter += 1
                                    final_deck_name = f"{base_name} ({counter})"
                                
                                # Create the Deck object
                                deck = Deck(
                                    name=final_deck_name,
                                    alternative_name=alternative_name or deck_name,
                                    archetype=archetype,
                                    color_identity=color_identity,
                                    colors_used=colors_used,
                                    meta_percentage=meta_percentage
                                )
                                deck.save()
                                decks_count += 1
                                print(f"      Deck saved: {final_deck_name} ({len(deck_cards)} cards)")
                                
                                # Populate DeckCard relationships only
                                populate_deck_cards(deck, deck_cards)
                                
                            except Exception as e:
                                print(f"      Error processing deck {deck_url}: {e}")
                                continue
                                
                    except Exception as e:
                        print(f"    Error processing archetype {archetype_url}: {e}")
                        continue
                        
            except Exception as e:
                print(f"Error processing page {page}: {e}")
                continue
                
    except Exception as e:
        print(f"Error accessing MTGGoldfish: {e}")
    
    print(f"Created {decks_count} decks")
    return decks_count


def extract_page_count(soup):
    """
    Extract the total number of pages from pagination.
    Searches for pagination links and gets the highest number.
    """
    num_pages = 1
    
    # Find all page links
    links = soup.find_all("a")
    
    for link in links:
        href = link.get("href", "")
        # Search for links containing ?page=
        if "page=" in href and "metagame/standard/full" in href:
            match = re.search(r'page=(\d+)', href)
            if match:
                page = int(match.group(1))
                if page > num_pages:
                    num_pages = page
    
    return num_pages


def extract_decks_from_page(soup):
    """
    Extract archetype URLs from a metagame page along with their meta percentages.
    Returns a list of tuples (archetype_url, meta_percentage).
    """
    archetype_data = []
    processed_urls = set()
    
    # Find all archetype containers - they have the META% info nearby
    # Look for elements containing "META%" text
    meta_pattern = re.compile(r'META%\s*(\d+\.?\d*)%')
    
    # Find all links pointing to archetypes
    links = soup.find_all("a")
    
    for link in links:
        href = link.get("href", "")
        
        # Filter only Standard archetype links
        if "/archetype/standard-" in href:
            # Clean the URL
            archetype_url = href.split("#")[0]  # Remove #paper, #online, etc.
            
            # Avoid duplicates
            if archetype_url in processed_urls:
                continue
            
            processed_urls.add(archetype_url)
            
            # Build full URL
            if not archetype_url.startswith("http"):
                archetype_url = BASE_URL + archetype_url
            
            # Try to find meta percentage near this link
            meta_percentage = 0.0
            parent = link.parent
            levels = 0
            while parent and parent.name != 'body' and levels < 8:
                parent_text = parent.get_text()
                match = meta_pattern.search(parent_text)
                if match:
                    meta_percentage = float(match.group(1))
                    break
                parent = parent.parent
                levels += 1
            
            archetype_data.append((archetype_url, meta_percentage))
    
    return archetype_data


def extract_individual_decks_from_archetype(archetype_url):
    """
    Visit an archetype page and extract individual deck URLs from tournament results.
    Returns a list of individual deck URLs.
    """
    deck_urls = []
    processed_urls = set()
    
    try:
        html = urlopen(archetype_url)
        soup = BeautifulSoup(html, "html.parser")
        
        # Find all links to individual decks
        links = soup.find_all("a")
        
        for link in links:
            href = link.get("href", "")
            
            # Look for individual deck links (e.g., /deck/7553859)
            # Avoid /edit, /visual, /download, etc.
            if re.match(r'/deck/\d+$', href):
                # Clean the URL
                deck_url = href.split("#")[0]  # Remove #paper, #online, etc.
                
                # Avoid duplicates
                if deck_url in processed_urls:
                    continue
                
                processed_urls.add(deck_url)
                
                # Build full URL
                if not deck_url.startswith("http"):
                    deck_url = BASE_URL + deck_url
                
                deck_urls.append(deck_url)
        
    except Exception as e:
        print(f"    Error extracting decks from {archetype_url}: {e}")
    
    return deck_urls


def extract_manacost_colors(link):
    """
    Extract deck colors by searching for spans with mana icons
    near the link. Colors are in classes like 'ms-w', 'ms-u', etc.
    """
    # Color code mapping
    code_to_color = {
        'w': 'W',  # White
        'u': 'U',  # Blue
        'b': 'B',  # Black
        'r': 'R',  # Red
        'g': 'G',  # Green
    }
    
    colors = []
    
    # Search in parent element and siblings
    parent = link.parent
    levels = 0
    while parent and parent.name != 'body' and levels < 5:
        # Find all spans that may have mana icons
        all_spans = parent.find_all("span", recursive=True)
        for span in all_spans:
            classes = span.get("class", [])
            if isinstance(classes, list):
                # Search in each individual class
                for cls in classes:
                    for code, color in code_to_color.items():
                        if cls == f"ms-{code}" and color not in colors:
                            colors.append(color)
            else:
                # It's a string
                for code, color in code_to_color.items():
                    if f"ms-{code}" in classes and color not in colors:
                        colors.append(color)
        
        # Also search <i> icons with mana classes
        all_icons = parent.find_all("i", recursive=True)
        for icon in all_icons:
            classes = icon.get("class", [])
            if isinstance(classes, list):
                for cls in classes:
                    for code, color in code_to_color.items():
                        if cls == f"ms-{code}" and color not in colors:
                            colors.append(color)
        
        if colors:
            break
        parent = parent.parent
        levels += 1
    
    # Sort colors in WUBRG order
    wubrg_order = ['W', 'U', 'B', 'R', 'G']
    sorted_colors = [c for c in wubrg_order if c in colors]
    
    return "".join(sorted_colors)


def extract_identity_and_archetype(deck_name):
    """
    Extract color identity and archetype from deck name.
    Valid archetypes are: Aggro, Control, Midrange, Combo, Tempo, Landfall, Dragons, Insidious Roots, Lessons, Artifacts.
    All others are classified as 'Other'.
    """
    name_lower = deck_name.lower()
    
    # Color identity dictionary
    identities = {
        'mono-red': 'Mono Red',
        'mono-white': 'Mono White',
        'mono-blue': 'Mono Blue',
        'mono-black': 'Mono Black',
        'mono-green': 'Mono Green',
        'izzet': 'Izzet',
        'dimir': 'Dimir',
        'azorius': 'Azorius',
        'orzhov': 'Orzhov',
        'boros': 'Boros',
        'selesnya': 'Selesnya',
        'golgari': 'Golgari',
        'simic': 'Simic',
        'rakdos': 'Rakdos',
        'gruul': 'Gruul',
        'esper': 'Esper',
        'grixis': 'Grixis',
        'jund': 'Jund',
        'naya': 'Naya',
        'bant': 'Bant',
        'abzan': 'Abzan',
        'jeskai': 'Jeskai',
        'sultai': 'Sultai',
        'mardu': 'Mardu',
        'temur': 'Temur',
        '4c': '4 Colors',
        '5c': '5 Colors',
    }
    
    color_identity = "Unknown"
    for key, identity in identities.items():
        if key in name_lower:
            color_identity = identity
            break
    
    # Extract archetype
    valid_archetypes = ['aggro', 'control', 'midrange', 'combo', 'tempo', 'landfall', 'dragons', 'insidious roots', 'lessons', 'artifacts']
    
    archetype = "Other"
    for arch in valid_archetypes:
        if arch in name_lower:
            archetype = arch.capitalize()
            break
    
    return color_identity, archetype


def extract_manacost_colors_from_soup(soup):
    """
    Extract deck colors by searching for mana symbols anywhere in the soup.
    Returns colors in WUBRG order as a string like "WUB".
    """
    # Color code mapping
    code_to_color = {
        'w': 'W',  # White
        'u': 'U',  # Blue
        'b': 'B',  # Black
        'r': 'R',  # Red
        'g': 'G',  # Green
    }
    
    colors = []
    
    # Find all spans and icons that may have mana symbols
    all_elements = soup.find_all(["span", "i"])
    
    for elem in all_elements:
        classes = elem.get("class", [])
        if not isinstance(classes, list):
            classes = [classes]
        
        for cls in classes:
            if isinstance(cls, str):
                # Look for mana symbols like 'ms-w', 'ms-u', etc.
                for code, color in code_to_color.items():
                    if f'ms-{code}' in cls.lower() and color not in colors:
                        colors.append(color)
    
    # Sort colors in WUBRG order
    wubrg_order = ['W', 'U', 'B', 'R', 'G']
    sorted_colors = [c for c in wubrg_order if c in colors]
    
    return "".join(sorted_colors)


def extract_meta_percentage(link, soup):
    """
    Extract the deck's meta percentage.
    Searches for text containing META% near the deck link.
    """
    meta_percentage = 0.0
    
    # Search parent element and siblings for META%
    parent = link.parent
    while parent:
        text = parent.get_text()
        # Search for META% pattern followed by a number
        match = re.search(r'META%\s*(\d+\.?\d*)%', text)
        if match:
            meta_percentage = float(match.group(1))
            break
        parent = parent.parent
        # Limit upward search
        if parent and parent.name == 'body':
            break
    
    return meta_percentage


def get_deck_details(deck_url):
    """
    Visit a specific individual deck page and extract the deck name, 
    alternative name, and card list from the hidden input field.
    Note: MTGGoldfish loads card categories (Creatures, Lands, etc.) via JavaScript
    which is not available through static HTML parsing. We extract from the hidden
    input field which only distinguishes maindeck vs sideboard.
    Returns tuple (deck_name, alternative_name, archetype, color_identity, colors_used, meta_percentage, cards_list).
    """
    deck_name = None
    alternative_name = None
    archetype = "Other"
    color_identity = "Unknown"
    colors_used = ""
    meta_percentage = 0.0
    cards_list = []
    
    try:
        html = urlopen(deck_url)
        soup = BeautifulSoup(html, "html.parser")
        
        # Find the h1 title containing the deck name and author
        h1 = soup.find("h1")
        if h1:
            h1_text = h1.get_text(strip=True)
            # Typical format is "Deck Nameby Author" or "Deck Name by Author"
            match = re.search(r'^(.+?)\s*by\s+', h1_text, re.IGNORECASE)
            if match:
                deck_name = match.group(1).strip()
            else:
                deck_name = h1_text.strip()
            
            # Extract archetype and color identity from deck name
            color_identity, archetype = extract_identity_and_archetype(deck_name)
            alternative_name = deck_name  # Use deck name as alternative name
        
        # Extract colors from mana symbols
        colors_used = extract_manacost_colors_from_soup(soup)
        
        # Extract cards from hidden input field (the only reliable source via static HTML)
        deck_input = soup.find("input", id="deck_input_deck")
        if deck_input:
            deck_text = deck_input.get("value", "")
            cards_list = parse_deck_text(deck_text)
        
    except Exception as e:
        print(f"    Error getting deck details from {deck_url}: {e}")
    
    return deck_name, alternative_name, archetype, color_identity, colors_used, meta_percentage, cards_list


def parse_deck_text(deck_text):
    """
    Parse deck text from the hidden input field.
    Format example: "4 Card Name\n3 Another Card\nsideboard\n2 Sideboard Card"
    Returns a list of dicts with card info: name, quantity, role.
    
    Note: The hidden input field does not contain card type information (Creature, Land, etc.)
    Only the distinction between maindeck and sideboard is available.
    """
    cards = []
    current_role = "Main Deck"  # Default role for maindeck cards
    
    # Role mapping for section headers
    role_mapping = {
        'sideboard': 'Sideboard',
        'side board': 'Sideboard',
        'side': 'Sideboard',
    }
    
    lines = deck_text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check if this is a role header (like "sideboard")
        line_lower = line.lower()
        if line_lower in role_mapping:
            current_role = role_mapping[line_lower]
            continue
        
        # Try to parse as "quantity card_name"
        match = re.match(r'(\d+)\s+(.+)', line)
        if match:
            quantity = int(match.group(1))
            card_name = match.group(2).strip()
            
            cards.append({
                'name': card_name,
                'quantity': quantity,
                'role': current_role
            })
    
    return cards

def populate_deck_cards(deck, deck_cards):
    """
    Populate DeckCard table for a specific deck.
    Only creates DeckCard entries, does not modify SellerCard table.
    
    Handles split card names (e.g., "Card A // Card B" or "Card A / Card B")
    by checking if any part of the split name matches a card in the database.
    """
    # Get all cards for lookup by name
    all_cards_by_name = {}
    # Also create a lookup for split card parts
    split_card_lookup = {}
    
    for card in Card.objects.all():
        # Store first card found with this name
        if card.name not in all_cards_by_name:
            all_cards_by_name[card.name] = card
        
        # If card name contains "//" or "/", index by each part
        if '//' in card.name:
            parts = [p.strip() for p in card.name.split('//')]
            for part in parts:
                if part and part not in split_card_lookup:
                    split_card_lookup[part] = card
        elif '/' in card.name:
            parts = [p.strip() for p in card.name.split('/')]
            for part in parts:
                if part and part not in split_card_lookup:
                    split_card_lookup[part] = card
    
    for card_info in deck_cards:
        card_name = card_info['name']
        
        # Try to find the card in the database by exact name first
        card = all_cards_by_name.get(card_name)
        
        if not card:
            # Try to find by split card parts
            card = split_card_lookup.get(card_name)
        
        if not card:
            # If the searched name has splits, try each part against exact names
            if '//' in card_name:
                search_parts = [p.strip() for p in card_name.split('//')]
                for part in search_parts:
                    card = all_cards_by_name.get(part)
                    if card:
                        break
            elif '/' in card_name:
                search_parts = [p.strip() for p in card_name.split('/')]
                for part in search_parts:
                    card = all_cards_by_name.get(part)
                    if card:
                        break
        
        if not card:
            # Card not found - skip it (don't create new cards)
            print(f"    Warning: Card '{card_name}' not found in database, skipping")
            continue
        
        # Create DeckCard relationship
        try:
            DeckCard.objects.create(
                deck=deck,
                card=card,
                quantity=card_info['quantity'],
                role=card_info['role']
            )
        except Exception as e:
            print(f"    Error creating DeckCard for {card_name}: {e}")


# =============================================================================
# USER RATINGS POPULATION
# =============================================================================

import random
from django.db import connection


def populate_user_ratings(num_users: int = 500) -> tuple:
    """
    Populate User and DeckRating tables with synthetic data for the recommendation system.
    
    Creates users with preferences for certain archetypes/colors,
    then generates ratings that are consistent with their preferences.
    
    Args:
        num_users: Number of synthetic users to create (default 500)
        
    Returns:
        Tuple of (users_count, ratings_count)
    """
    print(f"\nGenerating {num_users} users and their ratings...")
    
    # Clear existing user/rating data (already done in delete_tables, but ensure clean state)
    DeckRating.objects.all().delete()
    User.objects.all().delete()
    
    # Reset auto-increment counters to start from 1
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='main_user'")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='main_deckrating'")
    
    # Get all decks
    decks = list(Deck.objects.all())
    if not decks:
        print("No decks found in database. Skipping user ratings generation.")
        return (0, 0)
    
    # Extract unique archetypes and color identities from decks
    archetypes = list(set(d.archetype for d in decks if d.archetype))
    color_identities = list(set(d.color_identity for d in decks if d.color_identity))
    
    print(f"  Found {len(decks)} decks with {len(archetypes)} archetypes and {len(color_identities)} color identities")
    
    # Create users with preferences
    users = []
    for i in range(1, num_users + 1):
        user = User.objects.create(
            username=f"user_{i:04d}",
            preferred_archetype=random.choice(archetypes) if archetypes else None,
            preferred_colors=random.choice(color_identities) if color_identities else None
        )
        users.append(user)
    
    print(f"  Created {len(users)} users")
    
    # Generate ratings
    ratings_count = 0
    
    # Calculate max meta percentage for normalization
    max_meta = max(d.meta_percentage for d in decks) if decks else 1
    
    for user in users:
        # Each user rates a random subset of decks (30-80%)
        num_decks_to_rate = random.randint(int(len(decks) * 0.3), int(len(decks) * 0.8))
        decks_to_rate = random.sample(decks, min(num_decks_to_rate, len(decks)))
        
        for deck in decks_to_rate:
            # Base rating from meta percentage (0-5 scale)
            base_rating = (deck.meta_percentage / max_meta) * 3.0 + 1.0
            
            # Preference bonus
            preference_bonus = 0
            
            if user.preferred_archetype and deck.archetype == user.preferred_archetype:
                preference_bonus += random.uniform(0.3, 0.7)
            
            if user.preferred_colors and deck.color_identity == user.preferred_colors:
                preference_bonus += random.uniform(0.3, 0.7)
            
            # Partial color match bonus
            if user.preferred_colors and deck.colors_used:
                user_colors = set(user.preferred_colors.lower().split())
                deck_colors = set(deck.colors_used.lower().split())
                overlap = len(user_colors & deck_colors)
                if overlap > 0:
                    preference_bonus += overlap * 0.1
            
            # Random noise
            noise = random.gauss(0, 0.3)
            
            # Final rating (clamped to 0-5)
            final_rating = max(0, min(5, base_rating + preference_bonus + noise))
            final_rating = round(final_rating, 2)
            
            try:
                DeckRating.objects.create(
                    user=user,
                    deck=deck,
                    rating=final_rating
                )
                ratings_count += 1
            except Exception as e:
                print(f"    Error creating rating: {e}")
    
    print(f"  Generated {ratings_count} ratings")
    
    return (len(users), ratings_count)
