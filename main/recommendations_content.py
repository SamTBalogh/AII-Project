# encoding:utf-8
"""
Content-Based Recommendation System for MTG Decks.

This module implements a content-based recommendation system that suggests
decks based on their characteristics (archetype, colors, cards in common).
"""

import os
import shelve
from math import sqrt
from collections import Counter
from main.models import Deck, DeckCard, Card, User, DeckRating


def get_deck_features(deck):
    """
    Extract features from a deck for content-based similarity.
    
    Features include:
    - archetype: The deck archetype (Aggro, Control, Combo, etc.)
    - color_identity: The color identity (Mono White, Jeskai, etc.)
    - colors_used: Individual colors (White, Blue, Black, Red, Green)
    - cards: Set of card names in the deck
    - meta_percentage: How popular the deck is in the meta
    
    Returns:
        dict: Dictionary with deck features
    """
    # Get all cards in the deck
    deck_cards = DeckCard.objects.filter(deck=deck).select_related('card')
    card_names = set(dc.card.name for dc in deck_cards)
    
    # Parse colors_used into individual colors
    colors = set()
    for color in ['White', 'Blue', 'Black', 'Red', 'Green']:
        if color in deck.colors_used:
            colors.add(color)
    
    return {
        'id_deck': deck.id_deck,
        'name': deck.name,
        'archetype': deck.archetype,
        'color_identity': deck.color_identity,
        'colors': colors,
        'cards': card_names,
        'meta_percentage': deck.meta_percentage,
    }


def calculate_deck_similarity(deck1_features, deck2_features):
    """
    Calculate similarity between two decks based on their features.
    
    Similarity is calculated as a weighted combination of:
    - Archetype match (20%)
    - Color identity match (15%)
    - Colors overlap (Jaccard, 15%)
    - Cards overlap (Jaccard, 50%)
    
    Args:
        deck1_features: Features dict for first deck
        deck2_features: Features dict for second deck
        
    Returns:
        float: Similarity score between 0 and 1
    """
    similarity = 0.0
    
    # Archetype match (20%)
    if deck1_features['archetype'] == deck2_features['archetype']:
        similarity += 0.20
    
    # Color identity match (15%)
    if deck1_features['color_identity'] == deck2_features['color_identity']:
        similarity += 0.15
    
    # Colors overlap - Jaccard similarity (15%)
    colors1 = deck1_features['colors']
    colors2 = deck2_features['colors']
    if colors1 or colors2:
        color_intersection = len(colors1 & colors2)
        color_union = len(colors1 | colors2)
        if color_union > 0:
            similarity += 0.15 * (color_intersection / color_union)
    
    # Cards overlap - Jaccard similarity (50%)
    cards1 = deck1_features['cards']
    cards2 = deck2_features['cards']
    if cards1 or cards2:
        cards_intersection = len(cards1 & cards2)
        cards_union = len(cards1 | cards2)
        if cards_union > 0:
            similarity += 0.50 * (cards_intersection / cards_union)
    
    return similarity


def build_deck_profiles():
    """
    Build feature profiles for all decks.
    
    Returns:
        dict: {deck_id: features_dict}
    """
    profiles = {}
    for deck in Deck.objects.all():
        profiles[deck.id_deck] = get_deck_features(deck)
    return profiles


def build_user_profile(user_id, deck_profiles):
    """
    Build a user profile based on their highly-rated decks.
    
    The user profile is a weighted combination of features from
    decks they have rated positively (rating >= 3.5).
    
    Args:
        user_id: The user's ID
        deck_profiles: Dictionary of deck profiles
        
    Returns:
        dict: User profile with aggregated features
    """
    ratings = DeckRating.objects.filter(user_id=user_id, rating__gte=3.5)
    
    if not ratings:
        return None
    
    # Aggregate features from positively rated decks
    archetype_weights = Counter()
    color_identity_weights = Counter()
    color_weights = Counter()
    card_weights = Counter()
    total_weight = 0
    
    for rating in ratings:
        deck_id = rating.deck_id
        if deck_id not in deck_profiles:
            continue
            
        profile = deck_profiles[deck_id]
        weight = rating.rating  # Use rating as weight
        total_weight += weight
        
        archetype_weights[profile['archetype']] += weight
        color_identity_weights[profile['color_identity']] += weight
        
        for color in profile['colors']:
            color_weights[color] += weight
            
        for card in profile['cards']:
            card_weights[card] += weight
    
    if total_weight == 0:
        return None
    
    # Normalize weights
    for key in archetype_weights:
        archetype_weights[key] /= total_weight
    for key in color_identity_weights:
        color_identity_weights[key] /= total_weight
    for key in color_weights:
        color_weights[key] /= total_weight
    for key in card_weights:
        card_weights[key] /= total_weight
    
    return {
        'archetype_weights': dict(archetype_weights),
        'color_identity_weights': dict(color_identity_weights),
        'color_weights': dict(color_weights),
        'card_weights': dict(card_weights),
        'rated_decks': set(r.deck_id for r in ratings),
    }


