from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_cors import CORS
import logging
import functools
import re
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import requests
from bs4 import BeautifulSoup
import time

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('freeisland.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)
app.secret_key = 'freeisland-secret-key-2026'

# Configurações Supabase
SUPABASE_URL = "https://cnwrcrpihldqejyvgysn.supabase.co"
SUPABASE_KEY_SERVICE = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNud3JjcnBpaGxkcWVqeXZneXNuIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MTU5NzM3OSwiZXhwIjoyMDY3MTczMzc5fQ.GdZPPZvSAslVIgzbmq8rhstK94qxh7WUwH623GUvb4g"
SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY_SERVICE,
    "Authorization": f"Bearer {SUPABASE_KEY_SERVICE}",
    "Content-Type": "application/json"
}

# Credenciais de login
LOGIN_EMAIL = "gustavo.teodoro.fantini@gmail.com"
LOGIN_SENHA = "Gustavinho12."

# Linktree
LINKTREE_URL = "https://linktr.ee/freeisland"

def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

class FreeIslandScraper:
    def __init__(self):
        self.driver = None
        self.setup_driver()
    
    def setup_driver(self):
        """Configura o Selenium WebDriver"""
        options = Options()
        options.add_argument('--headless')  # Executar em modo headless
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            logger.info("WebDriver inicializado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao inicializar WebDriver: {e}")
            raise
    
    def identify_site(self, url):
        """Identifica o site pela URL"""
        from urllib.parse import urlparse
        
        parsed_url = urlparse(url.lower())
        domain = parsed_url.netloc
        full_url = url.lower()
        
        logger.info(f"Verificando URL: {url}")
        logger.info(f"Domínio extraído: {domain}")
        logger.info(f"URL completa: {full_url}")
        
        # Verificar no domínio e na URL completa
        magalu_domains = ['magazineluiza.com.br', 'magalu.com.br', 'magazineluiza.com', 'divulgador.magalu.com', 'magalu']
        
        if any(d in domain for d in ['mercadolivre.com', 'mercadolivre.com.br', 'ml.com.br', 'ml.com']):
            return 'mercadolivre'
        elif any(d in domain for d in ['amazon.com.br', 'amzn.to']):
            return 'amazon'
        elif any(d in domain for d in ['shopee.com.br', 's.shopee.com.br']):
            return 'shopee'
        elif any(d in domain for d in magalu_domains) or any(d in full_url for d in magalu_domains):
            logger.info(f"Magazine Luiza detectado: {domain}")
            return 'magazineluiza'
        
        logger.warning(f"Site não reconhecido para URL: {url} - Domínio: {domain}")
        return 'unknown'
    
    def clean_price(self, text):
        """Limpa e formata preço"""
        if not text:
            return None, None
        
        original = text.strip()
        logger.info(f"Processando preço: '{original}'")
        
        # Primeiro: normalizar quebras de linha e espaços múltiplos
        normalized = re.sub(r'[\n\r\s]+', '', text)
        
        # Limpar caracteres não numéricos, mantendo vírgula e ponto
        clean = re.sub(r'[^\d.,]', '', normalized)
        
        if not clean:
            return original, None
        
        try:
            # Lógica melhorada para preços brasileiros
            if ',' in clean and '.' in clean:
                # Tem ambos: "1.234,56" ou "1,234.56"
                last_comma = clean.rfind(',')
                last_dot = clean.rfind('.')
                
                if last_comma > last_dot:
                    # Formato brasileiro: "1.234,56"
                    clean = clean.replace('.', '').replace(',', '.')
                else:
                    # Formato americano: "1,234.56"
                    clean = clean.replace(',', '')
            elif '.' in clean:
                # Tem apenas ponto: verificar se é separador decimal ou de milhar
                parts = clean.split('.')
                if len(parts) == 2 and len(parts[1]) == 3:
                    # Provavelmente "123.456" (milhar) -> remover ponto
                    clean = clean.replace('.', '')
                elif len(parts) > 2:
                    # Múltiplos pontos -> remover todos
                    clean = clean.replace('.', '')
                # else: "123.45" (decimal) -> manter como está
            elif ',' in clean:
                # Tem apenas vírgula: verificar se é decimal ou milhar
                parts = clean.split(',')
                if len(parts) == 2 and len(parts[1]) <= 2:
                    # "123,45" (decimal) -> converter para ponto
                    clean = clean.replace(',', '.')
                else:
                    # "123456" (provavelmente milhar) -> remover vírgula
                    clean = clean.replace(',', '')
            
            price_float = float(clean)
            
            # Correção específica para Amazon: mover vírgula duas casas para a esquerda
            # Detectar padrão Amazon: número que precisa da vírgula movida
            if price_float >= 1000:
                # Verificar se é padrão Amazon (baseado no original)
                if '\n' in original or '\r' in original:
                    # Preço Amazon com quebra de linha: mover vírgula 2 casas
                    price_float = price_float / 100
                    logger.info(f"Preço Amazon corrigido (quebra linha): {original} -> {price_float}")
                elif len(str(int(price_float))) >= 4 and '.' not in clean and ',' not in clean:
                    # Número grande sem separadores: provavelmente Amazon
                    if len(str(int(price_float))) == 5:  # 39999 -> 399.99
                        price_float = price_float / 100
                        logger.info(f"Preço Amazon 5 dígitos corrigido: {original} -> {price_float}")
                    elif len(str(int(price_float))) == 4:  # 1299 -> 12.99
                        price_float = price_float / 100
                        logger.info(f"Preço Amazon 4 dígitos corrigido: {original} -> {price_float}")
                elif price_float >= 10000 and price_float < 100000:
                    # Padrão Amazon tradicional: mover vírgula 2 casas
                    price_float = price_float / 100
                    logger.info(f"Preço Amazon padrão corrigido: {original} -> {price_float}")
            
            # Formatar no padrão brasileiro
            if price_float >= 1000:
                formatted = f"R$ {price_float:,.2f}".replace(',', 'TEMP').replace('.', ',').replace('TEMP', '.')
            else:
                formatted = f"R$ {price_float:.2f}".replace('.', ',')
            
            logger.info(f"Preço processado: {original} -> {formatted}")
            return formatted, price_float
            
        except ValueError:
            logger.warning(f"Não foi possível converter o preço '{original}'")
            return original, None
    
    def scrape_amazon(self, url):
        """Extrai dados da Amazon com Selenium"""
        try:
            logger.info(f"Acessando Amazon: {url}")
            self.driver.get(url)
            time.sleep(3)
            
            data = {'url': url}
            
            # Título
            title_selectors = [
                '#productTitle',
                'h1#productTitle',
                '.a-size-large.product-title-word-break',
                'h1.a-size-large',
                'h1[data-asin]'
            ]
            
            for selector in title_selectors:
                try:
                    element = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    title = element.text.strip()
                    if title and len(title) > 5:
                        data['title'] = title
                        logger.info(f"Título encontrado: {title}")
                        break
                except TimeoutException:
                    continue
            
            # Preço
            price_selectors = [
                '.a-price.aok-align-center.reinventPricePriceToPayMargin.priceToPay',
                '.apexPriceToPay .a-price-whole',
                '.a-price-current',
                '.a-price .a-offscreen'
            ]
            
            for selector in price_selectors:
                try:
                    element = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    price_text = element.text.strip()
                    if price_text:
                        formatted, price_val = self.clean_price(price_text)
                        if formatted:
                            data['price'] = formatted
                            data['price_value'] = price_val
                            logger.info(f"Preço encontrado: {price_text} -> {formatted}")
                            break
                except TimeoutException:
                    continue
            
            # Imagem
            image_selectors = [
                '#landingImage',
                '.a-dynamic-image',
                'img[data-a-hires]'
            ]
            
            for selector in image_selectors:
                try:
                    element = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    img_src = element.get_attribute('src') or element.get_attribute('data-src')
                    if img_src and 'http' in img_src:
                        data['image_url'] = img_src
                        logger.info(f"Imagem encontrada: {img_src}")
                        break
                except TimeoutException:
                    continue
            
            return data
            
        except Exception as e:
            logger.error(f"Erro ao extrair dados da Amazon: {e}")
            return {'error': str(e), 'url': url}
    
    def scrape_mercadolivre(self, url):
        """Extrai dados do Mercado Livre com Selenium"""
        try:
            logger.info(f"Acessando Mercado Livre: {url}")
            self.driver.get(url)
            time.sleep(3)
            
            data = {'url': url}
            
            # Título
            title_selectors = [
                '.poly-component__title',
                'h1.ui-pdp-title',
                '.ui-pdp-title'
            ]
            
            for selector in title_selectors:
                try:
                    element = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    title = element.text.strip()
                    if title and len(title) > 5:
                        data['title'] = title
                        logger.info(f"Título encontrado: {title}")
                        break
                except TimeoutException:
                    continue
            
            # Preço
            price_selectors = [
                '.poly-price__current .andes-money-amount--cents-superscript .andes-money-amount__fraction',
                '.poly-price__current .andes-money-amount__fraction',
                '.ui-pdp-price__current .andes-money-amount__fraction'
            ]
            
            for selector in price_selectors:
                try:
                    element = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    price_text = element.text.strip()
                    if price_text:
                        formatted, price_val = self.clean_price(price_text)
                        if formatted:
                            data['price'] = formatted
                            data['price_value'] = price_val
                            logger.info(f"Preço encontrado: {price_text} -> {formatted}")
                            break
                except TimeoutException:
                    continue
            
            # Imagem
            image_selectors = [
                '.poly-component__picture',
                '.ui-pdp-gallery__figure__image',
                'img[src*="http2.mlstatic.com"]'
            ]
            
            for selector in image_selectors:
                try:
                    element = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    img_src = element.get_attribute('src') or element.get_attribute('data-src')
                    if img_src and 'http' in img_src:
                        data['image_url'] = img_src
                        logger.info(f"Imagem encontrada: {img_src}")
                        break
                except TimeoutException:
                    continue
            
            return data
            
        except Exception as e:
            logger.error(f"Erro ao extrair dados do Mercado Livre: {e}")
            return {'error': str(e), 'url': url}
    
    def scrape_magazineluiza(self, url):
        """Extrai dados do Magazine Luiza com Selenium"""
        try:
            logger.info(f"Acessando Magazine Luiza: {url}")
            
            # Configurar driver para Magazine Luiza
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.driver.get(url)
            time.sleep(3)  # Reduzido para 3 segundos - mais rápido
            
            # Esperar carregamento completo com timeout menor
            try:
                WebDriverWait(self.driver, 10).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
            except TimeoutException:
                logger.warning("Timeout aguardando carregamento completo, continuando...")
            
            # Verificar se houve redirecionamento
            current_url = self.driver.current_url
            logger.info(f"URL atual após carregamento: {current_url}")
            
            # Estratégia múltipla para encontrar o produto
            product_found = False
            
            # 1. Tentar encontrar botões ou links que levam ao produto
            try:
                button_selectors = [
                    'a[data-testid="button-container"]',
                    '.btn',
                    'button',
                    'a[href*="magazineluiza.com.br/p/"]',
                    'a[href*="magalu.com.br/p/"]',
                    '[data-testid*="button"]',
                    '.button',
                    'a[class*="button"]',
                    'a[class*="comprar"]',
                    'a[class*="product"]'
                ]
                
                for selector in button_selectors:
                    try:
                        product_buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        logger.info(f"Selector '{selector}' encontrou {len(product_buttons)} botões")
                        
                        for button in product_buttons:
                            try:
                                href = button.get_attribute('href')
                                text = button.text.strip().lower()
                                
                                if href and ('magazineluiza.com.br' in href or 'magalu.com.br' in href):
                                    logger.info(f"Encontrado link do produto: {href}")
                                    self.driver.get(href)
                                    time.sleep(2)
                                    product_found = True
                                    break
                                elif text and ('ver' in text or 'comprar' in text or 'produto' in text):
                                    href = button.get_attribute('href')
                                    if href:
                                        logger.info(f"Botão com texto '{text}' levando para: {href}")
                                        self.driver.get(href)
                                        time.sleep(2)
                                        product_found = True
                                        break
                            except:
                                continue
                        if product_found:
                            break
                    except Exception as e:
                        logger.debug(f"Erro com selector '{selector}': {e}")
                        continue
            except Exception as e:
                logger.debug(f"Erro ao procurar botões de produto: {e}")
            
            # 2. Se não encontrou botões, tentar encontrar links diretos na página
            if not product_found:
                try:
                    all_links = self.driver.find_elements(By.TAG_NAME, 'a')
                    logger.info(f"Verificando {len(all_links)} links na página...")
                    
                    for link in all_links:
                        try:
                            href = link.get_attribute('href')
                            if href and ('magazineluiza.com.br/p/' in href or 'magalu.com.br/p/' in href):
                                logger.info(f"Link direto do produto encontrado: {href}")
                                self.driver.get(href)
                                time.sleep(5)
                                product_found = True
                                break
                        except:
                            continue
                except Exception as e:
                    logger.debug(f"Erro ao procurar links diretos: {e}")
            
            data = {'url': url}
            
            # Título - seletores baseados no HTML real 2026
            title_selectors = [
                # HTML real fornecido - prioridade máxima
                'h1[data-testid="heading-product-title"]',
                'h1.sc-dcJsrY.jjGTqv',  # Classe específica do HTML
                
                # Página de produto
                'h2[data-testid="heading-product-title"]',
                '[data-testid="product-title"]',
                '[data-testid="heading-product"]',
                '.product-title',
                '.product-name',
                'h1.product-title',
                'h2.product-title',
                
                # Página de divulgador
                'h2[data-testid="heading"]',
                'h1[data-testid="heading"]',
                '.text-on-surface-2.font-xsm-regular',
                'h2.break-words',
                'h1',
                '[data-testid="heading"]',
                '.font-xsm-regular.text-on-surface-2',
                'h2.text-on-surface-2',
                'h1.text-on-surface-2',
                '.break-words.text-on-surface-2',
                
                # Genéricos
                '[class*="heading"]',
                '[class*="title"]',
                '[class*="product"]',
                '[class*="name"]',
                'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                'title',  # Tag title do HTML
                'div[class*="title"]',
                'span[class*="title"]',
                'p[class*="title"]',
                'div',  # Último recurso
                'span',
                'p'
            ]
            
            logger.info(f"URL atual: {self.driver.current_url}")
            logger.info("Procurando título...")
            
            for selector in title_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    logger.info(f"Selector '{selector}' encontrou {len(elements)} elementos")
                    
                    for element in elements:
                        title = element.text.strip()
                        if title and len(title) > 5 and len(title) < 300:
                            data['title'] = title
                            logger.info(f"Título encontrado com selector '{selector}': {title}")
                            break
                    if 'title' in data:
                        break
                except Exception as e:
                    logger.debug(f"Erro com selector '{selector}': {e}")
                    continue
            
            if 'title' not in data:
                logger.warning("Título não encontrado com nenhum selector")
            
            # Preço - seletores baseados no HTML real 2026
            price_selectors = [
                # HTML real fornecido - prioridade máxima
                'p[data-testid="price-value"]',
                'p.sc-dcJsrY.hsCKLu.sc-cXPBUD.kYFKbo',  # Classe específica do HTML
                'p[data-testid="price-original"]',
                'p.sc-dcJsrY.cHdUaZ.sc-cezyBN.kwGnVt',  # Preço original
                
                # Página de produto
                '[data-testid="price-value"]',
                '[data-testid="price"]',
                '[data-testid="price-current"]',
                '.price-current',
                '.price-value',
                '.product-price',
                '.price',
                'span.price-current',
                'p.price-current',
                
                # Página de divulgador
                '.text-on-surface-2.font-xlg-bold',
                '.text-on-surface-2.font-2xlg-bold',
                '.font-xlg-bold.text-on-surface-2',
                '.font-2xlg-bold.text-on-surface-2',
                'p.text-on-surface-2',
                'span.text-on-surface-2',
                
                # Genéricos
                '[class*="price"]',
                '[data-testid*="price"]',
                '[class*="valor"]',
                '[class*="money"]',
                '.font-xlg-bold',
                '.font-2xlg-bold',
                '.font-bold',
                'p', 'span', 'div', 'strong'
            ]
            
            logger.info("Procurando preço...")
            
            for selector in price_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    logger.info(f"Selector '{selector}' encontrou {len(elements)} elementos")
                    
                    for element in elements:
                        price_text = element.text.strip()
                        if price_text and ('R$' in price_text or any(c.isdigit() for c in price_text)):
                            formatted, price_val = self.clean_price(price_text)
                            if formatted:
                                data['price'] = formatted
                                data['price_value'] = price_val
                                logger.info(f"Preço encontrado com selector '{selector}': {price_text} -> {formatted}")
                                break
                    if 'price' in data:
                        break
                except Exception as e:
                    logger.debug(f"Erro com selector '{selector}': {e}")
                    continue
            
            if 'price' not in data:
                logger.warning("Preço não encontrado com nenhum selector")
            
            # Imagem - seletores baseados no HTML real 2026
            image_selectors = [
                # HTML real fornecido - prioridade máxima
                'img[data-testid="image-selected-thumbnail"]',
                'img.sc-hzhJZQ.knorgy',  # Classe específica do HTML
                'img[data-testid="media-gallery-image"]',
                'img.sc-hzhJZQ.dCUEWm',  # Classe específica do HTML
                
                # Página de produto
                'img[data-testid="image"]',
                '[data-testid="image"]',
                'img[data-testid="product-image"]',
                '[data-testid="product-image"]',
                '.product-image',
                '.product-picture',
                '.gallery-image',
                'img.product-image',
                
                # Página de divulgador
                'img[alt*="Imagem do produto"]',
                'img[alt*="imagem do produto"]',
                'img[alt*="produto"]',
                'img[alt*="Produto"]',
                'img[decoding="auto"]',
                
                # Domínios específicos
                'img[src*="mlcdn.com.br"]',
                'img[src*="wx.mlcdn.com.br"]',
                'img[src*="magazineluiza.com.br"]',
                'img[src*="magalu.com.br"]',
                'img[src*="a-static.mlcdn.com.br"]',  # Do HTML real
                
                # Genéricos
                'img[src*="http"]',
                'img[src*="https"]',
                'img[src*="cdn"]',
                'img[src*="image"]',
                'img[src*="img"]',
                'img[alt*="Imagem"]',
                'img[alt*="imagem"]',
                'img[alt*="Foto"]',
                'img[alt*="foto"]',
                'img'  # Fallback genérico
            ]
            
            logger.info("Procurando imagem...")
            
            for selector in image_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    logger.info(f"Selector '{selector}' encontrou {len(elements)} elementos")
                    
                    for element in elements:
                        img_src = element.get_attribute('src') or element.get_attribute('data-src')
                        if img_src and 'http' in img_src:
                            data['image_url'] = img_src
                            logger.info(f"Imagem encontrada com selector '{selector}': {img_src}")
                            break
                    if 'image_url' in data:
                        break
                except Exception as e:
                    logger.debug(f"Erro com selector '{selector}': {e}")
                    continue
            
            if 'image_url' not in data:
                logger.warning("Imagem não encontrada com nenhum selector")
            
            # Log do resultado
            title_found = bool(data.get('title'))
            price_found = bool(data.get('price'))
            image_found = bool(data.get('image_url'))
            
            logger.info(f"Scraping Magazine Luiza - Título: {title_found}, Preço: {price_found}, Imagem: {image_found}")
            
            if title_found and price_found:
                logger.info("Scraping Magazine Luiza bem-sucedido!")
            else:
                logger.warning("Scraping Magazine Luiza parcial ou falhou")
            
            return data
            
        except Exception as e:
            logger.error(f"Erro ao extrair dados do Magazine Luiza: {e}")
            return {'error': str(e), 'url': url}
    
    def scrape_shopee(self, url):
        """Extrai dados do Shopee com Selenium"""
        try:
            logger.info(f"Acessando Shopee: {url}")
            self.driver.get(url)
            time.sleep(2)
            
            data = {'url': url}
            
            # Título
            title_selectors = [
                'span[data-testid="pdp-product-title"]',
                '.product-briefing__title',
                'h1'
            ]
            
            for selector in title_selectors:
                try:
                    element = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    title = element.text.strip()
                    if title and len(title) > 5:
                        data['title'] = title
                        logger.info(f"Título encontrado: {title}")
                        break
                except TimeoutException:
                    continue
            
            # Preço
            price_selectors = [
                'span[data-testid="pdp-price"]',
                '.current-price',
                '.product-briefing__price .current-price'
            ]
            
            for selector in price_selectors:
                try:
                    element = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    price_text = element.text.strip()
                    if price_text:
                        formatted, price_val = self.clean_price(price_text)
                        if formatted:
                            data['price'] = formatted
                            data['price_value'] = price_val
                            logger.info(f"Preço encontrado: {price_text} -> {formatted}")
                            break
                except TimeoutException:
                    continue
            
            # Imagem
            image_selectors = [
                'img[data-testid="pdp-product-image"]',
                '.product-briefing__image',
                'img[src*="susercontent"]'
            ]
            
            for selector in image_selectors:
                try:
                    element = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    img_src = element.get_attribute('src') or element.get_attribute('data-src')
                    if img_src and 'http' in img_src:
                        data['image_url'] = img_src
                        logger.info(f"Imagem encontrada: {img_src}")
                        break
                except TimeoutException:
                    continue
            
            return data
            
        except Exception as e:
            logger.error(f"Erro ao extrair dados do Shopee: {e}")
            return {'error': str(e), 'url': url}
    
    def scrape_product(self, url):
        """Função principal de scraping"""
        try:
            site = self.identify_site(url)
            logger.info(f"Site identificado: {site}")
            
            if site == 'amazon':
                return self.scrape_amazon(url)
            elif site == 'mercadolivre':
                return self.scrape_mercadolivre(url)
            elif site == 'magazineluiza':
                return self.scrape_magazineluiza(url)
            elif site == 'shopee':
                return self.scrape_shopee(url)
            else:
                return {'error': f'Site não suportado: {site}', 'url': url}
                
        except Exception as e:
            logger.error(f"Erro no scraping: {e}")
            return {'error': str(e), 'url': url}
    
    def generate_message(self, product_data, free_shipping=False, coupon_name=None, coupon_discount=None):
        """Gera mensagem padronizada para WhatsApp com emojis"""
        try:
            title = product_data.get('title', 'Produto não encontrado')
            price = product_data.get('price', 'Preço não encontrado')
            
            message = f"🔥🔥 *SUPER OFERTA EXCLUSIVA!* 🔥🔥\n\n"
            message += f"�️ *PRODUTO:* {title}\n\n"
            message += f"� *PREÇO ESPECIAL:* {price}\n"
            
            if free_shipping:
                message += f"🚚 *FRETE GRÁTIS* para todo Brasil! 🇧🇷\n"
            
            if coupon_name and coupon_discount:
                message += f"�️ *CUPOM EXTRA:* {coupon_name} - {coupon_discount}% DE DESCONTO!\n"
            
            message += f"\n⏰ *CORRA! OFERTA POR TEMPO LIMITADO!* ⏰\n\n"
            message += f"� *GARANTA JÁ O SEU:* 👇\n"
            message += f"{product_data.get('url', '')}\n\n"
            message += f"�️ *Free Island - As melhores ofertas da internet!* �️\n"
            message += f"🔗 *Mais promoções:* {LINKTREE_URL}\n\n"
            message += f"✨ *Aproveite! Compre agora e economize muito!* ✨"
            
            return message
            
        except Exception as e:
            logger.error(f"Erro ao gerar mensagem: {e}")
            return "Erro ao gerar mensagem"
    
    def save_to_supabase(self, product_data, message):
        """Salva no Supabase"""
        try:
            payload = {
                "mensagem": json.dumps(message, ensure_ascii=False),
                "imagem_url": product_data.get('image_url', ''),
                "enviado": False,
                "criado_em": datetime.now().isoformat()
            }
            
            response = requests.post(
                f"{SUPABASE_URL}/rest/v1/produtos",
                headers=SUPABASE_HEADERS,
                json=payload
            )
            
            if response.status_code == 201:
                logger.info("Produto salvo no Supabase com sucesso")
                return True
            else:
                logger.error(f"Erro ao salvar no Supabase: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao salvar no Supabase: {e}")
            return False
    
    def close(self):
        """Fecha o WebDriver"""
        if self.driver:
            self.driver.quit()
            logger.info("WebDriver fechado")

