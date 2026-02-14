import sys
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone, timedelta
import time
import re
import os

# === KONFIGURACE FEEDŮ ===
FEEDS_CONFIG = {
    "lego-speed": {
        "url": "https://www.vinted.cz/catalog?search_text=lego%20speed&price_to=450.0&currency=CZK&order=newest_first",
        "title": "LEGO Speed Champions",
        "description": "LEGO Speed Champions do 450 Kč",
        "cache_file": "cache/lego_speed.json",
        "feed_file": "docs/lego_speed.xml"
    },
    "lego-technic-mix": {
        "url": "https://www.vinted.cz/catalog?search_text=technic%20mix&catalog[]=1767&search_id=27058343250&order=newest_first",
        "title": "LEGO Technic mix ",
        "description": "LEGO Technic mix",
        "cache_file": "cache/lego_technic_mix.json",
        "feed_file": "docs/lego_technic_mix.xml"
    },
    "lego-duplo": {
        "url": "https://www.vinted.cz/catalog?search_text=&catalog[]=1767&brand_ids[]=328531&search_id=26854064724&order=newest_first",
        "title": "LEGO Duplo",
        "description": "LEGO Duplo",
        "cache_file": "cache/lego_duplo.json",
        "feed_file": "docs/lego_duplo.xml"
    },

    "lego-technic": {
        "url": "https://www.vinted.cz/catalog?search_text=lego%20technic&price_from=50.0&currency=CZK&search_id=20000401975&order=newest_first",
        "title": "LEGO Technic",
        "description": "LEGO Technic",
        "cache_file": "cache/lego_technic.json",
        "feed_file": "docs/lego_technic.xml"
    },
    "lego-kg": {
        "url": "https://www.vinted.cz/catalog?search_text=lego%20kg&price_from=50.0&currency=CZK&search_id=20549846549&order=newest_first",
        "title": "LEGO KG",
        "description": "LEGO KG",
        "cache_file": "cache/lego_kg.json",
        "feed_file": "docs/lego_kg.xml"
    },

    "lego-technic-kat": {
        "url": "https://www.vinted.cz/catalog?search_text=&catalog[]=1767&brand_ids[]=407093&search_id=21855804981&order=newest_first",
        "title": "LEGO Technic kat",
        "description": "LEGO tehnic kat",
        "cache_file": "cache/lego_technic_kat.json",
        "feed_file": "docs/lego_technic_kat.xml"
    },
    "lego-mix": {
        "url": "https://www.vinted.cz/catalog?search_text=lego%20mix&search_id=23708556687&order=newest_first",
        "title": "LEGO mix",
        "description": "LEGO mix",
        "cache_file": "cache/lego_mix.json",
        "feed_file": "docs/lego_mix.xml"
    },
    "lego-200-300": {
        "url": "https://www.vinted.cz/catalog?search_text=&catalog[]=1767&price_from=200.0&price_to=300.0&currency=CZK&brand_ids[]=89162&search_id=30666696637&order=newest_first",
        "title": "LEGO 200-300",
        "description": "LEGO 200 300",
        "cache_file": "cache/lego_200_300.json",
        "feed_file": "docs/lego_200_300.xml"
    },

    "lego-kat": {
        "url": "https://www.vinted.cz/catalog?search_text=&catalog[]=1767&brand_ids[]=89162&search_id=30177685542&order=newest_first",
        "title": "LEGO kat",
        "description": "LEGO kat",
        "cache_file": "cache/lego_kat.json",
        "feed_file": "docs/lego_kat.xml"
    },






# Přidej další feedy zde...
}

MAX_POLOZEK = 300
MAZAT_STARSI_NEZ_DNI = 30


