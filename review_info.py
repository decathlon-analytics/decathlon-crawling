import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
import re

class DecathlonTrulyFinalCrawler:
    
    def __init__(self, debug=True):
        self.debug = debug
        options = Options() 
        if not debug:
            options.add_argument('--headless')
        options.add_argument('--start-maximized')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        self.driver = webdriver.Chrome(options=options)
        self.driver.maximize_window()
        self.wait = WebDriverWait(self.driver, 20)
        
    def extract_product_info(self, url):
        try:
            print(f"\n{'='*80}")
            print(f"Crawling: {url}")
            print(f"{'='*80}")
            
            self.driver.get(url)
            time.sleep(5)
            
            product_data = {
                "상품ID": "",
                "상품명": "",
                "브랜드": "",
                "설명": "",
                "특징 및 장점": "",
                "기술 정보": "",
                "구성/추천": "",
                "관리 지침": "",
                "URL": url
            }
            
            # Basic info
            product_data.update(self._extract_basic_info())
            
            # Expand EVERYTHING
            print("→ Expanding all sections aggressively...")
            self._super_expand()
            
            # Extract
            print("→ Extracting content...")
            product_data['설명'] = self._extract_description()
            product_data['특징 및 장점'] = self._extract_features_from_benefits()
            product_data['기술 정보'] = self._extract_technical_info()
            product_data['구성/추천'] = self._extract_composition()
            product_data['관리 지침'] = self._extract_care()
            
            # Results
            if self.debug:
                print("\n📊 Results:")
                for key, value in product_data.items():
                    if key != 'URL':
                        status = "✓" if value else "✗"
                        print(f"  {status} {key}: {len(value) if value else 0} chars")
                        if value:
                            print(f"      → {value[:80].replace(chr(10), ' ')}...")
            
            print(f"\n✅ Done: {product_data['상품명']}")
            return product_data
            
        except Exception as e:
            print(f"❌ Error: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            return None
    
    def _super_expand(self):
        """SUPER AGGRESSIVE expansion - click EVERYTHING"""
        try:
            # Scroll to content
            self.driver.execute_script("window.scrollTo(0, 1000);")
            time.sleep(2)
            
            # Click all accordion buttons (for 기술 정보)
            accordion_selectors = [
                "button[class*='accordion']",
                "button[class*='vp-accordion']",
                "[class*='accordion__item-header']",
                "button[id*='accordion']"
            ]
            
            for selector in accordion_selectors:
                try:
                    buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if self.debug:
                        print(f"  Found {len(buttons)} buttons with selector: {selector}")
                    for btn in buttons:
                        try:
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                            time.sleep(0.2)
                            self.driver.execute_script("arguments[0].click();", btn)
                            time.sleep(0.3)
                        except:
                            pass
                except:
                    pass
            
            # Click all h2 tags
            h2s = self.driver.find_elements(By.TAG_NAME, 'h2')
            for h2 in h2s:
                try:
                    self.driver.execute_script("arguments[0].click();", h2)
                    time.sleep(0.2)
                except:
                    pass
            
            # Click all buttons
            buttons = self.driver.find_elements(By.TAG_NAME, 'button')
            if self.debug:
                print(f"  Clicking {len(buttons)} total buttons...")
            for btn in buttons[:100]:  # Limit to first 100
                try:
                    self.driver.execute_script("arguments[0].click();", btn)
                    time.sleep(0.15)
                except:
                    pass
            
            # Full page scroll
            time.sleep(3)
            height = self.driver.execute_script("return document.body.scrollHeight")
            for i in range(0, height, 400):
                self.driver.execute_script(f"window.scrollTo(0, {i});")
                time.sleep(0.1)
            
            self.driver.execute_script("window.scrollTo(0, 1000);")
            time.sleep(3)
            
            print("  ✓ Super expansion complete")
            
        except Exception as e:
            if self.debug:
                print(f"  ⚠️ Expansion error: {e}")
    
    def _extract_description(self):
        """Extract 설명"""
        try:
            if self.debug:
                print("  → 설명")
            
            h2s = self.driver.find_elements(By.TAG_NAME, 'h2')
            for h2 in h2s:
                text = self.driver.execute_script("return arguments[0].textContent;", h2)
                if '설명' in text:
                    script = """
                    var h2 = arguments[0];
                    var results = [];
                    var current = h2.nextElementSibling;
                    while (current) {
                        if (current.tagName === 'H2') break;
                        if (current.tagName === 'H3') {
                            results.push(current.textContent.trim());
                        }
                        var h3s = current.getElementsByTagName('h3');
                        for (var i = 0; i < h3s.length; i++) {
                            results.push(h3s[i].textContent.trim());
                        }
                        current = current.nextElementSibling;
                    }
                    return results;
                    """
                    h3_texts = self.driver.execute_script(script, h2)
                    if h3_texts:
                        content = '\n'.join([t for t in h3_texts if len(t) > 10])[:1000]
                        if self.debug and content:
                            print(f"     ✓ {len(content)} chars")
                        return content
            return ""
        except:
            return ""
    
    def _extract_features_from_benefits(self):
        """Extract 특징 및 장점 from benefits wrapper"""
        try:
            if self.debug:
                print("  → 특징 및 장점")
            
            # Find wrapper
            wrapper = self.driver.find_element(By.CSS_SELECTOR, '[data-testid="product-benefits-wrapper"]')
            
            # Find h2 with 특징
            h2s = wrapper.find_elements(By.TAG_NAME, 'h2')
            for h2 in h2s:
                text = self.driver.execute_script("return arguments[0].textContent;", h2)
                if '특징' in text:
                    script = """
                    var h2 = arguments[0];
                    var results = [];
                    var current = h2.nextElementSibling;
                    while (current) {
                        if (current.tagName === 'H2') break;
                        var text = current.textContent.trim();
                        if (text && text.length > 10) {
                            results.push(text);
                        }
                        current = current.nextElementSibling;
                    }
                    return results;
                    """
                    contents = self.driver.execute_script(script, h2)
                    if contents:
                        result = '\n'.join(contents)[:1000]
                        if self.debug and result:
                            print(f"     ✓ {len(result)} chars")
                        return result
            return ""
        except:
            return ""
    
    def _extract_technical_info(self):
        """Extract 기술 정보 from accordion items"""
        try:
            if self.debug:
                print("  → 기술 정보 (from accordions)")
            
            # Find additionalinfo-popup
            try:
                popup = self.driver.find_element(By.CSS_SELECTOR, '[data-testid="additionalinfo-popup"]')
            except:
                # Fallback: look for accordion items anywhere
                popup = self.driver.find_element(By.TAG_NAME, 'body')
            
            # Find all accordion panels (expanded content)
            panels = popup.find_elements(By.CSS_SELECTOR, '[class*="accordion__item-panel"]')
            
            tech_items = []
            for panel in panels:
                try:
                    text = self.driver.execute_script("return arguments[0].textContent;", panel).strip()
                    if text and len(text) > 10:
                        tech_items.append(text)
                except:
                    pass
            
            if tech_items:
                result = '\n'.join(tech_items)[:1000]
                if self.debug:
                    print(f"     ✓ {len(tech_items)} accordion items, {len(result)} chars")
                return result
            
            # Fallback: Get from benefit rows
            try:
                wrapper = self.driver.find_element(By.CSS_SELECTOR, '[data-testid="product-benefits-wrapper"]')
                rows = wrapper.find_elements(By.CSS_SELECTOR, '[data-testid^="benefit-row-"]')
                items = []
                for row in rows:
                    text = self.driver.execute_script("return arguments[0].textContent;", row).strip()
                    if text and len(text) > 5:
                        items.append(text)
                if items:
                    result = '\n'.join(items)[:1000]
                    if self.debug:
                        print(f"     ✓ {len(items)} benefit rows, {len(result)} chars")
                    return result
            except:
                pass
            
            return ""
        except:
            return ""
    
    def _extract_composition(self):
        """Extract 구성/추천 from css-1ka3tud and similar divs"""
        try:
            if self.debug:
                print("  → 구성/추천")
            
            # Find h2 with 구성
            h2s = self.driver.find_elements(By.TAG_NAME, 'h2')
            for h2 in h2s:
                text = self.driver.execute_script("return arguments[0].textContent;", h2)
                if '구성' in text or '추천' in text:
                    # Get ALL following content
                    script = """
                    var h2 = arguments[0];
                    var results = [];
                    var current = h2.nextElementSibling;
                    while (current) {
                        if (current.tagName === 'H2') break;
                        var text = current.textContent.trim();
                        if (text && text.length > 10) {
                            results.push(text);
                        }
                        current = current.nextElementSibling;
                    }
                    return results;
                    """
                    contents = self.driver.execute_script(script, h2)
                    if contents:
                        result = '\n'.join(contents)[:1000]
                        if self.debug and result:
                            print(f"     ✓ {len(result)} chars")
                        return result
            
            # Fallback: Look for specific CSS classes
            try:
                divs = self.driver.find_elements(By.CSS_SELECTOR, '.css-1ka3tud, .css-xb0py4, .css-ksmov6')
                texts = []
                for div in divs:
                    text = self.driver.execute_script("return arguments[0].textContent;", div).strip()
                    if text and len(text) > 10:
                        texts.append(text)
                if texts:
                    result = '\n'.join(texts)[:1000]
                    if self.debug:
                        print(f"     ✓ {len(result)} chars from CSS classes")
                    return result
            except:
                pass
            
            return ""
        except:
            return ""
    
    def _extract_care(self):
        """Extract 관리 지침"""
        try:
            if self.debug:
                print("  → 관리 지침")
            
            body = self.driver.find_element(By.TAG_NAME, 'body').text
            pattern = r'(드라이 클리닝.*?표백제.*?사용금지)'
            matches = re.findall(pattern, body, re.DOTALL)
            if matches:
                result = matches[0].strip()[:500]
                if self.debug:
                    print(f"     ✓ {len(result)} chars")
                return result
            return ""
        except:
            return ""
    
    def _extract_basic_info(self):
        """Extract basic info"""
        info = {}
        
        try:
            match = re.search(r'(\d+)\.html$', self.driver.current_url)
            info['상품ID'] = match.group(1) if match else ''
        except:
            info['상품ID'] = ''
        
        try:
            h1 = self.driver.find_element(By.TAG_NAME, 'h1')
            info['상품명'] = self.driver.execute_script("return arguments[0].textContent;", h1).strip()
            if not info['상품명']:
                info['상품명'] = self.driver.title.split('|')[0].strip()
        except:
            info['상품명'] = self.driver.title.split('|')[0].strip()
        
        try:
            name_lower = info['상품명'].lower()
            url_lower = self.driver.current_url.lower()
            brands = {'QUECHUA': ['quechua'], 'KIPRUN': ['kiprun'], 
                     'KALENJI': ['kalenji'], 'FORCLAZ': ['forclaz'], 
                     'SIMOND': ['simond']}
            for brand, keywords in brands.items():
                if any(kw in name_lower or kw in url_lower for kw in keywords):
                    info['브랜드'] = brand
                    break
            if not info.get('브랜드'):
                info['브랜드'] = 'DECATHLON'
        except:
            info['브랜드'] = ''
        
        return info
    
    def crawl_products(self, urls, output='data/products_korean.json'):
        """Crawl and save"""
        products = []
        
        for i, url in enumerate(urls, 1):
            print(f"\n{'#'*80}")
            print(f"[{i}/{len(urls)}]")
            print(f"{'#'*80}")
            
            data = self.extract_product_info(url)
            if data:
                products.append(data)
            
            if i < len(urls):
                time.sleep(3)
        
        if products:
            import os
            os.makedirs('data', exist_ok=True)
            
            with open(output, 'w', encoding='utf-8') as f:
                json.dump(products, f, ensure_ascii=False, indent=2)
            
            print(f"\n💾 Saved: {output}")
            print(f"\n📊 Summary:")
            for field in ['설명', '특징 및 장점', '기술 정보', '구성/추천', '관리 지침']:
                count = sum(1 for p in products if p.get(field))
                print(f"  {field}: {count}/{len(products)}")
        
        return products
    
    def close(self):
        self.driver.quit()


def main():
    URLS = [
        
"https://www.decathlon.co.kr/p/여성-러닝-윈드-베스트-런-500-kiprun-8928640.html",
  "https://www.decathlon.co.kr/p/0370a64d-c6a3-49ca-9c91-70beca669726_남성-백팩킹-방풍발수-바지-mt900-simond-8852944.html",
  "https://www.decathlon.co.kr/p/0af2cade-091e-48b9-9799-3b7ac16b677b_남성-러닝-반팔-티-런-드라이-500-kiprun-8861547.html",
  "https://www.decathlon.co.kr/p/0d53ca2b-9e85-4d5a-9aff-b59a3deeaa9e_여성-3인치-러닝-경량-쇼츠-런-드라이-500-kiprun-8911355.html",
  "https://www.decathlon.co.kr/p/0e661008-65f4-4a76-aec0-5588dd141cd8_남성-하프집-러닝-긴팔-티-런-월-100-kalenji-8487923.html",
  "https://www.decathlon.co.kr/p/11e08502-12db-499e-ad2a-22a2136d4e4d_남성-러닝-반팔-티-런-드라이-500-kiprun-8861544.html",
  "https://www.decathlon.co.kr/p/157f0374-3cd1-4f47-8ca8-41893bc7d6ee_남성-러닝-반팔-티-런-드라이-그라프-500-kiprun-8842526.html",
  "https://www.decathlon.co.kr/p/16f96ea3-dade-4404-8caa-fae89d1aab80_러닝-보온-헤드밴드-런-월-kiprun-8342130.html",
  "https://www.decathlon.co.kr/p/1c2a73e6-2d84-4c91-89ab-f063eadd9a65_남성-6인치-러닝-쇼츠-컴포트-500-브리프-내장-kiprun-8588345.html",
  "https://www.decathlon.co.kr/p/1c444771-5de8-4908-9d35-d696b00f92bf_남성-하이킹-반팔-티-mh100-quechua-8316244.html",
  "https://www.decathlon.co.kr/p/1e9eca5e-07e5-40a4-81c3-3f504704c3b2_등산-백팩-20l-아르페나즈-nh100-quechua-8529024.html",
  "https://www.decathlon.co.kr/p/1ab57afe-c525-40f7-8c89-37dbe6237c3a_남성-러닝-패딩-베스트-런-월-500-kiprun-8911507.html",
  "https://www.decathlon.co.kr/p/22d6f249-14a3-4fbd-9325-c912450e22a5_남성-백팩킹-투인원-집오프-바지-mt100-forclaz-8666242.html",
  "https://www.decathlon.co.kr/p/26a11ae7-44ab-4be8-bb01-c419080201ca_여성-러닝-반팔-티-런-드라이-500-kiprun-8831477.html",
  "https://www.decathlon.co.kr/p/28b9e294-9042-4eb8-8260-eaca149b8855_남성-3인치-러닝-쇼츠-500-스플릿-브리프-내장-kiprun-8861551.html",
  "https://www.decathlon.co.kr/p/2abcfaa3-f77c-4064-a6ca-a24efab5b68c_남성-하이킹-윈드-재킷-헬륨-900-quechua-8862055.html",
  "https://www.decathlon.co.kr/p/374ef037-3be4-4ca5-94dc-b31acfe2e461_여성-백팩킹-바지-mt500-simond-8608070.html",
  "https://www.decathlon.co.kr/p/37cb9912-7e97-40e5-bab7-e4229728003f_남성-러닝-바지-런-드라이-100-kiprun-8882067.html",
  "https://www.decathlon.co.kr/p/3b0d88ba-e9a4-448f-88a8-4858f374c139_등산-백팩-20l-아르페나즈-nh100-quechua-8529019.html",
  "https://www.decathlon.co.kr/p/45fb8bb9-881a-48ff-8d0a-bf771292d472_등산-백팩-38l-mh500-quechua-8916236.html",
  "https://www.decathlon.co.kr/p/518712c5-981e-44c5-ad49-c16a6dd774a7_여성-러닝-윈드-재킷-런-100-kiprun-8885914.html",
  "https://www.decathlon.co.kr/p/5a0beee3-2295-4f65-8a4c-0999657f9031_남성-러닝-경량-싱글렛-900-울트라라이트-kiprun-8872861.html",
  "https://www.decathlon.co.kr/p/60949031-4af0-4554-a305-ddb06765d40c_여성-백팩킹-투인원-집오프-바지-mt100-forclaz-8544763.html",
  "https://www.decathlon.co.kr/p/63dda9dc-1ec7-4ae2-a7a8-43b64510c9d2_여성-러닝-반팔-티-런-드라이-100-kalenji-8817407.html",
  "https://www.decathlon.co.kr/p/647ebfbc-2346-4902-ae31-b7c7055282c3_러닝-스마트폰-벨트-베이직-2-kiprun-8648869.html",
  "https://www.decathlon.co.kr/p/66e6305f-bae3-4b53-987f-d1acfea14765_남성-러닝-싱글렛-런-드라이-100-kalenji-8488395.html",
  "https://www.decathlon.co.kr/p/69570cd7-b03c-4d61-9d3a-c2706ede7792_남성-하이킹-투인원-집오프-바지-mh100-quechua-8652204.html",
  "https://www.decathlon.co.kr/p/72a8e3b8-164b-44bc-a811-356238ee4bd5_여성-메리노울-백팩킹-긴팔-베이스-레이어-트래블-100-simond-8316437.html",
  "https://www.decathlon.co.kr/p/78255631-e894-4b45-968e-e862446468b5_남성-백팩킹-바지-mt500-simond-8916623.html",
  "https://www.decathlon.co.kr/p/7a06b69b-1432-4636-94d7-04485f2cd01e_남성-8인치-러닝-경량-쇼츠-런-드라이-플러스-500-kiprun-8751038.html",
  "https://www.decathlon.co.kr/p/842391c4-8e4f-4217-94bc-fe320e322db4_남성-메리노울-백팩킹-하프집-베이스-레이어-mt900-simond-8609386.html",
  "https://www.decathlon.co.kr/p/8688ef4f-d574-440a-b3ef-231842e602ea_남성-러닝-긴팔-티-런-드라이-500-kiprun-8817439.html",
  "https://www.decathlon.co.kr/p/8b8d0e98-de53-4ba7-9ad2-16474b941936_러닝-소프트-플라스크-물병-250ml-kiprun-8605519.html",
  "https://www.decathlon.co.kr/p/9464dd98-1793-40d1-987e-dd934bd58cb8_여성-러닝-경량-싱글렛-런-900-kiprun-8892090.html",
  "https://www.decathlon.co.kr/p/97ed0307-47c3-416f-98d6-6407f3893c5c_여성-러닝-바지-런-드라이-100-kiprun-8736665.html",
  "https://www.decathlon.co.kr/p/9986c3b3-e998-48b7-bf2d-d75e9eed248f_여성-러닝-윈드-재킷-런-100-kiprun-8817239.html",
  "https://www.decathlon.co.kr/p/9a453ff5-8055-4400-b156-201e43e38666_러닝-단목-양말-3컬레-런100-kiprun-8296177.html",
  "https://www.decathlon.co.kr/p/9b182817-c4ab-4e29-917b-23bb73e1b4c3_여성-하프집-러닝-긴팔-티-런-월-100-kalenji-8966974.html",
  "https://www.decathlon.co.kr/p/a251aef8-9f6c-4980-89fc-40651c666eda_경량-트레일러닝-베스트-5l-kiprun-8786242.html",
  "https://www.decathlon.co.kr/p/afbc3caf-dd14-491c-a61a-c903a9829acd_러닝-중목-양말-2컬레-파인-런-500-kiprun-8810971.html",
  "https://www.decathlon.co.kr/p/b02449e6-3ce1-49e1-8e7f-b73344cee8aa_남성-러닝-바지-월-100-kalenji-8807977.html",
  "https://www.decathlon.co.kr/p/b11531eb-3d4b-440a-889f-8a84b6f925e2_남성-카본-레이싱화-kd900x-2-kiprun-8915926.html",
  "https://www.decathlon.co.kr/p/b1d25295-0c02-4803-b387-f8fc64e1348d_남성-경량-하이킹-레인-재킷-mh500-quechua-8785247.html",
  "https://www.decathlon.co.kr/p/b4ee8d94-47c4-4899-a20f-d9ef0822b9cb_여성-4인치-러닝-쇼츠-런-드라이-100-kalenji-8926957.html",
  "https://www.decathlon.co.kr/p/b84bff5f-b87c-49a7-a193-5da9350e076d_남성-하프집-러닝-긴팔-티-런-드라이-500-kiprun-8902771.html",
  "https://www.decathlon.co.kr/p/bb27c120-85e5-4aa3-b932-1165e668d206_여성-4인치-러닝-쇼츠-런-드라이-100-kalenji-8553338.html",
  "https://www.decathlon.co.kr/p/c453cd06-5df2-4339-817b-8b04f9d696b4_백팩킹-오거나이저-백팩-40l-트래블-500-forclaz-8735937.html",
  "https://www.decathlon.co.kr/p/cb734175-9638-4771-b508-739373a08ba5_러닝-캡-모자-v2-kiprun-8871357.html",
  "https://www.decathlon.co.kr/p/c9a96ac6-db5c-499a-b9d0-3f9c8ca6eb58_여성-3인치-러닝-경량-쇼츠-런-드라이-500-kiprun-8852986.html",
  "https://www.decathlon.co.kr/p/d1933221-eb61-4a4a-8232-93c5a84e1de4_러닝-장갑-에볼루티브-v2-kiprun-8759614.html",
  "https://www.decathlon.co.kr/p/d660897b-e5ca-4e60-9338-05faeef6d3ad_남성-하이킹-바지-스트레치-mh500-quechua-8917639.html",
  "https://www.decathlon.co.kr/p/daf64b1f-0b1c-417c-a7f9-9d069921978a_남성-6인치-러닝-쇼츠-컴포트-500-브리프-내장-kiprun-8903143.html",
  "https://www.decathlon.co.kr/p/defe484d-e226-493c-836c-e86054a151bc_남성-러닝-윈드-재킷-런-100-kiprun-8926453.html",
  "https://www.decathlon.co.kr/p/dfa61a9f-76ce-4c1e-8e6b-77b21c2c6412_백팩킹-오거나이저-백팩-40l-트래블-500-forclaz-8787845.html",
  "https://www.decathlon.co.kr/p/d992b8f1-60e6-47df-b4ff-f99a47f777d1_남성-7인치-러닝-쇼츠-런-드라이-100-kalenji-8817443.html",
  "https://www.decathlon.co.kr/p/e11f887f-8a26-411a-bfe2-8cd95d93d1b2_남성-백팩킹-카고-바지-트래블-500-forclaz-8572546.html",
  "https://www.decathlon.co.kr/p/e8c0293c-d644-4b64-80d8-29c7440a3318_남성-8인치-러닝-투인원-쇼츠-런-드라이-550-kalenji-8772968.html",
  "https://www.decathlon.co.kr/p/e958cb2a-c0fa-4b1a-b887-3eab43461456_남성-러닝-바지-슬림핏-런-드라이-500-kiprun-8519080.html",
  "https://www.decathlon.co.kr/p/e95ec1f5-6642-4a64-af23-4a151a1465b8_여성-러닝-보온-레깅스-런-월-100-kiprun-8757546.html",
  "https://www.decathlon.co.kr/p/ee0af98b-a7b8-4e66-8ac2-341e7253dcd8_러닝-소프트-플라스크-물병-500ml-kiprun-8605419.html",
  "https://www.decathlon.co.kr/p/ee8555b6-1e4b-49fd-9db3-c0adc196f050_남성-경량-하이킹-레인-재킷-mh500-quechua-8612171.html",
  "https://www.decathlon.co.kr/p/f04856df-ea90-4431-9a24-ab143ec9a486_남성-러닝-반팔-티-런-드라이-100-decathlon-8488034.html",
  "https://www.decathlon.co.kr/p/f1363e08-082e-4eb2-b254-d51e1c40f67d_등산-백팩-25l-mh500-quechua-8916234.html",
  "https://www.decathlon.co.kr/p/fad14080-c9b8-429c-97a0-fd1644c06ed2_여성-러닝화-쿠션-500-kiprun-8914009.html",
  "https://www.decathlon.co.kr/p/남성-러닝화-kd900-kiprun-8798231.html",
  "https://www.decathlon.co.kr/p/남성-러닝화-조그플로우-500k-1-kalenji-8670209.html",
  "https://www.decathlon.co.kr/p/남성-카본-레이싱화-kd900x-2-kiprun-8915926.html"
    
    
    ]
    print("""
╔══════════════════════════════════════════════════════════╗
║   Decathlon Crawler - TRULY FINAL VERSION               ║
║   With accordion expansion for 기술 정보                 ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    crawler = DecathlonTrulyFinalCrawler(debug=True)
    
    try:
        crawler.crawl_products(URLS)
    finally:
        crawler.close()


if __name__ == "__main__":
    main()