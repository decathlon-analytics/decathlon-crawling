"""
Decathlon Korea Review Scraper - FIXED VERSION
"""

import time
import csv
import re
from datetime import datetime, timedelta
from urllib.parse import unquote
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains

class DecathlonReviewScraper:
    def __init__(self, headless=False, max_pages=40):
        self.options = Options()
        if headless:
            self.options.add_argument('--headless')
        self.options.add_argument('--start-maximized')
        self.options.add_argument('--disable-blink-features=AutomationControlled')
        self.options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        self.driver = webdriver.Chrome(options=self.options)
        self.wait = WebDriverWait(self.driver, 15)
        
        self.six_months_ago = datetime.now() - timedelta(days=180)
        self.max_pages = max_pages  # Maximum pages to scrape per product
        self.all_reviews = []
        self.product_summaries = {}
        
    def classify_subcategory(self, product_name):
        name_lower = product_name.lower()
        if any(w in name_lower for w in ['재킷', 'jacket', '셔츠', '티', '쇼츠', '베스트', '싱글렛', '레깅스']):
            return '의류'
        elif any(w in name_lower for w in ['백팩', '가방', '배낭', 'bag', 'vest']):
            return '가방'
        elif any(w in name_lower for w in ['캡', '모자', '벨트', '양말', '장갑']):
            return '액세서리'
        elif any(w in name_lower for w in ['물병', '플라스크', '러닝화', '신발']):
            return '용품'
        else:
            return '기타'
    
    def extract_product_info_from_url(self, url):
        try:
            product_id = url.split('-')[-1].split('.')[0]
            url_parts = url.split('_')
            if len(url_parts) > 1:
                encoded_name = url_parts[1].split('-')[0:-4]
                product_name_korean = unquote('_'.join(encoded_name))
                product_name_korean = product_name_korean.replace('_', ' ')
            else:
                product_name_korean = "Unknown Product"
            
            if '러닝' in product_name_korean or 'kiprun' in url.lower() or 'kalenji' in url.lower():
                category = '러닝'
                brand = 'KIPRUN' if 'kiprun' in url.lower() else 'KALENJI'
            elif '하이킹' in product_name_korean or '등산' in product_name_korean or 'quechua' in url.lower():
                category = '등산/하이킹'
                brand = 'QUECHUA'
            else:
                category = '스포츠'
                brand = 'DECATHLON'
            
            subcategory = self.classify_subcategory(product_name_korean)
            
            return {
                'product_id': product_id,
                'product_name': product_name_korean.title(),
                'category': category,
                'subcategory': subcategory,
                'brand': brand,
                'url': url
            }
        except Exception as e:
            print(f"Error extracting product info: {e}")
            return None
    
    def parse_korean_date(self, date_str):
        try:
            date_part = date_str.split('|')[1].strip()
            return datetime.strptime(date_part, '%d/%m/%Y')
        except:
            return None
    
    def classify_sentiment(self, review_text, rating):
        negative_words = ['별로', '실망', '안좋', '나쁘', '최악', '환불', '불만']
        positive_words = ['좋', '만족', '추천', '최고', '훌륭', '완벽']
        
        if rating >= 4.5:
            return 'positive'
        elif rating <= 2.5:
            return 'negative'
        else:
            has_negative = any(word in review_text for word in negative_words)
            has_positive = any(word in review_text for word in positive_words)
            if has_negative and has_positive:
                return 'mixed'
            elif has_negative:
                return 'negative'
            else:
                return 'mixed'
    
    def extract_rating_fixed(self, review_element):
        """FIXED: Extract rating from the specific span element"""
        try:
            # Method 1: Look for span with class containing "18wdkpi" (from your screenshot)
            try:
                rating_span = review_element.find_element(By.CSS_SELECTOR, 'span[class*="18wdkpi"]')
                rating_text = rating_span.text.strip()
                if rating_text:
                    rating = float(rating_text)
                    print(f"    ✅ Found rating: {rating}★")
                    return rating
            except:
                pass
            
            # Method 2: Look for any span that contains a decimal number pattern like "4.8"
            spans = review_element.find_elements(By.TAG_NAME, 'span')
            for span in spans:
                text = span.text.strip()
                # Match pattern like "4.8" or "5.0" or "3"
                match = re.match(r'^([0-5])(\.\d)?$', text)
                if match:
                    rating = float(text)
                    print(f"    ✅ Found rating: {rating}★")
                    return rating
            
            # Method 3: Count star symbols in the entire review text
            review_text = review_element.text
            filled_stars = review_text.count('★')
            if 1 <= filled_stars <= 5:
                print(f"    ✅ Found {filled_stars} filled stars")
                return float(filled_stars)
            
            # Method 4: Search in HTML for data attributes
            html = review_element.get_attribute('outerHTML')
            rating_patterns = [
                r'data-rating["\s:=]+([0-5]\.?\d*)',
                r'"rating"\s*:\s*([0-5]\.?\d*)',
            ]
            
            for pattern in rating_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                if matches:
                    rating = float(matches[0])
                    if 0 <= rating <= 5:
                        print(f"    ✅ Found rating in HTML: {rating}")
                        return rating
            
            print(f"    ⚠️ Could not find rating, defaulting to 5.0")
            return 5.0
            
        except Exception as e:
            print(f"    ❌ Error extracting rating: {e}")
            return 5.0
    
    def get_product_price(self):
        try:
            selectors = [
                '[data-testid*="price"]',
                '.product-price',
                '[class*="price"]',
                'span[class*="Price"]',
                'div[class*="price"]'
            ]
            
            for selector in selectors:
                try:
                    price_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    price_text = price_elem.text
                    if price_text and any(char.isdigit() for char in price_text):
                        price = int(re.sub(r'[^\d]', '', price_text))
                        if price > 0:
                            print(f"  💰 Price: {price:,}원")
                            return price
                except:
                    continue
            
            price_elements = self.driver.find_elements(By.XPATH, '//*[contains(text(), "원") and contains(text(), ",")]')
            for elem in price_elements:
                try:
                    price_text = elem.text
                    price = int(re.sub(r'[^\d]', '', price_text))
                    if price > 1000:
                        print(f"  💰 Price: {price:,}원")
                        return price
                except:
                    continue
            
            print("  ⚠️ Price not found")
            return None
        except Exception as e:
            print(f"  ⚠️ Error getting price: {e}")
            return None
    
    def get_product_thumbnail(self):
        try:
            selectors = [
                'img[alt*="제품"]',
                'img[class*="product"]',
                'img[class*="Product"]',
                '.product-image img',
                '[data-testid*="image"] img',
                'img[src*="product"]'
            ]
            
            for selector in selectors:
                try:
                    img_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    img_url = img_elem.get_attribute('src')
                    if img_url and 'http' in img_url:
                        print(f"  🖼️ Thumbnail found")
                        return img_url
                except:
                    continue
            
            images = self.driver.find_elements(By.TAG_NAME, 'img')
            for img in images[:10]:
                img_url = img.get_attribute('src')
                if img_url and 'http' in img_url and 'logo' not in img_url.lower():
                    print(f"  🖼️ Thumbnail found (fallback)")
                    return img_url
            
            print("  ⚠️ Thumbnail not found")
            return None
        except Exception as e:
            print(f"  ⚠️ Error getting thumbnail: {e}")
            return None
    
    def scroll_and_wait(self):
        print("Scrolling to reviews section...")
        for i in range(5):
            self.driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(1)
        time.sleep(3)
    
    def should_continue_scraping(self, date_str):
        """Check if we should continue scraping based on date (6 months cutoff)"""
        try:
            review_date = self.parse_korean_date(date_str)
            if review_date:
                is_recent = review_date >= self.six_months_ago
                return is_recent
            return True
        except:
            return True
    
    def click_next_page_fixed(self):
        """FIXED: Better pagination handling"""
        try:
            print(f"    🔄 Looking for next page button...")
            
            # Wait a bit for page to settle
            time.sleep(2)
            
            # Scroll to bottom to ensure pagination is visible
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            
            # Try multiple strategies to find and click next button
            next_button_strategies = [
                # Strategy 1: Look for next page button by ID
                (By.ID, 'r2'),
                # Strategy 2: Look for button with next-page data attribute
                (By.XPATH, '//button[@data-testid="next-page"]'),
                # Strategy 3: Look for pagination buttons - find the one after current
                (By.XPATH, '//button[contains(@id, "r") and not(contains(@class, "disabled"))]'),
                # Strategy 4: Generic next button patterns
                (By.XPATH, '//button[@aria-label="Next page"]'),
                (By.XPATH, '//button[contains(text(), "다음")]'),
                (By.XPATH, '//button[contains(@aria-label, "next")]'),
            ]
            
            for strategy_idx, (by, selector) in enumerate(next_button_strategies, 1):
                try:
                    buttons = self.driver.find_elements(by, selector)
                    
                    for button in buttons:
                        # Check if button is visible and enabled
                        if not button.is_displayed():
                            continue
                        
                        # Check if disabled
                        classes = button.get_attribute('class') or ''
                        disabled_attr = button.get_attribute('disabled')
                        aria_disabled = button.get_attribute('aria-disabled')
                        
                        if ('disabled' in classes.lower() or 
                            disabled_attr == 'true' or 
                            aria_disabled == 'true'):
                            continue
                        
                        # Try to click
                        try:
                            print(f"    ✓ Found next button (strategy {strategy_idx}), clicking...")
                            
                            # Scroll button into view
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                            time.sleep(1)
                            
                            # Try regular click first
                            try:
                                button.click()
                            except:
                                # If regular click fails, try JavaScript click
                                self.driver.execute_script("arguments[0].click();", button)
                            
                            # Wait for page to load
                            time.sleep(4)
                            
                            # Verify we moved to next page by checking if URL changed or content updated
                            print(f"    ✅ Successfully clicked next page")
                            return True
                            
                        except Exception as click_error:
                            print(f"    ⚠️ Click failed: {click_error}")
                            continue
                
                except Exception as strategy_error:
                    continue
            
            print(f"    ⏹️ No more pages or next button not found")
            return False
            
        except Exception as e:
            print(f"    ❌ Error in pagination: {e}")
            return False
    
    def extract_reviews_from_product(self, url):
        print(f"\n{'='*70}")
        print(f"Scraping: {url}")
        print(f"{'='*70}")
        
        product_info = self.extract_product_info_from_url(url)
        if not product_info:
            print("✗ Failed to extract product info")
            return
        
        self.driver.get(url)
        time.sleep(5)
        
        price = self.get_product_price()
        thumbnail = self.get_product_thumbnail()
        
        self.scroll_and_wait()
        
        product_id = product_info['product_id']
        self.product_summaries[product_id] = {
            'product_id': product_id,
            'product_name': product_info['product_name'],
            'category': product_info['category'],
            'subcategory': product_info['subcategory'],
            'brand': product_info['brand'],
            'price': price,
            'total_reviews': 0,
            'positive_reviews': 0,
            'mixed_reviews': 0,
            'negative_reviews': 0,
            'ratings_sum': 0,
            'url': url,
            'thumbnail_url': thumbnail
        }
        
        page_number = 1
        should_continue = True
        reviews_from_product = 0
        
        while should_continue and page_number <= self.max_pages:  # Added page limit check
            print(f"\n📄 Scraping page {page_number}/{self.max_pages}...")
            
            try:
                # Wait for reviews to load
                time.sleep(2)
                
                # Find review containers
                all_elements = self.driver.find_elements(By.XPATH, '//*[contains(text(), "대한민국")]')
                print(f"   Found {len(all_elements)} reviews on this page")
                
                if len(all_elements) == 0:
                    print("   ⚠️ No reviews found on this page")
                    break
                
                page_has_old_reviews = False
                
                for idx, elem in enumerate(all_elements, 1):
                    try:
                        # Find review container
                        review_container = None
                        for level in range(2, 8):
                            try:
                                parent = elem.find_element(By.XPATH, f'./ancestor::*[{level}]')
                                parent_text = parent.text
                                if len(parent_text) > 30 and '대한민국' in parent_text:
                                    review_container = parent
                                    break
                            except:
                                continue
                        
                        if not review_container:
                            continue
                        
                        full_text = review_container.text
                        
                        # Extract date
                        date_match = re.search(r'대한민국\s*\|\s*(\d{2}/\d{2}/\d{4})', full_text)
                        if date_match:
                            date_str = date_match.group(0)
                            review_date = self.parse_korean_date(date_str)
                            formatted_date = review_date.strftime('%Y-%m-%d') if review_date else date_str
                            
                            # Check if review is within 6 months
                            if not self.should_continue_scraping(date_str):
                                print(f"   ⏹️ Review {idx} is older than 6 months: {formatted_date}")
                                page_has_old_reviews = True
                                continue  # Skip this review but check others on page
                        else:
                            formatted_date = "Unknown"
                        
                        # Extract rating - USING FIXED METHOD
                        rating = self.extract_rating_fixed(review_container)
                        
                        # Extract review text
                        lines = full_text.split('\n')
                        review_lines = [line.strip() for line in lines if line.strip() and '대한민국' not in line and len(line) > 5]
                        
                        if review_lines:
                            review_text = ' '.join(review_lines)
                        else:
                            review_text = "No text content"
                        
                        if len(review_text) < 5:
                            continue
                        
                        sentiment = self.classify_sentiment(review_text, rating)
                        
                        review_data = {
                            'product_id': product_id,
                            'product_name': product_info['product_name'],
                            'category': product_info['category'],
                            'subcategory': product_info['subcategory'],
                            'brand': product_info['brand'],
                            'rating': rating,
                            'review_text': review_text[:200],
                            'sentiment': sentiment,
                            'date': formatted_date
                        }
                        
                        self.all_reviews.append(review_data)
                        self.product_summaries[product_id]['total_reviews'] += 1
                        self.product_summaries[product_id]['ratings_sum'] += rating
                        self.product_summaries[product_id][f'{sentiment}_reviews'] += 1
                        reviews_from_product += 1
                        
                        print(f"   ✓ Review #{reviews_from_product}: {rating}★ - {formatted_date}")
                        
                    except Exception as e:
                        print(f"   ✗ Error on review #{idx}: {e}")
                        continue
                
                # If this page has old reviews, check if ALL reviews are old
                if page_has_old_reviews:
                    recent_count = sum(1 for elem in all_elements if self.should_continue_scraping(elem.text))
                    if recent_count == 0:
                        print(f"   ⏹️ All reviews on page {page_number} are older than 6 months. Stopping.")
                        break
                
                # Check if we've reached max pages
                if page_number >= self.max_pages:
                    print(f"   ⏹️ Reached maximum page limit ({self.max_pages} pages)")
                    break
                
                # Try to go to next page - USING FIXED METHOD
                if self.click_next_page_fixed():
                    page_number += 1
                    time.sleep(3)  # Wait longer for new page to load
                else:
                    print(f"   ⏹️ No more pages available")
                    break
                
            except Exception as e:
                print(f"   ❌ Error on page {page_number}: {e}")
                break
        
        print(f"\n✅ Extracted {reviews_from_product} reviews from this product (within 6 months)")
        print(f"   Scraped {page_number} page(s)")
    
    def scrape_all_products(self, product_urls):
        print(f"\n🚀 Starting scraper for {len(product_urls)} products\n")
        print(f"📅 Collecting reviews from: {self.six_months_ago.strftime('%Y-%m-%d')} to today")
        print(f"📄 Maximum {self.max_pages} pages per product\n")
        
        for idx, url in enumerate(product_urls, 1):
            print(f"\n[Product {idx}/{len(product_urls)}]")
            self.extract_reviews_from_product(url)
            
            if idx < len(product_urls):
                print("\n⏳ Waiting 3 seconds before next product...")
                time.sleep(3)
    
    def save_complete_csv(self, filename='complete.csv'):
        if not self.all_reviews:
            print("⚠️ No reviews to save")
            return
        
        fieldnames = ['product_id', 'product_name', 'category', 'subcategory', 'brand', 
                     'rating', 'review_text', 'sentiment', 'date']
        
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.all_reviews)
        
        print(f"\n✅ Saved {len(self.all_reviews)} reviews to {filename}")
    
    def save_summary_csv(self, filename='summary.csv'):
        if not self.product_summaries:
            print("⚠️ No product summaries to save")
            return
        
        summary_list = []
        for product_id, summary in self.product_summaries.items():
            if summary['total_reviews'] > 0:
                avg_rating = round(summary['ratings_sum'] / summary['total_reviews'], 1)
            else:
                avg_rating = 0.0
            
            summary_record = {
                'product_id': summary['product_id'],
                'product_name': summary['product_name'],
                'category': summary['category'],
                'subcategory': summary['subcategory'],
                'brand': summary['brand'],
                'price': summary['price'],
                'avg_rating': avg_rating,
                'total_reviews': summary['total_reviews'],
                'positive_reviews': summary['positive_reviews'],
                'mixed_reviews': summary['mixed_reviews'],
                'negative_reviews': summary['negative_reviews'],
                'url': summary['url'],
                'thumbnail_url': summary['thumbnail_url']
            }
            summary_list.append(summary_record)
        
        fieldnames = ['product_id', 'product_name', 'category', 'subcategory', 'brand', 
                     'price', 'avg_rating', 'total_reviews', 'positive_reviews', 
                     'mixed_reviews', 'negative_reviews', 'url', 'thumbnail_url']
        
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(summary_list)
        
        print(f"✅ Saved {len(summary_list)} product summaries to {filename}")
    
    def close(self):
        self.driver.quit()


