from django.test import TestCase
from django.core.exceptions import ValidationError
from main.models import Card, Seller, SellerCard, Deck, DeckCard, User, DeckRating
from main.populate import parse_price, parse_price_simple, parse_int, populate_database


class CardModelTest(TestCase):
    """Tests for the Card model."""

    def test_create_card(self):
        """Test that a card can be created with valid data."""
        card = Card.objects.create(
            name="Lightning Bolt",
            rarity="Rare",
            card_number="123",
            set="Alpha",
            image_url="https://example.com/image.jpg",
            available_items=100,
            price_from=1.50,
            price_trend=2.00,
            avg_30_days=1.80,
            avg_7_days=1.90,
            avg_1_day=1.95
        )
        self.assertEqual(card.name, "Lightning Bolt")
        self.assertEqual(card.set, "Alpha")
        self.assertEqual(card.available_items, 100)

    def test_card_str_representation(self):
        """Test the string representation of a card."""
        card = Card.objects.create(
            name="Black Lotus",
            set="Alpha",
            card_number="1",
            price_from=10000.00
        )
        self.assertEqual(str(card), "Black Lotus (Alpha #1)")

    def test_card_unique_together(self):
        """Test that card name, set and version must be unique together."""
        Card.objects.create(
            name="Sol Ring",
            version="V.1",
            set="Alpha",
            card_number="50",
            price_from=5.00
        )
        # Try to create a duplicate (same name, set and version)
        with self.assertRaises(Exception):
            Card.objects.create(
                name="Sol Ring",
                version="V.1",
                set="Alpha",
                card_number="51",  # Different card number, but same name/version/set
                price_from=6.00
            )

    def test_card_nullable_fields(self):
        """Test that nullable fields work correctly."""
        card = Card.objects.create(
            name="Mystery Card",
            set="Mystery Set"
        )
        self.assertIsNone(card.rarity)
        self.assertIsNone(card.card_number)
        self.assertIsNone(card.price_from)


class SellerModelTest(TestCase):
    """Tests for the Seller model."""

    def test_create_seller(self):
        """Test that a seller can be created with valid data."""
        seller = Seller.objects.create(
            name="CardStore",
            real_name="Card Store Inc.",
            country="Germany",
            seller_type="Professional",
            sales_count=5000,
            available_items=10000,
            rating="Outstanding",
            approval_very_good="99 %",
            approval_good="1 %",
            approval_neutral="0 %",
            approval_bad="0 %",
            shipping_days=5,
            street_address="Main Street 123",
            postal_code="12345",
            city="Berlin"
        )
        self.assertEqual(seller.name, "CardStore")
        self.assertEqual(seller.country, "Germany")
        self.assertEqual(seller.sales_count, 5000)

    def test_seller_str_representation(self):
        """Test the string representation of a seller."""
        seller = Seller.objects.create(
            name="SuperSeller",
            country="Spain",
            seller_type="Powerseller",
            rating="Very good"
        )
        self.assertEqual(str(seller), "SuperSeller")

    def test_seller_unique_name(self):
        """Test that seller names must be unique."""
        Seller.objects.create(
            name="UniqueSeller",
            country="France",
            seller_type="Professional",
            rating="Good"
        )
        with self.assertRaises(Exception):
            Seller.objects.create(
                name="UniqueSeller",
                country="Italy",
                seller_type="Powerseller",
                rating="Outstanding"
            )

    def test_seller_ordering(self):
        """Test that sellers are ordered by sales_count descending."""
        Seller.objects.create(name="LowSales", country="UK", seller_type="Pro", rating="Good", sales_count=100)
        Seller.objects.create(name="HighSales", country="UK", seller_type="Pro", rating="Good", sales_count=10000)
        Seller.objects.create(name="MidSales", country="UK", seller_type="Pro", rating="Good", sales_count=1000)

        sellers = list(Seller.objects.all())
        self.assertEqual(sellers[0].name, "HighSales")
        self.assertEqual(sellers[1].name, "MidSales")
        self.assertEqual(sellers[2].name, "LowSales")


