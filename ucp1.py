from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from pymongo import MongoClient
import requests
import certifi
import random
import time
import re

# ==========================================
# 1. KONEKSI MONGODB
# ==========================================
client = MongoClient('mongodb+srv://aryabagas23:puong206@praktikum.jofjat5.mongodb.net/?appName=praktikum', tlsCAFile=certifi.where())
collections = client['ucp1']['CNBCIndo']

def crawl_cnbc_hybrid():
    print("🤖 Mempersiapkan Robot Browser (Selenium)...")
    
    # Setting agar Chrome berjalan di "belakang layar" (Headless) tanpa membuka jendela mengganggu
    chrome_options = Options()
    chrome_options.add_argument('--headless=new') 
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--log-level=3') # Menyembunyikan pesan error internal browser
    
    # Otomatis mendownload dan mencocokkan versi Chrome Anda
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    base_url = 'https://www.cnbcindonesia.com/search?query=Environmental+Sustainability'
    headers_requests = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    max_page = 3  # Kita coba 3 halaman dulu
    page = 1
    
    print("\n--- Memulai Proses Crawling Hybrid CNBC Indonesia ---")

    while page <= max_page:
        search_url = f'{base_url}&p={page}'
        print(f'\n📄 [SELENIUM] Membuka Halaman Pencarian {page}...')
        
        # Menyuruh robot Chrome membuka URL
        driver.get(search_url)
        
        # INI KUNCINYA: Tunggu 5 detik agar JavaScript CNBC selesai menggambar kotak beritanya
        print("⏳ Menunggu JavaScript memuat berita...")
        time.sleep(5) 
        
        # Ambil HTML yang SUDAH MATANG (sudah dieksekusi JavaScript)
        html_matang = driver.page_source
        soup = BeautifulSoup(html_matang, 'html.parser')
        
        all_links = soup.find_all('a', href=True)
        list_url_berita = []

        # Menyaring tautan berita
        for a in all_links:
            href = a['href']
            if "cnbcindonesia.com" in href and re.search(r'\d{8,}', href):
                if href not in list_url_berita:
                    list_url_berita.append(href)

        if not list_url_berita:
            print('❌ Tidak ada link artikel ditemukan. Lanjut ke halaman berikutnya.')
            page += 1
            continue

        print(f"🔍 Ditemukan {len(list_url_berita)} link artikel. Memulai ekstraksi isi (Requests)...")

        for url in list_url_berita:
            try:
                # Cek DB agar tidak dobel
                if collections.find_one({'url': url}):
                    print(f"⏩ Dilewati (Sudah ada): {url}")
                    continue

                # KITA KEMBALI MENGGUNAKAN REQUESTS UNTUK ISI BERITA AGAR SUPER CEPAT
                isi_res = requests.get(url, headers=headers_requests, timeout=15)
                isi_soup = BeautifulSoup(isi_res.text, 'html.parser')

                judul_tag = isi_soup.find('h1')
                judul = judul_tag.text.strip() if judul_tag else 'Judul tidak ditemukan'

                tanggal_tag = isi_soup.find('div', class_='date')
                tanggal = tanggal_tag.text.strip() if tanggal_tag else 'Tanggal tidak ditemukan'

                author_tag = isi_soup.find('div', class_='author')
                author = author_tag.text.strip() if author_tag else 'Author tidak ditemukan'

                tags_meta = isi_soup.find('meta', attrs={'name': 'keywords'})
                tags = tags_meta['content'].strip() if tags_meta else 'Tag tidak ditemukan'

                thumbnail_meta = isi_soup.find('meta', attrs={'property': 'og:image'})
                thumbnail = thumbnail_meta['content'].strip() if thumbnail_meta else 'Thumbnail tidak ditemukan'

                body_content = isi_soup.find('div', class_='detail_text')
                isi_berita = 'Isi tidak ditemukan'
                
                if body_content:
                    isi_paragraf_list = [p.get_text(strip=True) for p in body_content.find_all('p') if p.get_text(strip=True)]
                    if isi_paragraf_list:
                        isi_berita = ' '.join(isi_paragraf_list)

                data_final = {
                    'url': url,
                    'judul': judul,
                    'tanggal_publish': tanggal,
                    'author': author,
                    'tag_kategori': tags,
                    'isi_berita': isi_berita,
                    'thumbnail': thumbnail
                }

                collections.insert_one(data_final)
                print(f'✅ Tersimpan: {judul[:60]}...')

                time.sleep(random.uniform(1.0, 2.0)) 

            except Exception as e:
                print(f'❌ Error pada {url}: {e}')

        page += 1

    # Matikan robot setelah selesai bekerja
    driver.quit()
    print("\n--- Crawling Selesai! ---")

if __name__ == "__main__":
    crawl_cnbc_hybrid()