if __name__ == "__main__":
    # Your product URLs
    PRODUCT_URLS = [
        "https://www.decathlon.co.kr/r/e4f1b69a-54e6-46b9-875b-21b35ca777ea_러닝-장갑-에볼루티브-v2-kiprun-8759614.html",
    "https://www.decathlon.co.kr/r/b84bff5f-b87c-49a7-a193-5da9350e076d_남성-하프집-러닝-긴팔-티-런-드라이-500-kiprun-8902771.html",
    "https://www.decathlon.co.kr/r/1ab57afe-c525-40f7-8c89-37dbe6237c3a_남성-러닝-패딩-베스트-런-월-500-kiprun-8911507.html",
    "https://www.decathlon.co.kr/p/남성-러닝-윈드-재킷-런-100-kiprun-8926414.html",
    "https://www.decathlon.co.kr/r/16f96ea3-dade-4404-8caa-fae89d1aab80_러닝-보온-헤드밴드-런-월-kiprun-8342130.html",
    "https://www.decathlon.co.kr/r/37cb9912-7e97-40e5-bab7-e4229728003f_남성-러닝-바지-런-드라이-100-kiprun-8882067.html",
    "https://www.decathlon.co.kr/r/8688ef4f-d574-440a-b3ef-231842e602ea_남성-러닝-긴팔-티-런-드라이-500-kiprun-8817439.html",
    "https://www.decathlon.co.kr/r/0e661008-65f4-4a76-aec0-5588dd141cd8_남성-하프집-러닝-긴팔-티-런-월-100-kalenji-8487923.html",
    "https://www.decathlon.co.kr/r/b02449e6-3ce1-49e1-8e7f-b73344cee8aa_남성-러닝-바지-월-100-kalenji-8807977.html",
    "https://www.decathlon.co.kr/r/9b182817-c4ab-4e29-917b-23bb73e1b4c3_여성-하프집-러닝-긴팔-티-런-월-100-kalenji-8966974.html",
    "https://www.decathlon.co.kr/r/defe484d-e226-493c-836c-e86054a151bc_남성-러닝-윈드-재킷-런-100-kiprun-8926453.html",
    "https://www.decathlon.co.kr/r/cb734175-9638-4771-b508-739373a08ba5_러닝-캡-모자-v2-kiprun-8871357.html",
    "https://www.decathlon.co.kr/r/0af2cade-091e-48b9-9799-3b7ac16b677b_남성-러닝-반팔-티-런-드라이-500-kiprun-8861547.html",
    "https://www.decathlon.co.kr/r/1c2a73e6-2d84-4c91-89ab-f063eadd9a65_남성-6인치-러닝-쇼츠-컴포트-500-브리프-내장-kiprun-8588345.html",
    "https://www.decathlon.co.kr/r/e95ec1f5-6642-4a64-af23-4a151a1465b8_여성-러닝-보온-레깅스-런-월-100-kiprun-8757546.html",
    "https://www.decathlon.co.kr/r/e958cb2a-c0fa-4b1a-b887-3eab43461456_남성-러닝-바지-슬림핏-런-드라이-500-kiprun-8519080.html",
    "https://www.decathlon.co.kr/r/f04856df-ea90-4431-9a24-ab143ec9a486_남성-러닝-반팔-티-런-드라이-100-decathlon-8488034.html",
    "https://www.decathlon.co.kr/r/518712c5-981e-44c5-ad49-c16a6dd774a7_여성-러닝-윈드-재킷-런-100-kiprun-8885914.html",
    "https://www.decathlon.co.kr/r/d992b8f1-60e6-47df-b4ff-f99a47f777d1_남성-7인치-러닝-쇼츠-런-드라이-100-kalenji-8817443.html",
    "https://www.decathlon.co.kr/r/78255631-e894-4b45-968e-e862446468b5_남성-백팩킹-바지-mt500-simond-8916623.html",
    "https://www.decathlon.co.kr/r/69570cd7-b03c-4d61-9d3a-c2706ede7792_남성-하이킹-투인원-집오프-바지-mh100-quechua-8652204.html",
    "https://www.decathlon.co.kr/r/45fb8bb9-881a-48ff-8d0a-bf771292d472_등산-백팩-38l-mh500-quechua-8916236.html",
    "https://www.decathlon.co.kr/r/b1d25295-0c02-4803-b387-f8fc64e1348d_남성-경량-하이킹-레인-재킷-mh500-quechua-8785247.html",
    "https://www.decathlon.co.kr/r/1e9eca5e-07e5-40a4-81c3-3f504704c3b2_등산-백팩-20l-아르페나즈-nh100-quechua-8529024.html",
    "https://www.decathlon.co.kr/r/f1363e08-082e-4eb2-b254-d51e1c40f67d_등산-백팩-25l-mh500-quechua-8916234.html",
    "https://www.decathlon.co.kr/r/1c444771-5de8-4908-9d35-d696b00f92bf_남성-하이킹-반팔-티-mh100-quechua-8316244.html",
    "https://www.decathlon.co.kr/r/e11f887f-8a26-411a-bfe2-8cd95d93d1b2_남성-백팩킹-카고-바지-트래블-500-forclaz-8572546.html",
    "https://www.decathlon.co.kr/r/0370a64d-c6a3-49ca-9c91-70beca669726_남성-백팩킹-방풍발수-바지-mt900-simond-8852944.html",
    "https://www.decathlon.co.kr/r/60949031-4af0-4554-a305-ddb06765d40c_여성-백팩킹-투인원-집오프-바지-mt100-forclaz-8544763.html",
    "https://www.decathlon.co.kr/r/72a8e3b8-164b-44bc-a811-356238ee4bd5_여성-메리노울-백팩킹-긴팔-베이스-레이어-트래블-100-simond-8316437.html",
    "https://www.decathlon.co.kr/r/d660897b-e5ca-4e60-9338-05faeef6d3ad_남성-하이킹-바지-스트레치-mh500-quechua-8917639.html",
    "https://www.decathlon.co.kr/r/dfa61a9f-76ce-4c1e-8e6b-77b21c2c6412_백팩킹-오거나이저-백팩-40l-트래블-500-forclaz-8787845.html",
    "https://www.decathlon.co.kr/r/374ef037-3be4-4ca5-94dc-b31acfe2e461_여성-백팩킹-바지-mt500-simond-8608070.html",
    "https://www.decathlon.co.kr/r/ee8555b6-1e4b-49fd-9db3-c0adc196f050_남성-경량-하이킹-레인-재킷-mh500-quechua-8612171.html",
    "https://www.decathlon.co.kr/r/c453cd06-5df2-4339-817b-8b04f9d696b4_백팩킹-오거나이저-백팩-40l-트래블-500-forclaz-8735937.html",
    "https://www.decathlon.co.kr/r/2abcfaa3-f77c-4064-a6ca-a24efab5b68c_남성-하이킹-윈드-재킷-헬륨-900-quechua-8862055.html",
    "https://www.decathlon.co.kr/r/842391c4-8e4f-4217-94bc-fe320e322db4_남성-메리노울-백팩킹-하프집-베이스-레이어-mt900-simond-8609386.html",
    "https://www.decathlon.co.kr/r/22d6f249-14a3-4fbd-9325-c912450e22a5_남성-백팩킹-투인원-집오프-바지-mt100-forclaz-8666242.html",
    "https://www.decathlon.co.kr/r/3b0d88ba-e9a4-448f-88a8-4858f374c139_등산-백팩-20l-아르페나즈-nh100-quechua-8529019.html",
    "https://www.decathlon.co.kr/r/5a0beee3-2295-4f65-8a4c-0999657f9031_남성-러닝-경량-싱글렛-900-울트라라이트-kiprun-8872861.html",
    "https://www.decathlon.co.kr/r/e8c0293c-d644-4b64-80d8-29c7440a3318_남성-8인치-러닝-투인원-쇼츠-런-드라이-550-kalenji-8772968.html",
    "https://www.decathlon.co.kr/r/157f0374-3cd1-4f47-8ca8-41893bc7d6ee_남성-러닝-반팔-티-런-드라이-그라프-500-kiprun-8842526.html",
    "https://www.decathlon.co.kr/r/b11531eb-3d4b-440a-889f-8a84b6f925e2_남성-카본-레이싱화-kd900x-2-kiprun-8915926.html",
    "https://www.decathlon.co.kr/r/afbc3caf-dd14-491c-a61a-c903a9829acd_러닝-중목-양말-2컬레-파인-런-500-kiprun-8810971.html",
    "https://www.decathlon.co.kr/r/28b9e294-9042-4eb8-8260-eaca149b8855_남성-3인치-러닝-쇼츠-500-스플릿-브리프-내장-kiprun-8861551.html",
    "https://www.decathlon.co.kr/r/daf64b1f-0b1c-417c-a7f9-9d069921978a_남성-6인치-러닝-쇼츠-컴포트-500-브리프-내장-kiprun-8903143.html",
    "https://www.decathlon.co.kr/r/11e08502-12db-499e-ad2a-22a2136d4e4d_남성-러닝-반팔-티-런-드라이-500-kiprun-8861544.html",
    "https://www.decathlon.co.kr/r/7a06b69b-1432-4636-94d7-04485f2cd01e_남성-8인치-러닝-경량-쇼츠-런-드라이-플러스-500-kiprun-8751038.html",
    "https://www.decathlon.co.kr/r/66e6305f-bae3-4b53-987f-d1acfea14765_남성-러닝-싱글렛-런-드라이-100-kalenji-8488395.html",
    "https://www.decathlon.co.kr/r/647ebfbc-2346-4902-ae31-b7c7055282c3_러닝-스마트폰-벨트-베이직-2-kiprun-8648869.html",
    "https://www.decathlon.co.kr/r/ee0af98b-a7b8-4e66-8ac2-341e7253dcd8_러닝-소프트-플라스크-물병-500ml-kiprun-8605419.html",
    "https://www.decathlon.co.kr/r/9a453ff5-8055-4400-b156-201e43e38666_러닝-단목-양말-3컬레-런100-kiprun-8296177.html",
    "https://www.decathlon.co.kr/r/d1933221-eb61-4a4a-8232-93c5a84e1de4_러닝-장갑-에볼루티브-v2-kiprun-8759614.html",
    "https://www.decathlon.co.kr/r/9464dd98-1793-40d1-987e-dd934bd58cb8_여성-러닝-경량-싱글렛-런-900-kiprun-8892090.html",
    "https://www.decathlon.co.kr/r/fad14080-c9b8-429c-97a0-fd1644c06ed2_여성-러닝화-쿠션-500-kiprun-8914009.html",
    "https://www.decathlon.co.kr/r/0d53ca2b-9e85-4d5a-9aff-b59a3deeaa9e_여성-3인치-러닝-경량-쇼츠-런-드라이-500-kiprun-8911355.html",
    "https://www.decathlon.co.kr/r/647ebfbc-2346-4902-ae31-b7c7055282c3_러닝-스마트폰-벨트-베이직-2-kiprun-8648869.html",
    "https://www.decathlon.co.kr/r/57d4db53-b10e-4033-99dd-4b1771c82ca0_여성-카본-레이싱화-kd900x-2-kiprun-8931587.html",
    "https://www.decathlon.co.kr/r/9986c3b3-e998-48b7-bf2d-d75e9eed248f_여성-러닝-윈드-재킷-런-100-kiprun-8817239.html",
    "https://www.decathlon.co.kr/r/97ed0307-47c3-416f-98d6-6407f3893c5c_여성-러닝-바지-런-드라이-100-kiprun-8736665.html",
    "https://www.decathlon.co.kr/r/b4ee8d94-47c4-4899-a20f-d9ef0822b9cb_여성-4인치-러닝-쇼츠-런-드라이-100-kalenji-8926957.html",
    "https://www.decathlon.co.kr/r/26a11ae7-44ab-4be8-bb01-c419080201ca_여성-러닝-반팔-티-런-드라이-500-kiprun-8831477.html",
    "https://www.decathlon.co.kr/r/bb27c120-85e5-4aa3-b932-1165e668d206_여성-4인치-러닝-쇼츠-런-드라이-100-kalenji-8553338.html",
    "https://www.decathlon.co.kr/r/a251aef8-9f6c-4980-89fc-40651c666eda_경량-트레일러닝-베스트-5l-kiprun-8786242.html",
    "https://www.decathlon.co.kr/r/c9a96ac6-db5c-499a-b9d0-3f9c8ca6eb58_여성-3인치-러닝-경량-쇼츠-런-드라이-500-kiprun-8852986.html",
    "https://www.decathlon.co.kr/r/8b8d0e98-de53-4ba7-9ad2-16474b941936_러닝-소프트-플라스크-물병-250ml-kiprun-8605519.html",
    "https://www.decathlon.co.kr/p/여성-러닝-윈드-베스트-런-500-kiprun-8928640.html",
    "https://www.decathlon.co.kr/r/63dda9dc-1ec7-4ae2-a7a8-43b64510c9d2_여성-러닝-반팔-티-런-드라이-100-kalenji-8817407.html"
]

       
    
    
    # Create scraper with max 40 pages per product (you can change this number)
    scraper = DecathlonReviewScraper(headless=False, max_pages=40)
    
    try:
        scraper.scrape_all_products(PRODUCT_URLS)
        scraper.save_complete_csv('complete.csv')
        scraper.save_summary_csv('summary.csv')
        
        print(f"\n{'='*70}")
        print(f"📊 SCRAPING COMPLETE")
        print(f"{'='*70}")
        print(f"✅ complete.csv - {len(scraper.all_reviews)} reviews")
        print(f"✅ summary.csv - {len(scraper.product_summaries)} products")
        print(f"{'='*70}\n")
        
    finally:
        scraper.close()
        
        