# Inicializa o scraper
scraper = FreeIslandScraper()

@app.route('/')
def index():
    return redirect(url_for('login_page'))

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/auth', methods=['POST'])
def auth():
    email = request.form.get('email')
    senha = request.form.get('senha')
    
    if email == LOGIN_EMAIL and senha == LOGIN_SENHA:
        session['user_id'] = email
        session['user_name'] = 'Free Island'
        return redirect(url_for('dashboard'))
    else:
        return render_template('login.html', error='Credenciais inválidas!')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user_name=session.get('user_name'))

@app.route('/scrape', methods=['POST'])
@login_required
def scrape():
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'URL não fornecida'}), 400
        
        # Fazer scraping
        product_data = scraper.scrape_product(url)
        
        if 'error' in product_data:
            return jsonify({'error': product_data['error']}), 500
        
        # Gerar mensagem
        free_shipping = data.get('free_shipping', False)
        coupon_name = data.get('coupon_name')
        coupon_discount = data.get('coupon_discount')
        
        message = scraper.generate_message(
            product_data, 
            free_shipping, 
            coupon_name, 
            coupon_discount
        )
        
        return jsonify({
            'product': product_data,
            'message': message,
            'success': True
        })
        
    except Exception as e:
        logger.error(f"Erro no scraping: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/save', methods=['POST'])
@login_required
def save():
    try:
        data = request.get_json()
        product_data = data.get('product')
        message = data.get('message')
        
        if not product_data or not message:
            return jsonify({'error': 'Dados incompletos'}), 400
        
        # Salvar no Supabase
        success = scraper.save_to_supabase(product_data, message)
        
        if success:
            return jsonify({'success': True, 'message': 'Produto salvo com sucesso!'})
        else:
            return jsonify({'error': 'Erro ao salvar produto'}), 500
            
    except Exception as e:
        logger.error(f"Erro ao salvar: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=5000, debug=False)
    finally:
        scraper.close()