class SellerCardModelTest(TestCase):
    """Tests for the SellerCard intermediate model."""

    def setUp(self):
        """Set up test data."""
        self.card = Card.objects.create(
            name="Test Card",
            set="Test Set",
            price_from=1.00
        )
        self.seller = Seller.objects.create(
            name="Test Seller",
            country="Germany",
            seller_type="Professional",
            rating="Outstanding"
        )

    def test_create_seller_card(self):
        """Test that a seller-card relationship can be created."""
        seller_card = SellerCard.objects.create(
            seller=self.seller,
            card=self.card,
            quantity=5,
            price=2.50,
            condition="Near Mint",
            language="English"
        )
        self.assertEqual(seller_card.quantity, 5)
        self.assertEqual(seller_card.price, 2.50)
        self.assertEqual(seller_card.condition, "Near Mint")

    def test_seller_card_str_representation(self):
        """Test the string representation of a seller-card relationship."""
        seller_card = SellerCard.objects.create(
            seller=self.seller,
            card=self.card,
            quantity=1,
            price=1.00,
            condition="Good",
            language="Spanish"
        )
        self.assertEqual(str(seller_card), "Test Seller - Test Card")

    def test_seller_card_cascade_delete_seller(self):
        """Test that deleting a seller cascades to seller-cards."""
        SellerCard.objects.create(
            seller=self.seller,
            card=self.card,
            quantity=1,
            price=1.00,
            condition="Good",
            language="English"
        )
        self.assertEqual(SellerCard.objects.count(), 1)
        self.seller.delete()
        self.assertEqual(SellerCard.objects.count(), 0)

    def test_seller_card_cascade_delete_card(self):
        """Test that deleting a card cascades to seller-cards."""
        SellerCard.objects.create(
            seller=self.seller,
            card=self.card,
            quantity=1,
            price=1.00,
            condition="Good",
            language="English"
        )
        self.assertEqual(SellerCard.objects.count(), 1)
        self.card.delete()
        self.assertEqual(SellerCard.objects.count(), 0)


class DeckModelTest(TestCase):
    """Tests for the Deck model."""

    def test_create_deck(self):
        """Test that a deck can be created with valid data."""
        deck = Deck.objects.create(
            name="Mono Red Aggro",
            alternative_name="RDW",
            archetype="Aggro",
            color_identity="Mono Red",
            colors_used="R",
            meta_percentage=15.5
        )
        self.assertEqual(deck.name, "Mono Red Aggro")
        self.assertEqual(deck.archetype, "Aggro")
        self.assertEqual(deck.meta_percentage, 15.5)

    def test_deck_str_representation(self):
        """Test the string representation of a deck."""
        deck = Deck.objects.create(
            name="Control Deck",
            archetype="Control",
            color_identity="Azorius",
            colors_used="WU",
            meta_percentage=10.0
        )
        self.assertEqual(str(deck), "Control Deck")

    def test_deck_ordering(self):
        """Test that decks are ordered by meta_percentage descending."""
        Deck.objects.create(name="Deck A", archetype="Aggro", color_identity="Mono", colors_used="R", meta_percentage=5.0)
        Deck.objects.create(name="Deck B", archetype="Control", color_identity="Mono", colors_used="U", meta_percentage=20.0)
        Deck.objects.create(name="Deck C", archetype="Midrange", color_identity="Mono", colors_used="G", meta_percentage=10.0)

        decks = list(Deck.objects.all())
        self.assertEqual(decks[0].name, "Deck B")
        self.assertEqual(decks[1].name, "Deck C")
        self.assertEqual(decks[2].name, "Deck A")


class DeckCardModelTest(TestCase):
    """Tests for the DeckCard intermediate model."""

    def setUp(self):
        """Set up test data."""
        self.card = Card.objects.create(
            name="Lightning Bolt",
            set="Alpha",
            price_from=2.00
        )
        self.deck = Deck.objects.create(
            name="Burn Deck",
            archetype="Aggro",
            color_identity="Mono Red",
            colors_used="R",
            meta_percentage=12.0
        )

    def test_create_deck_card(self):
        """Test that a deck-card relationship can be created."""
        deck_card = DeckCard.objects.create(
            deck=self.deck,
            card=self.card,
            quantity=4,
            role="core"
        )
        self.assertEqual(deck_card.quantity, 4)
        self.assertEqual(deck_card.role, "core")

    def test_deck_card_str_representation(self):
        """Test the string representation of a deck-card relationship."""
        deck_card = DeckCard.objects.create(
            deck=self.deck,
            card=self.card,
            quantity=4,
            role="core"
        )
        self.assertEqual(str(deck_card), "4")


