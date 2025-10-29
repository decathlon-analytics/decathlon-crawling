# decathlon-crawling
A Python web scraper to collect product reviews, ratings, and product information from **Decathlon Korea**.

---

## 📦 Project Structure
```
decathlon-crawling/
├── decathlon_scraper.py    # Main Python scraper script
├── README.md               # This file
├── requirements.txt        # Python dependencies
├── .gitignore              # Files/folders to ignore in Git
└── data/
    ├── complete.csv        # All raw review data
    └── summary.csv         # Summarized product data
```

---

## 🛠 Features

- ✅ Scrapes product reviews, ratings, and basic product information from Decathlon Korea
- ✅ Collects reviews from the **last 6 months only**
- ✅ Handles pagination automatically (configurable page limit)
- ✅ Extracts product prices, thumbnails, and metadata
- ✅ Classifies review sentiment (positive/mixed/negative)
- ✅ Generates **complete.csv** with all review data
- ✅ Generates **summary.csv** with aggregated product statistics
- ✅ Uses **Selenium** for automated browser-based scraping

---

## 📋 Prerequisites

Before running the scraper, ensure you have:

1. **Python 3.7+** installed
2. **Google Chrome** or **Chromium** browser installed
3. **ChromeDriver** installed and in your PATH
   - Option A: Download from [ChromeDriver Downloads](https://chromedriver.chromium.org/downloads)
   - Option B: Use `webdriver-manager` (included in requirements.txt)

---

## ⚙️ Installation

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/decathlon-crawling.git
cd decathlon-crawling
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

**requirements.txt contents:**
```
selenium>=4.15.0
webdriver-manager>=4.0.0
```

---

## 🚀 How to Run

### Basic Usage

1. **Edit the product URLs** in `decathlon_scraper.py`:
```python
PRODUCT_URLS = [
    "https://www.decathlon.co.kr/p/your-product-url-1.html",
    "https://www.decathlon.co.kr/p/your-product-url-2.html",
    # Add more URLs here
]
```

2. **Run the scraper:**
```bash
python decathlon_scraper.py
```

3. **Find your data** in the `data/` folder:
   - `complete.csv` - All individual reviews
   - `summary.csv` - Product summaries and statistics

---

## ⚙️ Configuration Options

You can customize the scraper behavior by modifying these parameters:
```python
scraper = DecathlonReviewScraper(
    headless=False,    # Set to True to run browser in background
    max_pages=40       # Maximum pages to scrape per product
)
```

### Configuration Parameters:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `headless` | `False` | Run browser in background (no GUI) |
| `max_pages` | `40` | Maximum number of review pages per product |
| Date filter | 6 months | Only collects reviews from last 180 days |

---

## 📄 Output CSV Details

### `complete.csv`
Contains all scraped reviews with the following columns:

| Column | Type | Description |
|--------|------|-------------|
| `product_id` | String | Unique product identifier |
| `product_name` | String | Name of the product |
| `category` | String | Main product category (러닝, 등산/하이킹, etc.) |
| `subcategory` | String | Subcategory (의류, 가방, 액세서리, 용품) |
| `brand` | String | Product brand (KIPRUN, KALENJI, QUECHUA, etc.) |
| `rating` | Float | Rating given in review (0.0-5.0) |
| `review_text` | String | Review text content (max 200 chars) |
| `sentiment` | String | Sentiment classification (positive/mixed/negative) |
| `date` | String | Date of review (YYYY-MM-DD format) |

**Example row:**
```csv
8927845,메리노울 백팩킹 비니 Mt500,등산/하이킹,액세서리,SIMOND,4.5,"정말 따뜻하고 좋아요...",positive,2024-09-15
```

### `summary.csv`
Contains aggregated product information:

| Column | Type | Description |
|--------|------|-------------|
| `product_id` | String | Unique product identifier |
| `product_name` | String | Name of the product |
| `category` | String | Main category |
| `subcategory` | String | Subcategory |
| `brand` | String | Product brand |
| `price` | Integer | Product price in KRW (원) |
| `avg_rating` | Float | Average rating across all reviews |
| `total_reviews` | Integer | Total number of reviews collected |
| `positive_reviews` | Integer | Count of positive reviews |
| `mixed_reviews` | Integer | Count of mixed sentiment reviews |
| `negative_reviews` | Integer | Count of negative reviews |
| `url` | String | Product page URL |
| `thumbnail_url` | String | Product image URL |

**Example row:**
```csv
8927845,메리노울 백팩킹 비니 Mt500,등산/하이킹,액세서리,SIMOND,29900,4.6,45,38,5,2,https://...,https://...
```

---

## 🎯 Sentiment Classification Logic

Reviews are automatically classified based on:

- **Positive**: Rating ≥ 4.5 OR contains positive keywords
- **Negative**: Rating ≤ 2.5 OR contains negative keywords
- **Mixed**: Everything else, or contains both positive and negative keywords

**Positive keywords:** 좋, 만족, 추천, 최고, 훌륭, 완벽  
**Negative keywords:** 별로, 실망, 안좋, 나쁘, 최악, 환불, 불만

---

## 🔧 Troubleshooting

### ChromeDriver Issues
If you get "ChromeDriver not found" errors:
```bash
# Option 1: Install webdriver-manager (already in requirements.txt)
pip install webdriver-manager

# Then modify your code to use:
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

service = Service(ChromeDriverManager().install())
self.driver = webdriver.Chrome(service=service, options=self.options)
```

### No Reviews Found
- Verify the product URL is correct
- Check if the product has reviews on the website
- The scraper only collects reviews from the **last 6 months**

### Rate Limiting / Blocking
- Increase delays between requests: `time.sleep(5)`
- Run in non-headless mode: `headless=False`
- Reduce `max_pages` to avoid excessive requests

---

## 📊 Sample Output

After running the scraper, you'll see output like:
```
🚀 Starting scraper for 5 products
📅 Collecting reviews from: 2024-04-30 to today
📄 Maximum 40 pages per product

[Product 1/5]
======================================================================
Scraping: https://www.decathlon.co.kr/p/메리노울-백팩킹-비니...
======================================================================
  💰 Price: 29,900원
  🖼️ Thumbnail found

📄 Scraping page 1/40...
   Found 10 reviews on this page
   ✓ Review #1: 4.5★ - 2024-09-15
   ✓ Review #2: 5.0★ - 2024-09-10
   ...

✅ Extracted 45 reviews from this product (within 6 months)

======================================================================
📊 SCRAPING COMPLETE
======================================================================
✅ complete.csv - 237 reviews
✅ summary.csv - 5 products
======================================================================
```

---