def calculate_user_deck_score(user_profile, deck_features):
    """
    Calculate how well a deck matches a user's profile.
    
    Args:
        user_profile: User profile with weighted preferences
        deck_features: Features of the deck to score
        
    Returns:
        float: Score indicating how well the deck matches user preferences
    """
    score = 0.0
    
    # Archetype score (25%)
    archetype = deck_features['archetype']
    if archetype in user_profile['archetype_weights']:
        score += 0.25 * user_profile['archetype_weights'][archetype]
    
    # Color identity score (15%)
    color_identity = deck_features['color_identity']
    if color_identity in user_profile['color_identity_weights']:
        score += 0.15 * user_profile['color_identity_weights'][color_identity]
    
    # Colors score (15%)
    color_score = 0
    for color in deck_features['colors']:
        if color in user_profile['color_weights']:
            color_score += user_profile['color_weights'][color]
    if deck_features['colors']:
        color_score /= len(deck_features['colors'])
    score += 0.15 * color_score
    
    # Cards score (45%)
    card_score = 0
    for card in deck_features['cards']:
        if card in user_profile['card_weights']:
            card_score += user_profile['card_weights'][card]
    if deck_features['cards']:
        card_score /= len(deck_features['cards'])
    score += 0.45 * card_score
    
    return score


def load_content_recsys_data():
    """
    Load content-based recommendation system data and save to shelve file.
    
    Builds deck profiles and stores them for quick access.
    """
    deck_profiles = build_deck_profiles()
    
    # Use absolute path for shelve
    data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dataRS_content.dat')
    sh = shelve.open(data_path)
    sh['DeckProfiles'] = deck_profiles
    sh.close()
    
    print(f"Content-based recommendation data loaded successfully. {len(deck_profiles)} deck profiles created.")
    return len(deck_profiles)


def get_content_recommended_decks(user_id, n=10):
    """
    Get top n recommended decks for a user using content-based filtering.
    
    Args:
        user_id: The user ID to get recommendations for
        n: Number of recommendations to return
        
    Returns:
        List of tuples: [(score, deck), ...]
    """
    # Load deck profiles from shelve
    data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dataRS_content.dat')
    
    try:
        sh = shelve.open(data_path)
        deck_profiles = sh.get('DeckProfiles', {})
        sh.close()
    except Exception as e:
        print(f"Error loading shelve data: {e}")
        deck_profiles = build_deck_profiles()
    
    if not deck_profiles:
        deck_profiles = build_deck_profiles()
    
    # Build user profile
    user_profile = build_user_profile(user_id, deck_profiles)
    
    if not user_profile:
        return []
    
    # Score all decks the user hasn't rated
    scored_decks = []
    for deck_id, features in deck_profiles.items():
        if deck_id in user_profile['rated_decks']:
            continue
        
        score = calculate_user_deck_score(user_profile, features)
        scored_decks.append((score, deck_id))
    
    # Sort by score descending
    scored_decks.sort(reverse=True)
    
    # Convert to Deck objects
    result = []
    for score, deck_id in scored_decks[:n]:
        try:
            deck = Deck.objects.get(id_deck=deck_id)
            result.append((score, deck))
        except Deck.DoesNotExist:
            continue
    
    return result


def get_similar_decks(deck_id, n=5):
    """
    Get decks similar to a given deck based on content similarity.
    
    Args:
        deck_id: The deck ID to find similar decks for
        n: Number of similar decks to return
        
    Returns:
        List of tuples: [(similarity_score, deck), ...]
    """
    # Load deck profiles from shelve
    data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dataRS_content.dat')
    
    try:
        sh = shelve.open(data_path)
        deck_profiles = sh.get('DeckProfiles', {})
        sh.close()
    except Exception as e:
        print(f"Error loading shelve data: {e}")
        deck_profiles = build_deck_profiles()
    
    if deck_id not in deck_profiles:
        return []
    
    target_features = deck_profiles[deck_id]
    
    # Calculate similarity with all other decks
    similarities = []
    for other_id, other_features in deck_profiles.items():
        if other_id == deck_id:
            continue
        
        sim = calculate_deck_similarity(target_features, other_features)
        similarities.append((sim, other_id))
    
    # Sort by similarity descending
    similarities.sort(reverse=True)
    
    # Convert to Deck objects
    result = []
    for sim, d_id in similarities[:n]:
        try:
            deck = Deck.objects.get(id_deck=d_id)
            result.append((sim, deck))
        except Deck.DoesNotExist:
            continue
    
    return result


def get_user_preferred_features(user_id):
    """
    Get the top features preferred by a user.
    
    Args:
        user_id: The user ID
        
    Returns:
        dict: Top archetypes, colors, and cards preferred by the user
    """
    # Load deck profiles from shelve
    data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dataRS_content.dat')
    
    try:
        sh = shelve.open(data_path)
        deck_profiles = sh.get('DeckProfiles', {})
        sh.close()
    except Exception:
        deck_profiles = build_deck_profiles()
    
    user_profile = build_user_profile(user_id, deck_profiles)
    
    if not user_profile:
        return None
    
    # Get top 3 archetypes
    top_archetypes = sorted(
        user_profile['archetype_weights'].items(),
        key=lambda x: x[1],
        reverse=True
    )[:3]
    
    # Get top 3 color identities
    top_color_identities = sorted(
        user_profile['color_identity_weights'].items(),
        key=lambda x: x[1],
        reverse=True
    )[:3]
    
    # Get top colors
    top_colors = sorted(
        user_profile['color_weights'].items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    # Get top 10 cards
    top_cards = sorted(
        user_profile['card_weights'].items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    return {
        'archetypes': top_archetypes,
        'color_identities': top_color_identities,
        'colors': top_colors,
        'cards': top_cards,
    }