class ParsePriceTest(TestCase):
    """Tests for the parse_price function."""

    def test_parse_euro_price(self):
        """Test parsing euro prices."""
        price, currency = parse_price("0,05 €")
        self.assertEqual(price, 0.05)
        self.assertEqual(currency, "EUR")
        
        price, currency = parse_price("1,50 €")
        self.assertEqual(price, 1.50)
        self.assertEqual(currency, "EUR")

    def test_parse_pound_price(self):
        """Test parsing pound prices."""
        price, currency = parse_price("£0.02")
        self.assertEqual(price, 0.02)
        self.assertEqual(currency, "GBP")
        
        price, currency = parse_price("£10.50")
        self.assertEqual(price, 10.50)
        self.assertEqual(currency, "GBP")

    def test_parse_dollar_price(self):
        """Test parsing dollar prices."""
        price, currency = parse_price("$5.99")
        self.assertEqual(price, 5.99)
        self.assertEqual(currency, "USD")

    def test_parse_empty_price(self):
        """Test parsing empty or None prices."""
        price, currency = parse_price("")
        self.assertIsNone(price)
        
        price, currency = parse_price(None)
        self.assertIsNone(price)

    def test_parse_invalid_price(self):
        """Test parsing invalid prices."""
        price, currency = parse_price("invalid")
        self.assertIsNone(price)
        
        price, currency = parse_price("N/A")
        self.assertIsNone(price)

    def test_parse_price_simple(self):
        """Test parse_price_simple returns only the price."""
        self.assertEqual(parse_price_simple("0,05 €"), 0.05)
        self.assertEqual(parse_price_simple("$5.99"), 5.99)
        self.assertIsNone(parse_price_simple(""))


class SellerCardCurrencyTest(TestCase):
    """Tests for the SellerCard currency field."""

    def setUp(self):
        """Set up test data."""
        self.card = Card.objects.create(
            name="Test Card",
            set="Test Set",
            price_from=1.00
        )
        self.seller = Seller.objects.create(
            name="Test Seller",
            country="Germany",
            seller_type="Professional",
            rating="Outstanding"
        )

    def test_seller_card_default_currency(self):
        """Test that SellerCard defaults to EUR currency."""
        seller_card = SellerCard.objects.create(
            seller=self.seller,
            card=self.card,
            quantity=1,
            price=1.00,
            condition="Near Mint",
            language="English"
        )
        self.assertEqual(seller_card.currency, "EUR")

    def test_seller_card_usd_currency(self):
        """Test that SellerCard can store USD currency."""
        seller_card = SellerCard.objects.create(
            seller=self.seller,
            card=self.card,
            quantity=1,
            price=5.99,
            currency="USD",
            condition="Near Mint",
            language="English"
        )
        self.assertEqual(seller_card.currency, "USD")

    def test_seller_card_gbp_currency(self):
        """Test that SellerCard can store GBP currency."""
        seller_card = SellerCard.objects.create(
            seller=self.seller,
            card=self.card,
            quantity=1,
            price=4.50,
            currency="GBP",
            condition="Near Mint",
            language="English"
        )
        self.assertEqual(seller_card.currency, "GBP")


class ParseIntTest(TestCase):
    """Tests for the parse_int function."""

    def test_parse_simple_int(self):
        """Test parsing simple integers."""
        self.assertEqual(parse_int("100"), 100)
        self.assertEqual(parse_int("0"), 0)
        self.assertEqual(parse_int("999999"), 999999)

    def test_parse_empty_int(self):
        """Test parsing empty values."""
        self.assertEqual(parse_int(""), 0)
        self.assertEqual(parse_int(None), 0)

    def test_parse_formatted_int(self):
        """Test parsing integers with formatting."""
        self.assertEqual(parse_int("1,000"), 1000)
        self.assertEqual(parse_int("10.000"), 10000)


