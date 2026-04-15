from django import forms
from main.models import Card


class CardFilterForm(forms.Form):
    """
    Form to filter Standard format cards.
    Allows filtering by name, set, minimum and maximum price.
    """
    
    name = forms.CharField(
        required=False,
        max_length=200,
        label='Card Name',
        widget=forms.TextInput(attrs={
            'class': 'uk-input',
            'placeholder': 'Search by name...'
        })
    )
    
    set = forms.ChoiceField(
        required=False,
        label='Set',
        widget=forms.Select(attrs={
            'class': 'uk-select'
        })
    )
    
    price_min = forms.FloatField(
        required=False,
        min_value=0,
        label='Minimum Price (€)',
        widget=forms.NumberInput(attrs={
            'class': 'uk-input',
            'placeholder': 'E.g.: 0.50',
            'step': '0.01',
            'min': '0'
        })
    )
    
    price_max = forms.FloatField(
        required=False,
        min_value=0,
        label='Maximum Price (€)',
        widget=forms.NumberInput(attrs={
            'class': 'uk-input',
            'placeholder': 'E.g.: 100',
            'step': '0.01',
            'min': '0'
        })
    )
    
    rarity = forms.ChoiceField(
        required=False,
        label='Rarity',
        widget=forms.Select(attrs={
            'class': 'uk-select'
        })
    )
    
    def __init__(self, *args, **kwargs):
        """
        Initialize the form with dynamic set options
        obtained from the database.
        """
        super().__init__(*args, **kwargs)
        
        # Get unique sets from the database
        sets = Card.objects.values_list('set', flat=True).distinct().order_by('set')
        set_choices = [('', '-- All --')] + [(e, e) for e in sets]
        self.fields['set'].choices = set_choices
        
        # Get unique rarities from the database
        rarities = Card.objects.values_list('rarity', flat=True).distinct().order_by('rarity')
        rarity_choices = [('', '-- All --')] + [(r, r) for r in rarities if r]
        self.fields['rarity'].choices = rarity_choices
    
    def get_filtered_cards(self):
        """
        Returns the queryset of cards filtered according to form values.
        Should be called after validating the form with is_valid().
        """
        cards_queryset = Card.objects.all()
        
        if self.is_valid():
            # Filter by name
            name = self.cleaned_data.get('name')
            if name:
                cards_queryset = cards_queryset.filter(name__icontains=name)
            
            # Filter by set
            set = self.cleaned_data.get('set')
            if set:
                cards_queryset = cards_queryset.filter(set=set)
            
            # Filter by minimum price
            price_min = self.cleaned_data.get('price_min')
            if price_min is not None:
                cards_queryset = cards_queryset.filter(price_trend__gte=price_min)
            
            # Filter by maximum price
            price_max = self.cleaned_data.get('price_max')
            if price_max is not None:
                cards_queryset = cards_queryset.filter(price_trend__lte=price_max)
            
            # Filter by rarity
            rarity = self.cleaned_data.get('rarity')
            if rarity:
                cards_queryset = cards_queryset.filter(rarity=rarity)
        
        # Order by price trend descending
        return cards_queryset.order_by('-price_trend')


class UserIdForm(forms.Form):
    """
    Form to input a user ID for deck recommendations.
    """
    
    user_id = forms.IntegerField(
        required=True,
        min_value=1,
        label='User ID',
        widget=forms.NumberInput(attrs={
            'class': 'uk-input',
            'placeholder': 'Enter user ID (e.g.: 1, 2, 3...)',
            'min': '1',
            'step': '1'
        })
    )


class GenerateRatingsForm(forms.Form):
    """
    Form to specify the number of users to generate for the ratings system.
    """
    
    num_users = forms.IntegerField(
        required=True,
        min_value=1,
        max_value=10000,
        initial=50,
        label='Number of Users',
        widget=forms.NumberInput(attrs={
            'class': 'uk-input',
            'placeholder': 'Enter number of users (e.g.: 50, 100, 500...)',
            'min': '1',
            'max': '10000',
            'step': '1'
        })
    )
