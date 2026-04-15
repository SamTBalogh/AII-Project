# encoding:utf-8
import os
from main.models import Deck, DeckRating, User
from collections import Counter
import shelve
from django.db.models import Count
from math import sqrt

def sim_pearson(prefs, p1, p2):
    """
    Calculate Pearson correlation coefficient between two users.
    """
    si = {}
    for item in prefs[p1]: 
        if item in prefs[p2]: si[item] = 1

    if len(si) == 0: return 0
    n = len(si)

    sum1 = sum([prefs[p1][it] for it in si])
    sum2 = sum([prefs[p2][it] for it in si])

    sum1Sq = sum([pow(prefs[p1][it], 2) for it in si])
    sum2Sq = sum([pow(prefs[p2][it], 2) for it in si])	

    pSum = sum([prefs[p1][it] * prefs[p2][it] for it in si])

    num = pSum - (sum1 * sum2 / n)
    den = sqrt((sum1Sq - pow(sum1, 2) / n) * (sum2Sq - pow(sum2, 2) / n))
    if den == 0: return 0

    r = num / den

    return r

def topMatches(prefs, person, n=5, similarity=sim_pearson):
    """
    Get the top n most similar users to a given user.
    """
    scores = [(similarity(prefs, person, other), other)
              for other in prefs if other != person]
    scores.sort()
    scores.reverse()
    return scores[0:n]

def getRecommendations(prefs, person, similarity=sim_pearson):
    """
    Get deck recommendations for a user using collaborative filtering.
    Returns a list of (score, deck_id) tuples sorted by score descending.
    """
    totals = {}
    simSums = {}
    
    for other in prefs:
        if other == person: continue
        sim = similarity(prefs, person, other)
        
        if sim <= 0: continue
        
        for item in prefs[other]:
            if item not in prefs[person] or prefs[person][item] == 0:
                totals.setdefault(item, 0)
                totals[item] += prefs[other][item] * sim
                simSums.setdefault(item, 0)
                simSums[item] += sim
                
    rankings = [(totals[item] / simSums[item], item) for item in totals]
    rankings.sort()
    rankings.reverse()
    return rankings

def loadDict():
    """
    Load user-deck ratings from database into a preferences dictionary.
    Returns: {user_id: {deck_id: rating, ...}, ...}
    """
    prefs = {}
    ratings = DeckRating.objects.all()
    
    for r in ratings:
        user = int(r.user.id_user)  
        item = int(r.deck.id_deck)
        rating = float(r.rating)
        
        prefs.setdefault(user, {})
        prefs[user][item] = rating
        
    return prefs

def load_recsys_data():
    """
    Load recommendation system data from database and save to shelve file.
    """
    prefs = loadDict()
    
    # Use absolute path for shelve
    data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dataRS.dat')
    sh = shelve.open(data_path)
    sh['Prefs'] = prefs
    sh.close()
    
    print("Recommendation system data loaded successfully to dataRS.dat")
    return len(prefs)

def get_recommended_decks(user_id, n=10):
    """
    Get top n recommended decks for a specific user.
    
    Args:
        user_id: The user ID to get recommendations for
        n: Number of recommendations to return
        
    Returns:
        List of tuples: [(score, deck), ...]
    """
    # Load preferences from shelve
    data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dataRS.dat')
    
    try:
        sh = shelve.open(data_path)
        prefs = sh.get('Prefs', {})
        sh.close()
    except Exception as e:
        print(f"Error loading shelve data: {e}")
        # Fallback to loading from database
        prefs = loadDict()
    
    if user_id not in prefs:
        return []
    
    # Get recommendations
    recommendations = getRecommendations(prefs, user_id)
    
    # Convert deck IDs to Deck objects
    result = []
    for score, deck_id in recommendations[:n]:
        try:
            deck = Deck.objects.get(id_deck=deck_id)
            result.append((score, deck))
        except Deck.DoesNotExist:
            continue
    
    return result

def get_similar_users(user_id, n=5):
    """
    Get top n most similar users to a given user.
    
    Args:
        user_id: The user ID to find similar users for
        n: Number of similar users to return
        
    Returns:
        List of tuples: [(similarity_score, user), ...]
    """
    # Load preferences from shelve
    data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dataRS.dat')
    
    try:
        sh = shelve.open(data_path)
        prefs = sh.get('Prefs', {})
        sh.close()
    except Exception as e:
        print(f"Error loading shelve data: {e}")
        prefs = loadDict()
    
    if user_id not in prefs:
        return []
    
    # Get similar users
    matches = topMatches(prefs, user_id, n)
    
    # Convert user IDs to User objects
    result = []
    for score, uid in matches:
        try:
            user = User.objects.get(id_user=uid)
            result.append((score, user))
        except User.DoesNotExist:
            continue
    
    return result