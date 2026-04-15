"""
Module for extracting links from CardMarket HTML files.
"""
import os
import re
import csv
from bs4 import BeautifulSoup

SET_URL_LIST = [
    "Magic-The-Gathering-Avatar-The-Last-Airbender",
    "Magic-The-Gathering-Marvels-Spider-Man",
    "Edge-of-Eternities",
    "Magic-The-Gathering-Final-Fantasy",
    "Tarkir-Dragonstorm",
    "Aetherdrift",
    "Magic-The-Gathering-Foundations",
    "Magic-The-Gathering-Foundations-Starter-Collection",
    "Duskmourn-House-of-Horror",
    "Bloomburrow",
    "Outlaws-of-Thunder-Junction",
    "The-Big-Score",
    "Murders-at-Karlov-Manor",
    "The-Lost-Caverns-of-Ixalan",
    "Wilds-of-Eldraine",
]


# =============================================================================
# SET FUNCTIONS
# =============================================================================

def generate_set_urls(output_file: str = None) -> list:
    """
    Generates CardMarket URLs for all Standard format sets.
    Each set will have 10 URLs (site=1 to site=10).
    
    Args:
        output_file: Path to the output .txt file (optional)
    
    Returns:
        List of generated URLs
    """
    base_url = "https://www.cardmarket.com/en/Magic/Products/Singles"
    urls = []
    
    for slug in SET_URL_LIST:
        for site in range(1, 11):  # site from 1 to 10
            url = f"{base_url}/{slug}?idRarity=0&site={site}"
            urls.append(url)
    
    print(f"Generated {len(urls)} URLs for {len(SET_URL_LIST)} sets.")
    
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for url in urls:
                    f.write(url + '\n')
            print(f"URLs saved to: {output_file}")
        except Exception as e:
            print(f"Error saving file: {e}")
    
    return urls


# =============================================================================
# CARD FUNCTIONS
# =============================================================================

def extract_card_links(html_folder: str, output_file: str = None) -> list:
    """
    Extracts all card links from HTML files in a folder.
    
    Args:
        html_folder: Path to the folder containing HTML files
        output_file: Path to the output .txt file (optional)
    
    Returns:
        List of complete card URLs
    """
    card_links = set()  # Using set to avoid duplicates
    base_url = "https://www.cardmarket.com"
    
    # Get all HTML files from the folder
    if not os.path.exists(html_folder):
        print(f"Error: Folder '{html_folder}' does not exist.")
        return []
    
    html_files = [f for f in os.listdir(html_folder) if f.endswith('.html')]
    
    if not html_files:
        print(f"No HTML files found in '{html_folder}'")
        return []
    
    print(f"Processing {len(html_files)} HTML files...")
    
    for file in html_files:
        file_path = os.path.join(html_folder, file)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the HTML
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find all links pointing to Singles
            for link in soup.find_all('a', href=True):
                href = link['href']
                # Modify link to include desired parameters
                params = "?sellerType=1,2&minCondition=4&isFoil=N&isSigned=N&isAltered=N"
                if '/en/Magic/Products/Singles/' in href:
                    # Build complete URL
                    if href.startswith('/'):
                        full_url = base_url + href + params
                    else:
                        full_url = href + params
                    card_links.add(full_url)
        
        except Exception as e:
            print(f"  Error processing {file}: {e}")
    
    # Convert to list and sort
    links_list = sorted(list(card_links))
    
    print(f"\nFound {len(links_list)} unique card links.")
    
    # Save to file if specified
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for link in links_list:
                    f.write(link + '\n')
            print(f"Links saved to: {output_file}")
        except Exception as e:
            print(f"Error saving file: {e}")
    
    return links_list


