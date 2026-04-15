# AII-Project - Magic: The Gathering Deck Optimizer & Recommender

Samuel Tamayo Balogh's Project for the AII course (Acceso Inteligente a la Información)

## Description

This Django web application is a comprehensive tool for Magic: The Gathering players that helps:

- **Optimize deck purchases** by finding the best prices across multiple sellers on CardMarket
- **Calculate optimal shipping** by minimizing total cost including shipping fees based on weight
- **Recommend decks** using collaborative filtering based on user ratings

The application scrapes data from [CardMarket](https://www.cardmarket.com) and [MTGGoldfish](https://www.mtggoldfish.com/) and provides analysis to help make cost-effective purchasing decisions.

## Features

### Card & Seller Management

- Browse and search cards from the MTG Standard sets
- View detailed card information including prices across different sellers
- Explore seller profiles with their card offerings

### Deck Optimization

- **Price Optimization**: Find the minimum price for each card in a deck across all sellers
- **Shipping Optimization**: Minimize total cost by consolidating purchases to reduce shipping fees
- **Land Interchangeability**: Basic lands are searched across all expansions to find the best prices

### Recommendation System

- Collaborative filtering algorithm using Pearson correlation
- User-based recommendations for deck preferences
- Generate synthetic user ratings for testing the recommendation system

### Data Extraction

- Automated extraction of cards, sellers, and sets from CardMarket
- Export data to CSV format
- Populate database from extracted data

## Technologies

- **Web Scraping**: [AutoScrape](https://github.com/DrankRock/AutoScrape) for CardMarket. MTGGolsfish is scraped inside the app.
- **Recommendation Engine**: Shelve-based collaborative filtering

## Data Scraping with AutoScrape

This project uses [AutoScrape](https://github.com/DrankRock/AutoScrape) to extract data from CardMarket. AutoScrape is a tool that automates web scraping with human-like behavior to avoid detection.

### AutoScrape Configuration

To scrape CardMarket data, configure AutoScrape with the following settings:

| Setting | Value |
|---------|-------|
| **Selenium** | base |
| **Human Behaviour** | True |
| **Headless** | False |
| **Behavior Intensity** | High |

### Scraping Process

1. Clone and set up AutoScrape from the repository
2. Configure with the settings above
3. Use the link files in `data/links/` as input:
   - `cards.txt` - Links to individual card pages
   - `sellers.txt` - Links to seller profiles
   - `sets.txt` - Links to MTG set pages
4. Scraped HTML files will be saved to `data/html/`

## Project Structure

```
AII-Project/
├── main/                    # Main Django application
│   ├── models.py           # Database models (Card, Seller, SellerCard, User, DeckRating)
│   ├── views.py            # View functions
│   ├── forms.py            # Django forms
│   ├── populate.py         # Database population scripts
│   ├── templates/          # HTML templates
│   └── migrations/         # Database migrations
├── proyecto/               # Django project settings
├── data/                   # Data extraction directory
│   ├── data.py            # Data extraction logic
│   ├── csv/               # Extracted CSV files
│   ├── html/              # Scraped HTML files (not in repo)
│   └── links/             # URLs for scraping
├── static/                # Static files (CSS, JS, images)
└── manage.py              # Django management script
```

## Database Models

### Card

Stores Magic: The Gathering card information including name, expansion, rarity, and minimum price.

### Seller

Stores seller information from CardMarket including name, location, rating, and sales count.

### SellerCard

Junction table linking cards to sellers with pricing and availability information.

### User

Synthetic users for the recommendation system.

### DeckRating

User ratings for decks used in collaborative filtering recommendations.

## Usage

### Populating the Database

1. Navigate to the **Populate** section from the main menu
2. Enter the number of users to generate for the recommendation system
3. Click "Populate Database"
4. The system will import cards, sellers, and create synthetic user ratings

### Optimizing a Deck

1. Go to the **Decks** section
2. Enter your deck list (one card per line)
3. Choose optimization type:
   - **Optimize by Price**: Find cheapest individual cards
   - **Optimize by Shipping**: Minimize total cost including shipping

### Getting Recommendations

1. Go to the **Recommendations** section
2. Enter a User ID
3. View recommended decks based on collaborative filtering

## Shipping Calculation

Shipping costs are calculated based on package weight using CardMarket's standard rates:

| Weight Range | Base Cost | Extra Cost |
| ------------- | ----------- | ------------ |
| 0-20g | €0.85 | - |
| 20-50g | €1.00 | €0.05/g |
| 50-100g | €2.00 | €0.04/g |
| 100-250g | €3.00 | €0.03/g |
| 250-500g | €5.00 | €0.02/g |
| 500-1000g | €7.00 | €0.015/g |
| 1000-2000g | €10.00 | €0.01/g |
| >2000g | €15.00 | €0.008/g |

Each card weighs approximately 1.8 grams.

## License

This project is developed for educational purposes as part of the AII course.

## Acknowledgments

- [CardMarket](https://www.cardmarket.com) - Data source for MTG card prices
- [MTGGoldfish](https://www.mtggoldfish.com/) - Data source for MTG Standard Decks
- [AutoScrape](https://github.com/DrankRock/AutoScrape) - Web scraping tool
