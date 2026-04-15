from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Card(models.Model):
    """
    Model representing a Magic: The Gathering card.
    Cards are uniquely identified by (name, set, card_number) to handle
    different versions of the same card within the same set.
    """
    id_card = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200, verbose_name="Card name")
    version = models.CharField(max_length=10, null=True, blank=True, verbose_name="Version (e.g., V.1, V.2)")
    rarity = models.CharField(max_length=50, null=True, verbose_name="Rarity")
    card_number = models.CharField(max_length=20, null=True, verbose_name="Card number in Set")
    set = models.CharField(max_length=100, verbose_name="Set")
    image_url = models.URLField(max_length=500, null=True, verbose_name="Image URL")
    available_items = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Available items")
    price_from = models.FloatField(validators=[MinValueValidator(0)], null=True, verbose_name="Price from")
    price_trend = models.FloatField(validators=[MinValueValidator(0)], null=True, verbose_name="Price trend")
    avg_30_days = models.FloatField(validators=[MinValueValidator(0)], null=True, verbose_name="30 days average")
    avg_7_days = models.FloatField(validators=[MinValueValidator(0)], null=True, verbose_name="7 days average")
    avg_1_day = models.FloatField(validators=[MinValueValidator(0)], null=True, verbose_name="1 day average")

    def __str__(self):
        if self.version:
            return f"{self.name} ({self.version}) ({self.set} #{self.card_number})"
        return f"{self.name} ({self.set} #{self.card_number})"

    class Meta:
        ordering = ("name",)
        unique_together = ("name", "version", "set")


class Deck(models.Model):
    """
    Model representing a Magic: The Gathering deck.
    """
    id_deck = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, verbose_name="Deck name")
    alternative_name = models.CharField(max_length=100, null=True, verbose_name="Alternative deck name")

    # Free text (e.g.: "Combo", "Token", "Aggro", "Midrange", "Control", "Other")
    archetype = models.CharField(max_length=30, verbose_name="Archetype")
    # Free text (e.g.: "Mono White", "Jeskai", "Selesnya", "4C", "5C", "Colorless")
    color_identity = models.CharField(max_length=30, verbose_name="Color identity")
    # Colors used (free text, e.g.: "White Blue Red")
    colors_used = models.CharField(max_length=50, verbose_name="Colors used")

    member_cards = models.ManyToManyField(Card, through="DeckCard")

    # Meta percentage (0-100)
    meta_percentage = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)], verbose_name="Meta percentage")

    def __str__(self):
        return self.name

    class Meta:
        ordering = ("-meta_percentage",)
        unique_together = ("name", "alternative_name")


class DeckCard(models.Model):
    """
    Intermediate entity: Deck-Card relationship with quantity and role.
    Recommended role values: "side", "core".
    """
    id_deck_card = models.AutoField(primary_key=True)
    deck = models.ForeignKey(Deck, on_delete=models.CASCADE)
    card = models.ForeignKey(Card, on_delete=models.CASCADE)
    quantity = models.IntegerField(validators=[MinValueValidator(1)], verbose_name="Card quantity")
    role = models.CharField(max_length=20, verbose_name="Role")

    def __str__(self):
        return str(self.quantity)


class Seller(models.Model):
    """
    Model representing a CardMarket seller.
    """
    id_seller = models.AutoField(primary_key=True)
    name = models.CharField(max_length=150, unique=True, verbose_name="Seller name")
    real_name = models.CharField(max_length=200, null=True, verbose_name="Real name")
    country = models.CharField(max_length=80, verbose_name="Country")
    sales_count = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Sales count")
    available_items = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Available items")

    # Free text for type: e.g. "Professional" or "Powerseller"
    seller_type = models.CharField(max_length=60, verbose_name="Seller type")

    # Rating as text: e.g. "Outstanding", "Very good", "Good"
    rating = models.CharField(max_length=50, verbose_name="Rating")

    # Approval percentages
    approval_very_good = models.CharField(max_length=10, null=True, verbose_name="Very good approval %")
    approval_good = models.CharField(max_length=10, null=True, verbose_name="Good approval %")
    approval_neutral = models.CharField(max_length=10, null=True, verbose_name="Neutral approval %")
    approval_bad = models.CharField(max_length=10, null=True, verbose_name="Bad approval %")

    # Shipping days (null if on vacation)
    shipping_days = models.IntegerField(null=True, validators=[MinValueValidator(0)], verbose_name="Shipping days")

    # Address information
    street_address = models.CharField(max_length=300, null=True, verbose_name="Street address")
    postal_code = models.CharField(max_length=20, null=True, verbose_name="Postal code")
    city = models.CharField(max_length=100, null=True, verbose_name="City")

    cards = models.ManyToManyField(
        "Card",
        through="SellerCard",
        related_name="sellers",
    )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ("-sales_count",)


class SellerCard(models.Model):
    """
    Intermediate entity: Seller-Card relationship with quantity, price, condition and language.
    """
    id_seller_card = models.AutoField(primary_key=True)
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE)
    card = models.ForeignKey(Card, on_delete=models.CASCADE)
    quantity = models.IntegerField(validators=[MinValueValidator(1)], verbose_name="Available inventory")

    # Unit price
    price = models.FloatField(validators=[MinValueValidator(0)], verbose_name="Unit price")

    # Currency type: e.g. "EUR", "USD", "GBP"
    currency = models.CharField(max_length=10, default="EUR", verbose_name="Currency")

    # Free text: e.g. "Near Mint", "Excellent", "Good", "Light Played", "Played", "Poor"
    condition = models.CharField(max_length=40, verbose_name="Condition")

    # Free text: e.g. "Spanish", "English"...
    language = models.CharField(max_length=40, verbose_name="Language")

    def __str__(self):
        return f"{self.seller.name} - {self.card.name}"

    class Meta:
        ordering = ("price", "-quantity")


class User(models.Model):
    """
    Model representing a user for the recommendation system.
    Stores synthetic users for generating deck ratings.
    """
    id_user = models.AutoField(primary_key=True)
    username = models.CharField(max_length=100, unique=True, verbose_name="Username")
    
    # Preference weights for archetypes (used to generate consistent ratings)
    preferred_archetype = models.CharField(max_length=30, null=True, blank=True, verbose_name="Preferred archetype")
    preferred_colors = models.CharField(max_length=50, null=True, blank=True, verbose_name="Preferred colors")
    
    def __str__(self):
        return self.username
    
    class Meta:
        ordering = ("username",)


class DeckRating(models.Model):
    """
    Model representing a user's rating of a deck.
    Used for the recommendation system.
    """
    id_rating = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ratings")
    deck = models.ForeignKey(Deck, on_delete=models.CASCADE, related_name="ratings")
    rating = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        verbose_name="Rating (0-5)"
    )
    
    def __str__(self):
        return f"{self.user.username} -> {self.deck.name}: {self.rating}"
    
    class Meta:
        ordering = ("-rating",)
        unique_together = ("user", "deck")