def extract_card_data(html_folder: str, output_file: str = None) -> list:
    """
    Extracts card data from HTML files and exports to CSV.
    
    Extracts the following fields from each card:
    - name: Card name
    - rarity: Card rarity (Common, Uncommon, Rare, Mythic Rare)
    - number: Card number in the set
    - set: Set name
    - image_url: Card image URL
    - available_items: Number of available items for sale
    - price_from: Minimum price
    - price_trend: Price trend
    - avg_30_days: 30-day average price
    - avg_7_days: 7-day average price
    - avg_1_day: 1-day average price
    
    Args:
        html_folder: Path to the folder containing card HTML files
        output_file: Path to the output CSV file (optional)
    
    Returns:
        List of dictionaries with card data
    """
    cards_data = []
    
    # Verify folder exists
    if not os.path.exists(html_folder):
        print(f"Error: Folder '{html_folder}' does not exist.")
        return []
    
    html_files = [f for f in os.listdir(html_folder) if f.endswith('.html')]
    
    if not html_files:
        print(f"No HTML files found in '{html_folder}'")
        return []
    
    print(f"Processing {len(html_files)} HTML files to extract card data...")
    
    for i, file in enumerate(html_files, 1):
        file_path = os.path.join(html_folder, file)
        
        # Show progress every 500 files
        if i % 500 == 0:
            print(f"  Processed {i}/{len(html_files)} files...")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the HTML
            soup = BeautifulSoup(content, 'html.parser')
            
            # Initialize card data dictionary
            card = {
                'name': '',
                'version': '',
                'rarity': '',
                'card_number': '',
                'set': '',
                'image_url': '',
                'available_items': '',
                'price_from': '',
                'price_trend': '',
                'avg_30_days': '',
                'avg_7_days': '',
                'avg_1_day': ''
            }
            
            # Extract card name and version from the page title
            # Title format: "Card Name (V.1) (SET) - MTG Singles | Cardmarket"
            # or without version: "Card Name (SET) - MTG Singles | Cardmarket"
            title_tag = soup.find('title')
            if title_tag:
                title_text = title_tag.get_text(strip=True)
                # Remove the suffix " - MTG Singles | Cardmarket"
                title_clean = re.sub(r'\s*-\s*MTG Singles\s*\|\s*Cardmarket\s*$', '', title_text)
                # Now we have "Card Name (V.1) (SET)" or "Card Name (SET)"
                # Extract version if present (V.X pattern before the set code)
                version_match = re.search(r'\((V\.\d+)\)\s*\([^)]+\)\s*$', title_clean)
                if version_match:
                    card['version'] = version_match.group(1)
                    # Remove version and set code from name
                    card['name'] = re.sub(r'\s*\(V\.\d+\)\s*\([^)]+\)\s*$', '', title_clean).strip()
                else:
                    # No version, just remove the set code at the end
                    card['name'] = re.sub(r'\s*\([^)]+\)\s*$', '', title_clean).strip()
            
            # Extract image URL from the card image
            card_img = soup.find('img', class_='is-front')
            if card_img:
                card['image_url'] = card_img.get('src', '')
            
            # Find the info-list-container with all card data
            info_container = soup.find('div', class_='info-list-container')
            if info_container:
                # Find all dt/dd pairs in the labeled dl
                dl = info_container.find('dl', class_='labeled')
                if dl:
                    dt_elements = dl.find_all('dt')
                    dd_elements = dl.find_all('dd')
                    
                    # Create a dictionary of label -> value pairs
                    for dt, dd in zip(dt_elements, dd_elements):
                        label = dt.get_text(strip=True)
                        
                        # Handle different fields based on label
                        if label == 'Rarity':
                            # Rarity is in an SVG with aria-label
                            svg = dd.find('svg')
                            if svg:
                                card['rarity'] = svg.get('aria-label', '')
                        
                        elif label == 'Number':
                            card['card_number'] = dd.get_text(strip=True)
                        
                        elif label == 'Printed in':
                            # Set name is in a link
                            exp_link = dd.find('a', class_='mb-2')
                            if exp_link:
                                card['set'] = exp_link.get_text(strip=True)
                        
                        elif label == 'Available items':
                            card['available_items'] = dd.get_text(strip=True)
                        
                        elif label == 'From':
                            card['price_from'] = dd.get_text(strip=True)
                        
                        elif label == 'Price Trend':
                            card['price_trend'] = dd.get_text(strip=True)
                        
                        elif label == '30-days average price':
                            card['avg_30_days'] = dd.get_text(strip=True)
                        
                        elif label == '7-days average price':
                            card['avg_7_days'] = dd.get_text(strip=True)
                        
                        elif label == '1-day average price':
                            card['avg_1_day'] = dd.get_text(strip=True)
            
            # Only add card if we got at least the name
            if card['name']:
                cards_data.append(card)
        
        except Exception as e:
            print(f"  Error processing {file}: {e}")
    
    print(f"\nExtracted data from {len(cards_data)} cards.")
    
    # Save to CSV file if specified
    if output_file and cards_data:
        try:
            # Define CSV headers
            headers = [
                'name', 'version', 'rarity', 'card_number', 'set', 'image_url',
                'available_items', 'price_from', 'price_trend',
                'avg_30_days', 'avg_7_days', 'avg_1_day'
            ]
            
            with open(output_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(cards_data)
            
            print(f"Card data saved to: {output_file}")
        except Exception as e:
            print(f"Error saving CSV file: {e}")
    
    return cards_data


# =============================================================================
# VENDOR FUNCTIONS
# =============================================================================

def extract_seller_links(html_folder: str, output_file: str = None) -> list:
    """
    Extracts all unique seller links from card HTML files.
    
    Args:
        html_folder: Path to the folder containing card HTML files
        output_file: Path to the output .txt file (optional)
    
    Returns:
        List of unique seller URLs
    """
    seller_links = set()  # Using set to avoid duplicates
    base_url = "https://www.cardmarket.com"
    
    # Verify folder exists
    if not os.path.exists(html_folder):
        print(f"Error: Folder '{html_folder}' does not exist.")
        return []
    
    html_files = [f for f in os.listdir(html_folder) if f.endswith('.html')]
    
    if not html_files:
        print(f"No HTML files found in '{html_folder}'")
        return []
    
    print(f"Processing {len(html_files)} HTML files to extract sellers...")
    
    for i, file in enumerate(html_files, 1):
        file_path = os.path.join(html_folder, file)
        
        # Show progress every 500 files
        if i % 500 == 0:
            print(f"  Processed {i}/{len(html_files)} files...")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the HTML
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find all links pointing to user/seller profiles
            # Pattern: /en/Magic/Users/{SellerName}
            for link in soup.find_all('a', href=True):
                href = link['href']
                if '/en/Magic/Users/' in href:
                    # Build complete URL
                    if href.startswith('/'):
                        full_url = base_url + href
                    else:
                        full_url = href
                    seller_links.add(full_url)
        
        except Exception as e:
            print(f"  Error processing {file}: {e}")
    
    # Convert to list and sort
    links_list = sorted(list(seller_links))
    
    print(f"\nFound {len(links_list)} unique sellers.")
    
    # Save to file if specified
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for link in links_list:
                    f.write(link + '\n')
            print(f"Seller links saved to: {output_file}")
        except Exception as e:
            print(f"Error saving file: {e}")
    
    return links_list


def extract_seller_data(html_folder: str, output_file: str = None) -> list:
    """
    Extracts seller profile data from HTML files for the Vendedor table.
    
    Extracts the following fields from each seller profile:
    - name: Seller username
    - real_name: Real name (if available)
    - country: Seller's country
    - seller_type: Type of seller (Private, Powerseller, Professional, etc.)
    - sales_count: Number of completed sales
    - available_items: Number of available items for sale
    - rating: Overall rating (Outstanding, Very Good, Good, etc.)
    - approval_very_good: Percentage of Very Good evaluations
    - approval_good: Percentage of Good evaluations
    - approval_neutral: Percentage of Neutral evaluations
    - approval_bad: Percentage of Bad evaluations
    - shipping_days: Estimated shipping days
    - street_address: Street address
    - postal_code: Postal code
    - city: City
    
    Args:
        html_folder: Path to the folder containing seller HTML files
        output_file: Path to the output CSV file (optional)
    
    Returns:
        List of dictionaries with seller data
    """
    sellers_data = []
    
    # Verify folder exists
    if not os.path.exists(html_folder):
        print(f"Error: Folder '{html_folder}' does not exist.")
        return []
    
    html_files = [f for f in os.listdir(html_folder) if f.endswith('.html')]
    
    if not html_files:
        print(f"No HTML files found in '{html_folder}'")
        return []
    
    print(f"Processing {len(html_files)} HTML files to extract seller data...")
    
    for i, file in enumerate(html_files, 1):
        file_path = os.path.join(html_folder, file)
        
        # Show progress every 200 files
        if i % 200 == 0:
            print(f"  Processed {i}/{len(html_files)} files...")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the HTML
            soup = BeautifulSoup(content, 'html.parser')
            
            # Initialize seller data dictionary
            seller = {
                'name': '',
                'real_name': '',
                'country': '',
                'seller_type': '',
                'sales_count': '',
                'available_items': '',
                'rating': '',
                'approval_very_good': '',
                'approval_good': '',
                'approval_neutral': '',
                'approval_bad': '',
                'shipping_days': '',
                'street_address': '',
                'postal_code': '',
                'city': ''
            }
            
            # Extract seller username from headline
            headline = soup.find('h1', id='PublicProfileHeadline')
            if headline:
                seller['name'] = headline.get_text(strip=True)
            
            # Extract seller type (Private, Powerseller, Professional)
            # Look for icons like fonticon-users-powerseller, fonticon-users-professional, fonticon-users
            # Order matters: check most specific first (powerseller before professional, then generic Private)
            for class_suffix in ['powerseller', 'professional', '']:
                class_name = f'fonticon-users-{class_suffix}' if class_suffix else 'fonticon-users'
                seller_type_icon = soup.find('span', class_=lambda x: x and class_name in str(x))
                if seller_type_icon:
                    seller['seller_type'] = seller_type_icon.get('aria-label', '')
                    if seller['seller_type']:
                        break
            
            # Extract sales count and available items from badge tooltip
            # Format: "2339&nbsp;Sales&nbsp;|&nbsp;30824&nbsp;Available items"
            sales_badge = soup.find('span', class_='badge', attrs={'data-bs-original-title': lambda x: x and 'Sales' in str(x)})
            if sales_badge:
                tooltip_text = sales_badge.get('data-bs-original-title', '')
                # Replace &nbsp; with space for easier parsing
                tooltip_text = tooltip_text.replace('&nbsp;', ' ').replace('\xa0', ' ')
                
                # Extract sales count
                sales_match = re.search(r'(\d+)\s*Sales', tooltip_text)
                if sales_match:
                    seller['sales_count'] = sales_match.group(1)
                
                # Extract available items
                available_match = re.search(r'(\d+)\s*Available', tooltip_text)
                if available_match:
                    seller['available_items'] = available_match.group(1)
            
            # Alternative extraction from div with aria-label (for sellers like Crossover, Arcana-Trieste)
            # Format: aria-label="119560 Sales | 10030 Available items"
            if not seller['sales_count'] or not seller['available_items']:
                sales_div = soup.find('div', class_='d-inline-flex', attrs={'aria-label': lambda x: x and 'Sales' in str(x)})
                if sales_div:
                    aria_text = sales_div.get('aria-label', '')
                    # Extract sales count
                    sales_match = re.search(r'(\d+)\s*Sales', aria_text)
                    if sales_match and not seller['sales_count']:
                        seller['sales_count'] = sales_match.group(1)
                    # Extract available items
                    available_match = re.search(r'(\d+)\s*Available', aria_text)
                    if available_match and not seller['available_items']:
                        seller['available_items'] = available_match.group(1)
            
            # Another alternative extraction from collapsible <dl> section
            if not seller['sales_count'] or not seller['available_items']:
                dl_section = soup.find('dl', class_='row')
                if dl_section:
                    dt_elements = dl_section.find_all('dt')
                    for dt in dt_elements:
                        dt_text = dt.get_text(strip=True)
                        dd = dt.find_next_sibling('dd')
                        if dd:
                            dd_text = dd.get_text(strip=True)
                            if dt_text == 'Sales' and not seller['sales_count']:
                                seller['sales_count'] = dd_text
                            elif 'Available' in dt_text and not seller['available_items']:
                                seller['available_items'] = dd_text
            
            # Extract rating (Outstanding, Very Good, Good, etc.)
            rating_icon = soup.find('span', class_=lambda x: x and 'fonticon-seller-rating' in str(x))
            if rating_icon:
                seller['rating'] = rating_icon.get('aria-label', '')
            
            # Extract approval percentages from Overall Evaluation row
            # Look for the row with "Overall Evaluation" text
            all_spans = soup.find_all('span', class_='personalInfo-light')
            for span in all_spans:
                if 'Overall Evaluation' in span.get_text():
                    # Find the parent row
                    parent_row = span.find_parent('div', class_='row')
                    if parent_row:
                        # Find all evaluation icons and their percentages
                        eval_divs = parent_row.find_all('div', class_=lambda x: x and 'col' in str(x))
                        for div in eval_divs:
                            icon = div.find('span', class_=lambda x: x and 'fonticon-shipment-evaluation' in str(x))
                            pct_span = div.find('span', class_='mt-n1')
                            if icon and pct_span:
                                icon_classes = ' '.join(icon.get('class', []))
                                pct_text = pct_span.get_text(strip=True)
                                
                                if 'very-good' in icon_classes:
                                    seller['approval_very_good'] = pct_text
                                elif 'evaluation-good' in icon_classes and 'very' not in icon_classes:
                                    seller['approval_good'] = pct_text
                                elif 'neutral' in icon_classes:
                                    seller['approval_neutral'] = pct_text
                                elif 'bad' in icon_classes:
                                    seller['approval_bad'] = pct_text
                    break
            
            # Extract shipping days - look for the "days to you" section
            # Structure: <span class="h2 me-2 mb-0">24</span><span class="lead">days to you</span>
            lead_spans = soup.find_all('span', class_='lead')
            for lead in lead_spans:
                lead_text = lead.get_text(strip=True)
                if 'days to' in lead_text.lower():
                    # Get the sibling span with class h2 that contains the number
                    sibling = lead.find_previous_sibling('span')
                    if sibling:
                        sibling_classes = sibling.get('class', [])
                        # Make sure it's the h2 span but NOT a fonticon (vacation icon)
                        if 'h2' in sibling_classes or 'me-2' in sibling_classes:
                            # Check it's not a fonticon element
                            if not any('fonticon' in c for c in sibling_classes):
                                days_text = sibling.get_text(strip=True)
                                if days_text.isdigit():
                                    seller['shipping_days'] = days_text
                                    break
            
            # Extract country from flag icon using onmouseover showMsgBox
            country_icons = soup.find_all('span', attrs={'onmouseover': lambda x: x and 'showMsgBox' in str(x)})
            for icon in country_icons:
                mouseover = icon.get('onmouseover', '')
                country_match = re.search(r"showMsgBox\(this,`([^`]+)`\)", mouseover)
                if country_match:
                    country_name = country_match.group(1)
                    # Skip non-country values like language names
                    if country_name not in ['English', 'French', 'German', 'Spanish', 'Italian', 'Description of items', 'Packaging of shipment']:
                        seller['country'] = country_name
                        break
            
            # Extract address information from PersonalInfoRow
            personal_info = soup.find('div', id='PersonalInfoRow')
            if personal_info:
                # Find all personalInfo divs
                info_divs = personal_info.find_all('div', class_='personalInfo')
                
                for info_div in info_divs:
                    paragraphs = info_div.find_all('p', class_='mb-1')
                    
                    # Check if this div contains address (has country flag icon in parent)
                    parent_row = info_div.find_parent('div', class_='row')
                    if parent_row:
                        # Look for flag icon with onmouseover containing country
                        flag = parent_row.find('span', attrs={'onmouseover': lambda x: x and 'showMsgBox' in str(x)})
                        if flag and len(paragraphs) >= 2:
                            # This is likely the address section
                            address_lines = [p.get_text(strip=True) for p in paragraphs]
                            
                            if len(address_lines) >= 1:
                                seller['street_address'] = address_lines[0]
                            if len(address_lines) >= 2:
                                # Parse postal code + city in various formats:
                                # German/Spanish: "36204 Vigo" or "13088 Berlin"
                                # UK: "KY12 7EA Dunfermline" or "S80 1QJ Worksop"
                                # Poland: "30-394 Kraków"
                                postal_city = address_lines[1]
                                
                                # Try UK format first: 1-2 letters, 1-2 digits, optional letter, space, digit, 2 letters
                                uk_match = re.match(r'^([A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2})\s+(.+)$', postal_city, re.IGNORECASE)
                                if uk_match:
                                    seller['postal_code'] = uk_match.group(1).upper()
                                    seller['city'] = uk_match.group(2)
                                # Try Ireland format: D02XE80, A65F4E2, etc. (letter + 2 digits + alphanumeric)
                                elif re.match(r'^([A-Z]\d{2}\s?[A-Z0-9]{2,4})\s+(.+)$', postal_city, re.IGNORECASE):
                                    ie_match = re.match(r'^([A-Z]\d{2}\s?[A-Z0-9]{2,4})\s+(.+)$', postal_city, re.IGNORECASE)
                                    seller['postal_code'] = ie_match.group(1).upper().replace(' ', '')
                                    seller['city'] = ie_match.group(2)
                                # Try Latvia format: LV-XXXX, e.g. "LV-1001 Riga"
                                elif re.match(r'^(LV-\d{4})\s+(.+)$', postal_city, re.IGNORECASE):
                                    lv_match = re.match(r'^(LV-\d{4})\s+(.+)$', postal_city, re.IGNORECASE)
                                    seller['postal_code'] = lv_match.group(1).upper()
                                    seller['city'] = lv_match.group(2)
                                # Try Netherlands format: 4 digits + 2 letters (no space), e.g. "6811AZ Arnhem"
                                elif re.match(r'^(\d{4}[A-Z]{2})\s+(.+)$', postal_city, re.IGNORECASE):
                                    nl_match = re.match(r'^(\d{4}[A-Z]{2})\s+(.+)$', postal_city, re.IGNORECASE)
                                    seller['postal_code'] = nl_match.group(1).upper()
                                    seller['city'] = nl_match.group(2)
                                # Try Portugal format: XXXX-XXX, e.g. "2675-271 Odivelas"
                                elif re.match(r'^(\d{4}-\d{3})\s+(.+)$', postal_city):
                                    pt_match = re.match(r'^(\d{4}-\d{3})\s+(.+)$', postal_city)
                                    seller['postal_code'] = pt_match.group(1)
                                    seller['city'] = pt_match.group(2)
                                # Try Poland format: XX-XXX, e.g. "30-394 Kraków"
                                elif re.match(r'^(\d{2}-\d{3})\s+(.+)$', postal_city):
                                    poland_match = re.match(r'^(\d{2}-\d{3})\s+(.+)$', postal_city)
                                    seller['postal_code'] = poland_match.group(1)
                                    seller['city'] = poland_match.group(2)
                                # Try standard numeric format (Germany, Spain, etc.)
                                elif re.match(r'^(\d+)\s+(.+)$', postal_city):
                                    numeric_match = re.match(r'^(\d+)\s+(.+)$', postal_city)
                                    seller['postal_code'] = numeric_match.group(1)
                                    seller['city'] = numeric_match.group(2)
                                else:
                                    # No postal code found, just use as city
                                    seller['city'] = postal_city
                            if len(address_lines) >= 3:
                                # Country is usually last, but we already have it
                                if not seller['country']:
                                    seller['country'] = address_lines[2]
                        elif not flag and paragraphs:
                            # This might be the real name section (no flag icon)
                            seller['real_name'] = paragraphs[0].get_text(strip=True)
            
            # Only add seller if we got at least the name
            if seller['name']:
                sellers_data.append(seller)
        
        except Exception as e:
            print(f"  Error processing {file}: {e}")
    
    print(f"\nExtracted data from {len(sellers_data)} sellers.")
    
    # Save to CSV file if specified
    if output_file and sellers_data:
        try:
            # Define CSV headers
            headers = [
                'name', 'real_name', 'country', 'seller_type', 'sales_count',
                'available_items', 'rating', 'approval_very_good', 'approval_good', 
                'approval_neutral', 'approval_bad', 'shipping_days',
                'street_address', 'postal_code', 'city'
            ]
            
            with open(output_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(sellers_data)
            
            print(f"Seller data saved to: {output_file}")
        except Exception as e:
            print(f"Error saving CSV file: {e}")
    
    return sellers_data


def extract_seller_card_data(html_folder: str, output_file: str = None) -> list:
    """
    Extracts seller-card relationship data from HTML files for the VendedorCarta table.
    
    Extracts the following fields from each article row:
    - card_name: Name of the card (from the page)
    - set: Set name (to differentiate reprints/basic lands)
    - seller_name: Name of the seller
    - quantity: Available quantity
    - price: Unit price
    - condition: Card condition (MT, NM, EX, GD, LP, PL, PO)
    - language: Card language (English, Spanish, French, etc.)
    
    Args:
        html_folder: Path to the folder containing card HTML files
        output_file: Path to the output CSV file (optional)
    
    Returns:
        List of dictionaries with seller-card relationship data
    """
    seller_card_data = []
    
    # Verify folder exists
    if not os.path.exists(html_folder):
        print(f"Error: Folder '{html_folder}' does not exist.")
        return []
    
    html_files = [f for f in os.listdir(html_folder) if f.endswith('.html')]
    
    if not html_files:
        print(f"No HTML files found in '{html_folder}'")
        return []
    
    print(f"Processing {len(html_files)} HTML files to extract seller-card data...")
    
    for i, file in enumerate(html_files, 1):
        file_path = os.path.join(html_folder, file)
        
        # Show progress every 500 files
        if i % 500 == 0:
            print(f"  Processed {i}/{len(html_files)} files...")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the HTML
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract card name and version from the page title
            # Title format: "Card Name (V.1) (SET) - MTG Singles | Cardmarket"
            # or without version: "Card Name (SET) - MTG Singles | Cardmarket"
            title_tag = soup.find('title')
            if title_tag:
                title_text = title_tag.get_text(strip=True)
                # Remove the suffix " - MTG Singles | Cardmarket"
                title_clean = re.sub(r'\s*-\s*MTG Singles\s*\|\s*Cardmarket\s*$', '', title_text)
                # Now we have "Card Name (V.1) (SET)" or "Card Name (SET)"
                # Extract version if present (V.X pattern before the set code)
                version_match = re.search(r'\((V\.\d+)\)\s*\([^)]+\)\s*$', title_clean)
                if version_match:
                    card_version = version_match.group(1)
                    # Remove version and set code from name
                    card_name = re.sub(r'\s*\(V\.\d+\)\s*\([^)]+\)\s*$', '', title_clean).strip()
                else:
                    # No version, just remove the set code at the end
                    card_name = re.sub(r'\s*\([^)]+\)\s*$', '', title_clean).strip()
                    # Reset the version
                    card_version = ''
            
            # Get set name from the info-list-container
            info_container = soup.find('div', class_='info-list-container')
            if info_container:
                dl = info_container.find('dl', class_='labeled')
                if dl:
                    dt_elements = dl.find_all('dt')
                    dd_elements = dl.find_all('dd')
                    for dt, dd in zip(dt_elements, dd_elements):
                        label = dt.get_text(strip=True)
                        if label == 'Printed in':
                            exp_link = dd.find('a', class_='mb-2')
                            if exp_link:
                                card_set = exp_link.get_text(strip=True)
                            break
            
            # Find all article rows (each represents a seller offer)
            article_rows = soup.find_all('div', class_='article-row')
            
            for row in article_rows:
                try:

                    record = {
                        'card_name': card_name,
                        'version': card_version,
                        'set': card_set,
                        'seller_name': '',
                        'quantity': '',
                        'price': '',
                        'condition': '',
                        'language': ''
                    }
                    
                    # Extract seller name from the link
                    seller_link = row.find('a', href=lambda x: x and '/en/Magic/Users/' in x)
                    if seller_link:
                        record['seller_name'] = seller_link.get_text(strip=True)
                    
                    # Extract quantity (item-count)
                    quantity_span = row.find('span', class_='item-count')
                    if quantity_span:
                        record['quantity'] = quantity_span.get_text(strip=True)
                    
                    # Extract price (color-primary with price)
                    price_span = row.find('span', class_=lambda x: x and 'color-primary' in x and 'fw-bold' in x)
                    if price_span:
                        record['price'] = price_span.get_text(strip=True)
                    
                    # Extract condition from article-condition element
                    condition_elem = row.find('a', class_=lambda x: x and 'article-condition' in str(x))
                    if condition_elem:
                        # Get condition from data-bs-original-title or aria-label
                        condition = condition_elem.get('data-bs-original-title', '') or condition_elem.get('aria-label', '')
                        record['condition'] = condition
                    
                    # Extract language from icon with aria-label
                    # Look for language icon in product-attributes
                    product_attrs = row.find('div', class_='product-attributes')
                    if product_attrs:
                        lang_icon = product_attrs.find('span', attrs={'aria-label': True})
                        if lang_icon:
                            record['language'] = lang_icon.get('aria-label', '')
                    
                    # Only add record if we have seller name
                    if record['seller_name']:
                        seller_card_data.append(record)
                
                except Exception as e:
                    continue  # Skip problematic rows
        
        except Exception as e:
            print(f"  Error processing {file}: {e}")
    
    print(f"\nExtracted {len(seller_card_data)} seller-card relationships.")
    
    # Save to CSV file if specified
    if output_file and seller_card_data:
        try:
            # Define CSV headers
            headers = [
                'card_name', 'version', 'set', 'seller_name', 'quantity', 'price',
                'condition', 'language'
            ]
            
            with open(output_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(seller_card_data)
            
            print(f"Seller-card data saved to: {output_file}")
        except Exception as e:
            print(f"Error saving CSV file: {e}")
    
    return seller_card_data


# =============================================================================
# USER RATINGS GENERATION
# =============================================================================

import random
from main.models import User, DeckRating, Deck


def generate_user_ratings(num_users: int = 500, output_file: str = None) -> dict:
    """
    Generate synthetic user ratings for the recommendation system.
    
    Creates users with preferences for certain archetypes/colors,
    then generates ratings that are consistent with their preferences:
    - Higher meta% decks get higher average ratings
    - Users rate decks matching their preferred archetype/colors higher
    - Some randomness to simulate real user behavior
    
    Args:
        num_users: Number of synthetic users to create (default 500)
        output_file: Optional path to save CSV file
        
    Returns:
        Dictionary with counts: {'users': n, 'ratings': n}
    """
    from django.db import connection
    
    # Clear existing data
    DeckRating.objects.all().delete()
    User.objects.all().delete()
    
    # Reset auto-increment counters to start from 1
    with connection.cursor() as cursor:
        # SQLite syntax for resetting autoincrement
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='main_user'")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='main_deckrating'")
    
    # Get all decks
    decks = list(Deck.objects.all())
    if not decks:
        print("No decks found in database. Please populate decks first.")
        return {'users': 0, 'ratings': 0}
    
    # Extract unique archetypes and color identities from decks
    archetypes = list(set(d.archetype for d in decks if d.archetype))
    color_identities = list(set(d.color_identity for d in decks if d.color_identity))
    
    print(f"Found {len(decks)} decks with {len(archetypes)} archetypes and {len(color_identities)} color identities")
    
    # Create users with preferences
    users = []
    for i in range(1, num_users + 1):
        user = User.objects.create(
            username=f"user_{i:04d}",
            preferred_archetype=random.choice(archetypes) if archetypes else None,
            preferred_colors=random.choice(color_identities) if color_identities else None
        )
        users.append(user)
    
    print(f"Created {len(users)} users")
    
    # Generate ratings
    ratings_data = []
    ratings_count = 0
    
    # Calculate max meta percentage for normalization
    max_meta = max(d.meta_percentage for d in decks) if decks else 1
    
    for user in users:
        # Each user rates a random subset of decks (30-80%)
        num_decks_to_rate = random.randint(int(len(decks) * 0.3), int(len(decks) * 0.8))
        decks_to_rate = random.sample(decks, min(num_decks_to_rate, len(decks)))
        
        for deck in decks_to_rate:
            # Base rating from meta percentage (0-5 scale)
            # Higher meta% = higher base rating
            base_rating = (deck.meta_percentage / max_meta) * 3.0 + 1.0  # Range: 1.0 - 4.0
            
            # Preference bonus: +0.5 to +1.0 if matches user preferences
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
            
            # Random noise to simulate human behavior
            noise = random.gauss(0, 0.3)
            
            # Calculate final rating (clamped to 0-5)
            final_rating = max(0, min(5, base_rating + preference_bonus + noise))
            final_rating = round(final_rating, 2)
            
            # Create rating
            try:
                DeckRating.objects.create(
                    user=user,
                    deck=deck,
                    rating=final_rating
                )
                ratings_count += 1
                
                # Store for CSV
                ratings_data.append({
                    'user_id': user.id_user,
                    'username': user.username,
                    'deck_name': deck.name,
                    'deck_alternative_name': deck.alternative_name or '',
                    'rating': final_rating
                })
            except Exception as e:
                print(f"Error creating rating for {user.username} -> {deck.name}: {e}")
    
    print(f"Generated {ratings_count} ratings")
    
    # Save to CSV if output file specified
    if output_file:
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['user_id', 'username', 'deck_name', 'deck_alternative_name', 'rating'])
                writer.writeheader()
                writer.writerows(ratings_data)
            print(f"Ratings saved to: {output_file}")
        except Exception as e:
            print(f"Error saving CSV: {e}")
    
    return {'users': len(users), 'ratings': ratings_count, 'csv_data': ratings_data}


# =============================================================================
# HTML FILE RENAMING
# =============================================================================

def rename_card_html_files(html_folder: str, links_file: str) -> dict:
    """
    Renames HTML files in the cards folder based on their corresponding line 
    in the cards.txt links file.
    
    The new filename format is: "NNNN_CardName_SetName.html"
    Where:
    - NNNN: Line number (4 digits, zero-padded)
    - CardName: Card name from the URL (with hyphens preserved)
    - SetName: Set name from the URL
    
    Example: "0001_Aatchik-Emerald-Radian_Aetherdrift.html"
    
    Args:
        html_folder: Path to the folder containing card HTML files
        links_file: Path to the cards.txt file with card URLs
        
    Returns:
        Dictionary with counts: {'renamed': n, 'skipped': n, 'errors': n}
    """
    import re
    
    # Verify paths exist
    if not os.path.exists(html_folder):
        print(f"Error: Folder '{html_folder}' does not exist.")
        return {'renamed': 0, 'skipped': 0, 'errors': 0}
    
    if not os.path.exists(links_file):
        print(f"Error: Links file '{links_file}' does not exist.")
        return {'renamed': 0, 'skipped': 0, 'errors': 0}
    
    # Read the links file
    with open(links_file, 'r', encoding='utf-8') as f:
        links = [line.strip() for line in f if line.strip()]
    
    print(f"Found {len(links)} card links in {links_file}")
    
    # Build a mapping from URL patterns to line numbers
    # URL format: https://www.cardmarket.com/en/Magic/Products/Singles/{SetName}/{CardName}?...
    url_to_line = {}
    for i, url in enumerate(links, 1):
        # Extract the card path from the URL (after Singles/)
        match = re.search(r'/Singles/([^?]+)', url)
        if match:
            path = match.group(1)  # e.g., "Aetherdrift/Aatchik-Emerald-Radian"
            parts = path.split('/')
            if len(parts) >= 2:
                set_name = parts[0]
                card_name = parts[1]
                url_to_line[(set_name, card_name)] = i
    
    print(f"Mapped {len(url_to_line)} URL patterns to line numbers")
    
    # Get all HTML files from the folder
    html_files = [f for f in os.listdir(html_folder) if f.endswith('.html')]
    
    if not html_files:
        print(f"No HTML files found in '{html_folder}'")
        return {'renamed': 0, 'skipped': 0, 'errors': 0}
    
    print(f"Processing {len(html_files)} HTML files...")
    
    renamed_count = 0
    skipped_count = 0
    error_count = 0
    progress_interval = max(100, len(html_files) // 10)
    
    for i, file in enumerate(html_files, 1):
        # Progress reporting
        if i % progress_interval == 0:
            percent = (i / len(html_files)) * 100
            print(f"  Progress: {i}/{len(html_files)} ({percent:.1f}%) - {renamed_count} renamed, {skipped_count} skipped")
        
        file_path = os.path.join(html_folder, file)
        
        try:
            # Extract set name and card name from HTML content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # Try to find the canonical URL or og:url meta tag
            card_name = None
            set_name = None
            
            # Method 1: Look for og:url meta tag
            og_url = soup.find('meta', property='og:url')
            if og_url and og_url.get('content'):
                url = og_url['content']
                match = re.search(r'/Singles/([^/]+)/([^/?]+)', url)
                if match:
                    set_name = match.group(1)
                    card_name = match.group(2)
            
            # Method 2: Look for canonical link
            if not card_name or not set_name:
                canonical = soup.find('link', rel='canonical')
                if canonical and canonical.get('href'):
                    url = canonical['href']
                    match = re.search(r'/Singles/([^/]+)/([^/?]+)', url)
                    if match:
                        set_name = match.group(1)
                        card_name = match.group(2)
            
            # Method 3: Extract from title tag
            if not card_name or not set_name:
                title_tag = soup.find('title')
                if title_tag:
                    title_text = title_tag.get_text()
                    # Title format: "Card Name (SET) - MTG Singles | Cardmarket"
                    # or "Card Name (V.1) (SET) - MTG Singles | Cardmarket"
                    # We need to extract from the URL in page instead
                    pass
            
            # Method 4: Try to extract from existing filename if it already has format
            if not card_name or not set_name:
                # Check if file already has new format: NNNN_CardName_SetName.html
                match = re.match(r'^\d{4}_(.+)_(.+)\.html$', file)
                if match:
                    card_name = match.group(1)
                    set_name = match.group(2)
            
            if not card_name or not set_name:
                print(f"  Could not extract card/set info from: {file}")
                skipped_count += 1
                continue
            
            # Look up the line number
            line_num = url_to_line.get((set_name, card_name))
            
            if not line_num:
                # Try without URL encoding issues
                for (s, c), num in url_to_line.items():
                    if s == set_name and c == card_name:
                        line_num = num
                        break
            
            if not line_num:
                print(f"  No matching URL found for: {set_name}/{card_name}")
                skipped_count += 1
                continue
            
            # Generate new filename
            new_filename = f"{line_num:04d}_{card_name}_{set_name}.html"
            new_file_path = os.path.join(html_folder, new_filename)
            
            # Skip if already named correctly
            if file == new_filename:
                skipped_count += 1
                continue
            
            # Handle case where target file already exists
            if os.path.exists(new_file_path) and file != new_filename:
                print(f"  Target file already exists: {new_filename}")
                skipped_count += 1
                continue
            
            # Rename the file
            os.rename(file_path, new_file_path)
            renamed_count += 1
            
        except Exception as e:
            print(f"  Error processing {file}: {e}")
            error_count += 1
    
    print(f"\nRenaming complete:")
    print(f"  Renamed: {renamed_count}")
    print(f"  Skipped: {skipped_count}")
    print(f"  Errors: {error_count}")
    
    return {'renamed': renamed_count, 'skipped': skipped_count, 'errors': error_count}


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    # Get the current script directory path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Data folder is at ../data relative to main/
    data_dir = os.path.join(os.path.dirname(current_dir), 'data')
    
    # =========================================================================
    # BLOCK 1: SET URLs
    # =========================================================================
    # Generate CardMarket URLs for all Standard sets (10 pages each)
    # Output: data/links/set_urls.txt
    # -------------------------------------------------------------------------
    # set_urls_file = os.path.join(data_dir, "links", "set_urls.txt")
    # urls = generate_set_urls(set_urls_file)
    # if urls:
    #     print("\nFirst 5 set URLs:")
    #     for url in urls[:5]:
    #         print(f"  {url}")
    
    # =========================================================================
    # BLOCK 2: CARD LINKS
    # =========================================================================
    # Extract card links from downloaded set HTML pages
    # Input: data/html/sets/*.html
    # Output: data/links/cards.txt
    # -------------------------------------------------------------------------
    # sets_folder = os.path.join(data_dir, "html", "sets")
    # cards_links_file = os.path.join(data_dir, "links", "cards.txt")
    # cards = extract_card_links(sets_folder, cards_links_file)
    # if cards:
    #     print("\nFirst 15 card links:")
    #     for card in cards[:15]:
    #         print(f"  {card}")
    
    # =========================================================================
    # BLOCK 3: SELLER LINKS
    # =========================================================================
    # Extract unique seller links from card HTML pages
    # Input: data/html/cards/*.html
    # Output: data/links/sellers.txt
    # -------------------------------------------------------------------------
    # cards_folder = os.path.join(data_dir, "html", "cards")
    # sellers_file = os.path.join(data_dir, "links", "sellers.txt")
    # sellers = extract_seller_links(cards_folder, sellers_file)
    # if sellers:
    #     print("\nFirst 15 sellers:")
    #     for seller in sellers[:15]:
    #         print(f"  {seller}")
    
    # =========================================================================
    # BLOCK 4: CARD DATA EXTRACTION
    # =========================================================================
    # Extract card data from HTML files (Carta table)
    # Input: data/html/cards/*.html
    # Output: data/csv/cards.csv
    # -------------------------------------------------------------------------
    # cards_html_folder = os.path.join(data_dir, "html", "cards")
    # cards_csv_file = os.path.join(data_dir, "csv", "cards.csv")
    # cards_data = extract_card_data(cards_html_folder, cards_csv_file)
    # if cards_data:
    #     print("\nFirst 5 cards extracted:")
    #     for card in cards_data[:5]:
    #         print(f"  {card['name']} - {card['set']} - {card['rarity']}")
    
    # =========================================================================
    # BLOCK 5: SELLER-CARD DATA EXTRACTION
    # =========================================================================
    # Extract seller-card relationships (VendedorCarta table)
    # Input: data/html/cards/*.html
    # Output: data/csv/seller_cards.csv
    # -------------------------------------------------------------------------
    # cards_html_folder = os.path.join(data_dir, "html", "cards")
    # seller_cards_csv_file = os.path.join(data_dir, "csv", "seller_cards.csv")
    # seller_cards = extract_seller_card_data(cards_html_folder, seller_cards_csv_file)
    # if seller_cards:
    #     print("\nFirst 10 seller-card relationships extracted:")
    #     for record in seller_cards[:10]:
    #         print(f"  {record['seller_name']} -> {record['card_name']} | "
    #               f"Qty: {record['quantity']} | Price: {record['price']} | "
    #               f"Condition: {record['condition']} | Lang: {record['language']}")
    
    # =========================================================================
    # BLOCK 6: SELLER DATA EXTRACTION
    # =========================================================================
    # Extract seller profile data (Vendedor table)
    # Input: data/html/sellers/*.html
    # Output: data/csv/sellers.csv
    # -------------------------------------------------------------------------
    # sellers_html_folder = os.path.join(data_dir, "html", "sellers")
    # sellers_csv_file = os.path.join(data_dir, "csv", "sellers.csv")
    # sellers_data = extract_seller_data(sellers_html_folder, sellers_csv_file)
    # if sellers_data:
    #     print("\nFirst 10 sellers extracted:")
    #     for seller in sellers_data[:10]:
    #         print(f"  {seller['name']} | {seller['country']} | {seller['seller_type']} | "
    #               f"Sales: {seller['sales_count']} | Rating: {seller['rating']}")
    
    # pass


