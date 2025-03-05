# Apify Store Actors Scraper

This project is a web scraper developed with Playwright and Python to extract all actors' data from the [Apify Store](https://apify.com/store/categories).

## Features

- Automatically scrolls to load all actors (approximately 4000+ records in total)
- Extracts detailed information for each actor:
  - Title
  - Slug (URL identifier)
  - Description
  - Author name
  - Number of users
  - Rating
- Saves the scraped data as a CSV file

## Requirements

- Python 3.8+
- Playwright
- Pandas
- Other dependencies (see `requirements.txt`)

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd apify
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install Playwright browsers:
```bash
playwright install
```

## Usage

Run the script to start scraping:

```bash
python scrape_actors.py
```

The script will automatically:
1. Open a browser and navigate to the Apify Store
2. Scroll the page until all actors are loaded
3. Extract data from all actors
4. Save the data to an `apify_actors.csv` file

## Output Example

The generated CSV file contains the following fields:
- `title`: Actor title
- `slug`: Unique identifier for the actor
- `description`: Actor description
- `author`: Author name
- `users`: Number of users
- `rating`: Rating
- `url`: Actor URL

## Notes

- The scraper runs in headed browser mode, showing the browser interface during the process
- The complete scraping process may take several minutes, depending on network speed and total number of records
- The script includes automatic detection to stop scraping when no new content is loaded after multiple scrolls