class VintedRSSGenerator:
    def __init__(self, feed_name):
        if feed_name not in FEEDS_CONFIG:
            print(f"❌ Feed '{feed_name}' neexistuje!")
            sys.exit(1)
        
        self.config = FEEDS_CONFIG[feed_name]
        self.vinted_url = self.config["url"]
        self.cache_file = self.config["cache_file"]
        self.feed_file = self.config["feed_file"]
        self.feed_title = self.config["title"]
        self.feed_description = self.config["description"]
        
        # Vytvoř složky
        os.makedirs('cache', exist_ok=True)
        os.makedirs('docs', exist_ok=True)
    
    def nacti_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    print(f"📂 Načteno {len(data)} položek z cache")
                    return data
            except Exception as e:
                print(f"⚠️ Chyba při načítání cache: {e}")
                return {}
        else:
            print("📂 Cache soubor neexistuje, vytvářím nový")
            return {}
    
    def uloz_cache(self, data):
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾 Uloženo {len(data)} položek do cache")
    
    def vycisti_stare_polozky(self, cache, max_stari_dnu):
        if not cache:
            return cache
        
        now = datetime.now(timezone.utc)
        pocet_pred = len(cache)
        
        nove_cache = {}
        for url, item in cache.items():
            datum_str = item.get('datum_pridani')
            if datum_str:
                try:
                    datum = datetime.fromisoformat(datum_str)
                    stari = now - datum
                    if stari.days <= max_stari_dnu:
                        nove_cache[url] = item
                except:
                    nove_cache[url] = item
            else:
                nove_cache[url] = item
        
        smazano = pocet_pred - len(nove_cache)
        if smazano > 0:
            print(f"🗑️ Odstraněno {smazano} položek starších než {max_stari_dnu} dní")
        
        return nove_cache
    
    def je_reklama(self, link):
        parent = link.parent
        for level in range(10):
            if parent is None:
                break
            
            parent_classes = parent.get('class', [])
            if parent_classes:
                classes_str = ' '.join(parent_classes)
                if 'closet' in classes_str.lower():
                    return True
            
            parent = parent.parent
        
        return False
    
    def scrapuj_vinted(self):
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        chrome_options.add_argument('--window-size=1920,1080')
        
        # Pro GitHub Actions
        if os.environ.get('GITHUB_ACTIONS'):
            chrome_options.add_argument('--disable-software-rasterizer')
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        items = []
        preskoceno_reklam = 0
        
        try:
            print(f"📦 Načítám: {self.feed_title}")
            driver.get(self.vinted_url)
            
            time.sleep(5)
            
            try:
                cookie_button = driver.find_element(By.ID, "onetrust-accept-btn-handler")
                cookie_button.click()
                time.sleep(2)
            except:
                pass
            
            print("📜 Scrolluji...")
            last_height = driver.execute_script("return document.body.scrollHeight")
            
            for i in range(8):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
            
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            item_links = soup.find_all('a', href=re.compile(r'/items/\d+'))
            print(f"🔍 Analyzuji {len(item_links)} položek...")
            
            zpracovane_urls = set()
            
            for link in item_links:
                href = link.get('href', '')
                full_url = f"https://www.vinted.cz{href}" if href.startswith('/') else href
                
                if full_url in zpracovane_urls:
                    continue
                zpracovane_urls.add(full_url)
                
                if self.je_reklama(link):
                    preskoceno_reklam += 1
                    continue
                
                item = {}
                item['url'] = full_url
                
                full_title = link.get('title') or link.get('aria-label') or ''
                
                if full_title:
                    title_match = re.match(r'^(.+?),\s*značka:', full_title)
                    if title_match:
                        item['title'] = title_match.group(1).strip()
                    else:
                        title_match = re.match(r'^(.+?),\s*\d+', full_title)
                        if title_match:
                            item['title'] = title_match.group(1).strip()
                        else:
                            item['title'] = full_title.split(',')[0].strip()
                    
                    brand_match = re.search(r'značka:\s*([^,]+)', full_title)
                    if brand_match:
                        item['brand'] = brand_match.group(1).strip()
                    
                    condition_match = re.search(r'stav:\s*([^,]+)', full_title)
                    if condition_match:
                        item['condition'] = condition_match.group(1).strip()
                    
                    size_match = re.search(r'velikost:\s*([^,]+)', full_title)
                    if size_match:
                        item['size'] = size_match.group(1).strip()
                    
                    price_match = re.search(r'(\d+[,\s]?\d*)\s*Kč', full_title)
                    if price_match:
                        item['price'] = f"{price_match.group(1)} Kč"
                
                container = link.find_parent('div', class_=re.compile(r'feed-grid|ItemBox|styles_container'))
                if not container:
                    container = link.parent
                
                if container:
                    img = container.find('img')
                    if img:
                        src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                        if src and 'placeholder' not in src.lower() and src.startswith('http'):
                            item['img'] = src
                        else:
                            srcset = img.get('srcset')
                            if srcset:
                                first_src = srcset.split(',')[0].split()[0]
                                if first_src.startswith('http'):
                                    item['img'] = first_src
                
                if item.get('title') and len(item['title']) > 5:
                    items.append(item)
            
            print(f"✅ Načteno {len(items)} položek")
            if preskoceno_reklam > 0:
                print(f"🚫 Přeskočeno {preskoceno_reklam} reklam")
            
        except Exception as e:
            print(f"❌ Chyba: {e}")
            
        finally:
            driver.quit()
        
        return items
    
    def sluc_polozky(self, cache, nove_polozky):
        now = datetime.now(timezone.utc).isoformat()
        
        pridano = 0
        aktualizovano = 0
        
        for item in nove_polozky:
            url = item['url']
            
            if url not in cache:
                item['datum_pridani'] = now
                item['posledni_videno'] = now
                cache[url] = item
                pridano += 1
            else:
                cache[url]['posledni_videno'] = now
                if item.get('price') and item['price'] != cache[url].get('price'):
                    cache[url]['price'] = item['price']
                    aktualizovano += 1
        
        if pridano > 0:
            print(f"➕ Přidáno {pridano} nových")
        if aktualizovano > 0:
            print(f"🔄 Aktualizováno {aktualizovano}")
        
        return cache
    
    def oznac_nedostupne(self, cache, aktualni_url_list):
        aktualni_urls = set(aktualni_url_list)
        
        oznaceno = 0
        for url, item in cache.items():
            if url not in aktualni_urls:
                if not item.get('nedostupne'):
                    item['nedostupne'] = True
                    oznaceno += 1
            else:
                if item.get('nedostupne'):
                    item['nedostupne'] = False
        
        if oznaceno > 0:
            print(f"⚠️ {oznaceno} nedostupných")
        
        return cache
    
    def generuj_feed(self, cache):
        fg = FeedGenerator()
        fg.title(f'Vinted - {self.feed_title}')
        fg.link(href=self.vinted_url)
        fg.description(self.feed_description)
        fg.language('cs')
        fg.lastBuildDate(datetime.now(timezone.utc))
        
        sorted_items = sorted(
            cache.values(),
            key=lambda x: x.get('datum_pridani', ''),
            reverse=True
        )[:MAX_POLOZEK]
        
        added_count = 0
        for item in sorted_items:
            title = item.get('title', '').strip()
            if not title or len(title) < 5:
                continue
            
            price = item.get('price', 'Cena neuvedena')
            nedostupne = item.get('nedostupne', False)
            
            fe = fg.add_entry()
            
            if nedostupne:
                fe.title(f"[PRODÁNO?] {title} - {price}")
            else:
                fe.title(f"{title} - {price}")
            
            fe.link(href=item['url'])
            
            description = ""
            if nedostupne:
                description += '<p style="color: red;">⚠️ Možná nedostupné</p>'
            
            if item.get('img'):
                description += f'<img src="{item["img"]}" style="max-width: 400px;"><br>'
            
            description += f"<b>Cena:</b> {price}<br>"
            
            if item.get('brand'):
                description += f"<b>Značka:</b> {item['brand']}<br>"
            if item.get('condition'):
                description += f"<b>Stav:</b> {item['condition']}<br>"
            
            fe.description(description)
            fe.guid(item['url'])
            
            if item.get('datum_pridani'):
                try:
                    datum = datetime.fromisoformat(item['datum_pridani'])
                    fe.pubDate(datum)
                except:
                    fe.pubDate(datetime.now(timezone.utc))
            
            added_count += 1
        
        fg.rss_file(self.feed_file)
        print(f"📄 Feed: {self.feed_file} ({added_count} položek)")
        
        return added_count
    
    def run(self):
        print(f"\n{'='*40}")
        print(f"🚀 {self.feed_title}")
        print(f"{'='*40}")
        
        cache = self.nacti_cache()
        cache = self.vycisti_stare_polozky(cache, MAZAT_STARSI_NEZ_DNI)
        nove_polozky = self.scrapuj_vinted()
        
        if nove_polozky:
            cache = self.sluc_polozky(cache, nove_polozky)
            aktualni_urls = [item['url'] for item in nove_polozky]
            cache = self.oznac_nedostupne(cache, aktualni_urls)
        
        self.uloz_cache(cache)
        self.generuj_feed(cache)


def main():
    if len(sys.argv) > 1:
        feed_name = sys.argv[1]
        generator = VintedRSSGenerator(feed_name)
        generator.run()
    else:
        # Aktualizovat všechny
        for feed_name in FEEDS_CONFIG.keys():
            generator = VintedRSSGenerator(feed_name)
            generator.run()
            time.sleep(5)  # Pauza mezi feedy


if __name__ == "__main__":
    main()