class PopulateDatabaseTest(TestCase):
    """Tests for the populate_database function."""

    def test_delete_tables_clears_all_data(self):
        """Test that delete_tables removes all records."""
        # Create some test data
        card = Card.objects.create(name="Test Card", set="Test", price_from=1.0)
        seller = Seller.objects.create(name="Test Seller", country="DE", seller_type="Pro", rating="Good")
        SellerCard.objects.create(seller=seller, card=card, quantity=1, price=1.0, condition="NM", language="EN")

        # Verify data exists
        self.assertEqual(Card.objects.count(), 1)
        self.assertEqual(Seller.objects.count(), 1)
        self.assertEqual(SellerCard.objects.count(), 1)

        # Delete all tables
        from main.populate import delete_tables
        delete_tables()

        # Verify all data is deleted
        self.assertEqual(Card.objects.count(), 0)
        self.assertEqual(Seller.objects.count(), 0)
        self.assertEqual(SellerCard.objects.count(), 0)


class CardSellerRelationshipTest(TestCase):
    """Tests for the relationship between cards and sellers."""

    def test_seller_can_have_multiple_cards(self):
        """Test that a seller can have multiple cards."""
        seller = Seller.objects.create(name="BigSeller", country="DE", seller_type="Pro", rating="Good")
        card1 = Card.objects.create(name="Card 1", set="Set A", price_from=1.0)
        card2 = Card.objects.create(name="Card 2", set="Set A", price_from=2.0)

        SellerCard.objects.create(seller=seller, card=card1, quantity=5, price=1.5, condition="NM", language="EN")
        SellerCard.objects.create(seller=seller, card=card2, quantity=3, price=2.5, condition="NM", language="EN")

        self.assertEqual(seller.cards.count(), 2)

    def test_card_can_have_multiple_sellers(self):
        """Test that a card can be sold by multiple sellers."""
        card = Card.objects.create(name="Popular Card", set="Set A", price_from=5.0)
        seller1 = Seller.objects.create(name="Seller 1", country="DE", seller_type="Pro", rating="Good")
        seller2 = Seller.objects.create(name="Seller 2", country="FR", seller_type="Pro", rating="Good")

        SellerCard.objects.create(seller=seller1, card=card, quantity=10, price=5.0, condition="NM", language="EN")
        SellerCard.objects.create(seller=seller2, card=card, quantity=8, price=5.5, condition="NM", language="FR")

        self.assertEqual(card.sellers.count(), 2)

    def test_seller_card_different_conditions(self):
        """Test that a seller can have the same card in different conditions."""
        seller = Seller.objects.create(name="ConditionSeller", country="DE", seller_type="Pro", rating="Good")
        card = Card.objects.create(name="Condition Card", set="Set A", price_from=2.0)

        SellerCard.objects.create(seller=seller, card=card, quantity=5, price=2.0, condition="Near Mint", language="EN")
        SellerCard.objects.create(seller=seller, card=card, quantity=3, price=1.5, condition="Light Played", language="EN")
        SellerCard.objects.create(seller=seller, card=card, quantity=2, price=1.0, condition="Played", language="EN")

        seller_cards = SellerCard.objects.filter(seller=seller, card=card)
        self.assertEqual(seller_cards.count(), 3)


class UserModelTest(TestCase):
    """Tests for the User model."""

    def test_create_user(self):
        """Test that a user can be created."""
        user = User.objects.create(
            username="testuser",
            preferred_archetype="Aggro",
            preferred_colors="Red White"
        )
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.preferred_archetype, "Aggro")

    def test_user_str_representation(self):
        """Test the string representation of a user."""
        user = User.objects.create(username="player1")
        self.assertEqual(str(user), "player1")

    def test_user_unique_username(self):
        """Test that usernames must be unique."""
        User.objects.create(username="unique_user")
        with self.assertRaises(Exception):
            User.objects.create(username="unique_user")


class DeckRatingModelTest(TestCase):
    """Tests for the DeckRating model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create(username="testuser")
        self.deck = Deck.objects.create(
            name="Test Deck",
            archetype="Aggro",
            color_identity="Mono Red",
            colors_used="R",
            meta_percentage=10.0
        )

    def test_create_deck_rating(self):
        """Test that a deck rating can be created."""
        rating = DeckRating.objects.create(
            user=self.user,
            deck=self.deck,
            rating=4.5
        )
        self.assertEqual(rating.rating, 4.5)
        self.assertEqual(rating.user, self.user)
        self.assertEqual(rating.deck, self.deck)

    def test_deck_rating_str_representation(self):
        """Test the string representation of a deck rating."""
        rating = DeckRating.objects.create(
            user=self.user,
            deck=self.deck,
            rating=3.5
        )
        self.assertEqual(str(rating), "testuser -> Test Deck: 3.5")

    def test_deck_rating_unique_together(self):
        """Test that a user can only rate a deck once."""
        DeckRating.objects.create(user=self.user, deck=self.deck, rating=4.0)
        with self.assertRaises(Exception):
            DeckRating.objects.create(user=self.user, deck=self.deck, rating=5.0)

    def test_deck_rating_cascade_delete(self):
        """Test that deleting a user or deck cascades to ratings."""
        DeckRating.objects.create(user=self.user, deck=self.deck, rating=4.0)
        self.assertEqual(DeckRating.objects.count(), 1)
        self.user.delete()
        self.assertEqual(DeckRating.objects.count(), 0)


class CardFilterFormTest(TestCase):
    """Tests for the CardFilterForm."""

    def setUp(self):
        """Set up test data."""
        Card.objects.create(name="Lightning Bolt", set="Alpha", rarity="Rare", price_trend=2.0)
        Card.objects.create(name="Black Lotus", set="Alpha", rarity="Mythic", price_trend=5000.0)
        Card.objects.create(name="Forest", set="Beta", rarity="Common", price_trend=0.10)

    def test_form_initialization(self):
        """Test that the form initializes with choices."""
        from main.forms import CardFilterForm
        form = CardFilterForm()
        self.assertIn('name', form.fields)
        self.assertIn('set', form.fields)
        self.assertTrue(len(form.fields['set'].choices) > 0)

    def test_form_filter_by_name(self):
        """Test filtering cards by name."""
        from main.forms import CardFilterForm
        form = CardFilterForm(data={'name': 'Lightning'})
        self.assertTrue(form.is_valid())
        cards = form.get_filtered_cards()
        self.assertEqual(cards.count(), 1)
        self.assertEqual(cards.first().name, "Lightning Bolt")

    def test_form_filter_by_set(self):
        """Test filtering cards by set."""
        from main.forms import CardFilterForm
        form = CardFilterForm(data={'set': 'Alpha'})
        self.assertTrue(form.is_valid())
        cards = form.get_filtered_cards()
        self.assertEqual(cards.count(), 2)

    def test_form_filter_by_price_range(self):
        """Test filtering cards by price range."""
        from main.forms import CardFilterForm
        form = CardFilterForm(data={'price_min': 1.0, 'price_max': 10.0})
        self.assertTrue(form.is_valid())
        cards = form.get_filtered_cards()
        self.assertEqual(cards.count(), 1)

    def test_form_filter_by_rarity(self):
        """Test filtering cards by rarity."""
        from main.forms import CardFilterForm
        form = CardFilterForm(data={'rarity': 'Common'})
        self.assertTrue(form.is_valid())
        cards = form.get_filtered_cards()
        self.assertEqual(cards.count(), 1)


class UserIdFormTest(TestCase):
    """Tests for the UserIdForm."""

    def test_valid_user_id(self):
        """Test that valid user IDs are accepted."""
        from main.forms import UserIdForm
        form = UserIdForm(data={'user_id': 5})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['user_id'], 5)

    def test_invalid_user_id_negative(self):
        """Test that negative user IDs are rejected."""
        from main.forms import UserIdForm
        form = UserIdForm(data={'user_id': -1})
        self.assertFalse(form.is_valid())

    def test_invalid_user_id_zero(self):
        """Test that zero user ID is rejected."""
        from main.forms import UserIdForm
        form = UserIdForm(data={'user_id': 0})
        self.assertFalse(form.is_valid())


class GenerateRatingsFormTest(TestCase):
    """Tests for the GenerateRatingsForm."""

    def test_valid_num_users(self):
        """Test that valid number of users is accepted."""
        from main.forms import GenerateRatingsForm
        form = GenerateRatingsForm(data={'num_users': 100})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['num_users'], 100)

    def test_default_num_users(self):
        """Test that the default value is 50."""
        from main.forms import GenerateRatingsForm
        form = GenerateRatingsForm()
        self.assertEqual(form.fields['num_users'].initial, 50)

    def test_invalid_num_users_too_large(self):
        """Test that values over 10000 are rejected."""
        from main.forms import GenerateRatingsForm
        form = GenerateRatingsForm(data={'num_users': 15000})
        self.assertFalse(form.is_valid())

    def test_invalid_num_users_zero(self):
        """Test that zero is rejected."""
        from main.forms import GenerateRatingsForm
        form = GenerateRatingsForm(data={'num_users': 0})
        self.assertFalse(form.is_valid())


class RecommendationSystemTest(TestCase):
    """Tests for the recommendation system functions."""

    def setUp(self):
        """Set up test data."""
        # Create users
        self.user1 = User.objects.create(username="user1", preferred_archetype="Aggro")
        self.user2 = User.objects.create(username="user2", preferred_archetype="Aggro")
        self.user3 = User.objects.create(username="user3", preferred_archetype="Control")
        
        # Create decks
        self.deck1 = Deck.objects.create(
            name="Red Aggro", archetype="Aggro", 
            color_identity="Mono Red", colors_used="R", meta_percentage=15.0
        )
        self.deck2 = Deck.objects.create(
            name="Blue Control", archetype="Control",
            color_identity="Mono Blue", colors_used="U", meta_percentage=10.0
        )
        self.deck3 = Deck.objects.create(
            name="White Aggro", archetype="Aggro",
            color_identity="Mono White", colors_used="W", meta_percentage=12.0
        )
        
        # Create ratings
        DeckRating.objects.create(user=self.user1, deck=self.deck1, rating=5.0)
        DeckRating.objects.create(user=self.user1, deck=self.deck2, rating=2.0)
        DeckRating.objects.create(user=self.user1, deck=self.deck3, rating=4.5)
        
        DeckRating.objects.create(user=self.user2, deck=self.deck1, rating=4.8)
        DeckRating.objects.create(user=self.user2, deck=self.deck2, rating=2.5)
        
        DeckRating.objects.create(user=self.user3, deck=self.deck1, rating=2.0)
        DeckRating.objects.create(user=self.user3, deck=self.deck2, rating=5.0)

    def test_load_dict(self):
        """Test that loadDict loads ratings correctly."""
        from main.recommendations import loadDict
        prefs = loadDict()
        self.assertIn(self.user1.id_user, prefs)
        self.assertIn(self.deck1.id_deck, prefs[self.user1.id_user])
        self.assertEqual(prefs[self.user1.id_user][self.deck1.id_deck], 5.0)

    def test_sim_pearson(self):
        """Test Pearson correlation calculation."""
        from main.recommendations import sim_pearson, loadDict
        prefs = loadDict()
        # Users 1 and 2 have similar tastes (both like aggro)
        sim = sim_pearson(prefs, self.user1.id_user, self.user2.id_user)
        self.assertIsInstance(sim, (int, float))
        self.assertGreaterEqual(sim, -1.0)
        self.assertLessEqual(sim, 1.0)

    def test_top_matches(self):
        """Test finding top similar users."""
        from main.recommendations import topMatches, loadDict
        prefs = loadDict()
        matches = topMatches(prefs, self.user1.id_user, n=2)
        self.assertIsInstance(matches, list)
        self.assertLessEqual(len(matches), 2)

    def test_get_recommendations(self):
        """Test getting deck recommendations."""
        from main.recommendations import getRecommendations, loadDict
        prefs = loadDict()
        recs = getRecommendations(prefs, self.user2.id_user)
        self.assertIsInstance(recs, list)
        # User2 hasn't rated deck3, so it should be recommended
        deck_ids = [deck_id for score, deck_id in recs]
        self.assertIn(self.deck3.id_deck, deck_ids)

    def test_load_recsys_data(self):
        """Test loading data to shelve file."""
        from main.recommendations import load_recsys_data
        num_users = load_recsys_data()
        self.assertEqual(num_users, 3)

    def test_get_recommended_decks(self):
        """Test getting recommended decks with Deck objects."""
        from main.recommendations import load_recsys_data, get_recommended_decks
        load_recsys_data()
        recs = get_recommended_decks(self.user2.id_user, n=5)
        self.assertIsInstance(recs, list)
        if len(recs) > 0:
            score, deck = recs[0]
            self.assertIsInstance(deck, Deck)

    def test_get_similar_users(self):
        """Test getting similar users with User objects."""
        from main.recommendations import load_recsys_data, get_similar_users
        load_recsys_data()
        similar = get_similar_users(self.user1.id_user, n=2)
        self.assertIsInstance(similar, list)
        if len(similar) > 0:
            score, user = similar[0]
            self.assertIsInstance(user, User)


class ViewsTest(TestCase):
    """Tests for views."""

    def setUp(self):
        """Set up test data."""
        self.card = Card.objects.create(
            name="Test Card", set="Test Set",
            rarity="Rare", price_from=1.0
        )
        self.seller = Seller.objects.create(
            name="Test Seller", country="Germany",
            seller_type="Professional", rating="Outstanding"
        )

    def test_index_view(self):
        """Test the index view."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'index.html')

    def test_cards_view(self):
        """Test the cards list view."""
        response = self.client.get('/cards/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cards.html')
        self.assertIn('cards', response.context)

    def test_card_detail_view(self):
        """Test the card detail view."""
        response = self.client.get(f'/cards/{self.card.id_card}/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'card_detail.html')
        self.assertEqual(response.context['card'], self.card)

    def test_sellers_view(self):
        """Test the sellers list view."""
        response = self.client.get('/sellers/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sellers.html')
        self.assertIn('sellers', response.context)

    def test_seller_detail_view(self):
        """Test the seller detail view."""
        response = self.client.get(f'/sellers/{self.seller.id_seller}/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'seller_detail.html')
        self.assertEqual(response.context['seller'], self.seller)

    def test_card_detail_not_found(self):
        """Test card detail view with invalid ID."""
        response = self.client.get('/cards/99999/')
        self.assertEqual(response.status_code, 404)

    def test_seller_detail_not_found(self):
        """Test seller detail view with invalid ID."""
        response = self.client.get('/sellers/99999/')
        self.assertEqual(response.status_code, 404)


class ShippingCostCalculationTest(TestCase):
    """Tests for shipping cost calculation."""

    def test_shipping_cost_lightweight(self):
        """Test shipping cost for lightweight packages (0-20g)."""
        from main.views import calculate_shipping_cost
        cost = calculate_shipping_cost("Germany", 5)  # 5 cards = 9g + 5g packaging = 14g
        self.assertEqual(cost, 1.60)

    def test_shipping_cost_medium(self):
        """Test shipping cost for medium packages (20-50g)."""
        from main.views import calculate_shipping_cost
        cost = calculate_shipping_cost("Germany", 15)  # 15 cards = 27g + 5g = 32g
        self.assertEqual(cost, 2.40)

    def test_shipping_cost_heavy(self):
        """Test shipping cost for heavy packages."""
        from main.views import calculate_shipping_cost
        cost = calculate_shipping_cost("Germany", 100)  # 100 cards = 180g + 5g = 185g
        self.assertEqual(cost, 5.00)


class CardVersionTest(TestCase):
    """Tests for card versioning."""

    def test_card_with_version(self):
        """Test card with version in string representation."""
        card = Card.objects.create(
            name="Test Card", version="V.1",
            set="Test Set", card_number="001"
        )
        self.assertIn("V.1", str(card))

    def test_card_without_version(self):
        """Test card without version in string representation."""
        card = Card.objects.create(
            name="Test Card", set="Test Set", card_number="001"
        )
        self.assertNotIn("V.1", str(card))


class DeckCardRelationshipTest(TestCase):
    """Tests for deck-card relationships."""

    def setUp(self):
        """Set up test data."""
        self.deck = Deck.objects.create(
            name="Test Deck", archetype="Aggro",
            color_identity="Mono Red", colors_used="R", meta_percentage=10.0
        )
        self.card1 = Card.objects.create(name="Card 1", set="Set A")
        self.card2 = Card.objects.create(name="Card 2", set="Set A")

    def test_deck_can_have_multiple_cards(self):
        """Test that a deck can have multiple cards."""
        DeckCard.objects.create(deck=self.deck, card=self.card1, quantity=4, role="Main Deck")
        DeckCard.objects.create(deck=self.deck, card=self.card2, quantity=2, role="Sideboard")
        self.assertEqual(self.deck.member_cards.count(), 2)

    def test_deck_card_quantities(self):
        """Test that deck-card quantities are correct."""
        dc1 = DeckCard.objects.create(deck=self.deck, card=self.card1, quantity=4, role="Main Deck")
        dc2 = DeckCard.objects.create(deck=self.deck, card=self.card2, quantity=3, role="Main Deck")
        self.assertEqual(dc1.quantity, 4)
        self.assertEqual(dc2.quantity, 3)
