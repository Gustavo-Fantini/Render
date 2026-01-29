from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_cors import CORS
import logging
import functools
import re
import json
from datetime import datetime
import uuid
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import os
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

IS_PRODUCTION = os.environ.get('RENDER') == 'true'
BASE_SCRAPE_DELAY_SECONDS = int(os.environ.get('SCRAPE_BASE_DELAY_SECONDS', '5'))
# Versionamento:
# correção -> 0.0.1 | coisa nova -> 0.1.0 | estrutura completamente nova -> 1.0.0
# Atualize este número a cada push.
APP_VERSION = os.environ.get('APP_VERSION', '3.15.2')
ALLOW_SELENIUM_IN_PROD = os.environ.get('ALLOW_SELENIUM_IN_PROD', 'true').lower() in ('1', 'true', 'yes')
ALWAYS_USE_SELENIUM = os.environ.get('ALWAYS_USE_SELENIUM', 'true').lower() in ('1', 'true', 'yes')

def get_env(name, default=None, required=False):
    value = os.environ.get(name, default)
    if required and not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

app = Flask(__name__)
app.secret_key = get_env('FLASK_SECRET_KEY', default='dev-secret-key', required=IS_PRODUCTION)
app.config['JSON_AS_ASCII'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
if IS_PRODUCTION:
    app.config['SESSION_COOKIE_SECURE'] = True
CORS(app)

@app.context_processor
def inject_app_meta():
    return {
        "app_version": APP_VERSION,
        "current_year": datetime.utcnow().year
    }

# Configurações Supabase
SUPABASE_URL = get_env('SUPABASE_URL', default='', required=IS_PRODUCTION)
SUPABASE_KEY_SERVICE = get_env('SUPABASE_SERVICE_KEY', default='', required=IS_PRODUCTION)
SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY_SERVICE,
    "Authorization": f"Bearer {SUPABASE_KEY_SERVICE}",
    "Content-Type": "application/json"
}

# Credenciais de login
LOGIN_EMAIL = get_env('LOGIN_EMAIL', default='', required=IS_PRODUCTION)
LOGIN_SENHA = get_env('LOGIN_PASSWORD', default='', required=IS_PRODUCTION)

# Linktree
LINKTREE_URL = "https://linktr.ee/freeisland"

# Código de erro padronizado para resposta e logs
def error_response(code, message, http_status=500, details=None, request_id=None):
    payload = {
        "error_code": code,
        "error": message,
        "request_id": request_id
    }
    if details:
        payload["details"] = details
    return payload, http_status

def log_event(level, message, **fields):
    # Log estruturado simples para facilitar diagnóstico no Render
    entry = {"message": message}
    if fields:
        entry["fields"] = fields
    logger.log(level, json.dumps(entry, ensure_ascii=False))

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
        self.last_error = None
        self.setup_driver()

    def set_last_error(self, code, message, **details):
        self.last_error = {"error_code": code, "error": message}
        if details:
            self.last_error["details"] = details
        log_event(logging.WARNING, "scrape_stage_error", code=code, message=message, **details)

    def clear_last_error(self):
        self.last_error = None

    def build_chrome_options(self, production=False, user_agent=None):
        options = Options()
        headless_arg = '--headless=new' if production else '--headless'
        options.add_argument(headless_arg)
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-features=IsolateOrigins,site-per-process')
        options.add_argument('--lang=pt-BR,pt')
        if user_agent:
            options.add_argument(f'--user-agent={user_agent}')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_experimental_option('prefs', {
            'intl.accept_languages': 'pt-BR,pt',
            'profile.default_content_setting_values.notifications': 2
        })
        return options

    def setup_driver(self):
        """Configura o Selenium WebDriver para deploy no Render"""
        if IS_PRODUCTION:
            # Configuração para Render
            options = self.build_chrome_options(
                production=True,
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            uc = None
            try:
                import undetected_chromedriver as uc  # Lazy import to avoid distutils issues on newer Python
            except Exception as e:
                logger.warning(f"Undetected Chrome indisponível: {e}")

            if uc is not None:
                try:
                    # Tentar usar undetected-chromedriver primeiro
                    self.driver = uc.Chrome(options=options, version_main=None)
                    logger.info("WebDriver (undetected) inicializado com sucesso no Render")
                except Exception as e:
                    logger.warning(f"Undetected Chrome falhou: {e}")
                    self.driver = None

            if self.driver is None:
                try:
                    # Fallback para Chrome normal
                    self.driver = webdriver.Chrome(options=options)
                    logger.info("WebDriver (normal) inicializado com sucesso no Render")
                except Exception as e2:
                    logger.error(f"Todos os drivers falharam: {e2}")
                    self.driver = None
            self.harden_driver()
        else:
            # Configuração para desenvolvimento local
            options = self.build_chrome_options(
                production=False,
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            try:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=options)
                logger.info("WebDriver inicializado com sucesso localmente")
            except Exception as e:
                logger.error(f"Erro ao inicializar WebDriver local: {e}")
                self.driver = None
            self.harden_driver()

    def harden_driver(self):
        if not self.driver:
            return
        try:
            self.driver.execute_cdp_cmd("Emulation.setTimezoneOverride", {"timezoneId": "America/Sao_Paulo"})
            self.driver.execute_cdp_cmd(
                "Network.setUserAgentOverride",
                {
                    "userAgent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "acceptLanguage": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                    "platform": "Linux x86_64"
                }
            )
            self.driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'languages', {get: () => ['pt-BR','pt','en-US','en']});
Object.defineProperty(navigator, 'platform', {get: () => 'Linux x86_64'});
Object.defineProperty(navigator, 'vendor', {get: () => 'Google Inc.'});
window.chrome = window.chrome || { runtime: {} };
"""}
            )
        except Exception as e:
            logger.debug(f"Falha ao aplicar hardening do driver: {e}")

    def is_blocked_page(self, page_source):
        if not page_source:
            return False
        lower = page_source.lower()
        return any(token in lower for token in (
            'captcha',
            'robot check',
            'validatecaptcha',
            'unusual traffic',
            'access denied',
            'temporarily unavailable',
        ))

    def navigate_with_wait(self, url, wait_seconds=2, ready_timeout=10):
        self.driver.set_page_load_timeout(20)
        try:
            self.driver.get(url)
        except TimeoutException:
            logger.warning("Timeout no carregamento (Selenium), continuando...")
            self.set_last_error("SELENIUM_TIMEOUT", "Timeout no carregamento da página", url=url)
        except Exception as e:
            logger.warning(f"Falha ao carregar URL no Selenium: {e}")
            self.set_last_error("SELENIUM_NAV_EXCEPTION", "Falha ao abrir página no Selenium", url=url, error=str(e))
            return False
        time.sleep(wait_seconds)
        self.wait_ready(timeout=ready_timeout)
        try:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.5);")
            time.sleep(0.7)
            self.driver.execute_script("window.scrollTo(0, 0);")
        except Exception:
            pass
        return True

    def retry_if_blocked(self, wait_seconds=2, ready_timeout=8):
        """Tenta um refresh simples quando detecta bloqueio/captcha"""
        try:
            page_source = self.driver.page_source
            if self.is_blocked_page(page_source):
                logger.warning("Bloqueio detectado, tentando refresh...")
                self.driver.refresh()
                time.sleep(wait_seconds)
                self.wait_ready(timeout=ready_timeout)
                page_source = self.driver.page_source
                if self.is_blocked_page(page_source):
                    return True
        except Exception:
            pass
        return False
    
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
        # Evitar duplicações de separadores (ex: "3.913,,05")
        clean = re.sub(r'[.,]{2,}', lambda m: m.group(0)[0], clean)
        
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

    def normalize_price_text(self, text):
        """Normaliza preço para lidar com faixas e separadores incomuns"""
        if not text:
            return None
        normalized = text.replace('\xa0', ' ').strip()
        parts = re.split(r'\s*[-–]\s*', normalized)
        return parts[0].strip() if parts else normalized

    def ensure_driver(self):
        """Garante que o WebDriver esteja pronto para uso"""
        if self.driver is None:
            self.setup_driver()
        return self.driver is not None

    def wait_ready(self, timeout=10):
        """Aguarda o carregamento básico da página"""
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") in ("interactive", "complete")
            )
        except TimeoutException:
            logger.warning("Timeout aguardando document.readyState, continuando...")

    def has_any_data(self, data):
        return any(data.get(k) for k in ("title", "price", "image_url"))

    def first_text_by_selectors(self, selectors, min_len=1):
        """Retorna o primeiro texto encontrado para a lista de seletores"""
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    text = element.text.strip()
                    if text and len(text) >= min_len:
                        return text
            except Exception:
                continue
        return None

    def first_attr_by_selectors(self, selectors, attrs=("src", "data-src", "data-old-hires", "data-a-hires")):
        """Retorna o primeiro atributo válido encontrado para a lista de seletores"""
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    for attr in attrs:
                        val = element.get_attribute(attr)
                        if val and 'http' in val and not val.startswith('data:'):
                            return val
            except Exception:
                continue
        return None

    def extract_title_from_selectors(self, selectors, min_len=5, max_len=300):
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    title = element.text.strip()
                    if title and min_len <= len(title) <= max_len:
                        return title
            except Exception:
                continue
        return None

    def extract_price_from_selectors(self, selectors):
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    price_text = element.text.strip()
                    if price_text and any(c.isdigit() for c in price_text):
                        price_text = self.normalize_price_text(price_text)
                        formatted, price_val = self.clean_price(price_text)
                        if formatted and price_val:
                            return formatted, price_val
            except Exception:
                continue
        return None, None

    def extract_image_from_selectors(self, selectors):
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    img_src = element.get_attribute('src') or element.get_attribute('data-src')
                    if img_src and 'http' in img_src and not img_src.startswith('data:'):
                        return img_src
            except Exception:
                continue
        return None

    def extract_amazon_price(self):
        """Extrai preço Amazon usando combinações de seletores mais estáveis"""
        # 1) Preço principal no bloco corePriceDisplay (mais confiável)
        offscreen_text = self.first_text_by_selectors([
            '#corePriceDisplay_desktop_feature_div .priceToPay .aok-offscreen',
            '#corePriceDisplay_desktop_feature_div .priceToPay .a-offscreen',
            '#corePriceDisplay_desktop_feature_div .a-price .aok-offscreen',
            '#corePriceDisplay_desktop_feature_div .a-price .a-offscreen',
            '#apex_desktop_newAccordionRow .a-offscreen',
        ], min_len=2)
        if offscreen_text:
            return offscreen_text

        # 2) Montar preço por partes (símbolo + inteiro + fração) no corePriceDisplay
        containers = [
            '#corePriceDisplay_desktop_feature_div .a-price.priceToPay',
            '#corePriceDisplay_desktop_feature_div .a-price.aok-align-center.reinventPricePriceToPayMargin.priceToPay',
            '#corePriceDisplay_desktop_feature_div .a-price',
        ]
        for selector in containers:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    symbol = element.find_elements(By.CSS_SELECTOR, '.a-price-symbol')
                    whole = element.find_elements(By.CSS_SELECTOR, '.a-price-whole')
                    fraction = element.find_elements(By.CSS_SELECTOR, '.a-price-fraction')
                    if whole:
                        symbol_text = symbol[0].text.strip() if symbol else 'R$'
                        whole_text = whole[0].text.strip().rstrip(',.')
                        fraction_text = fraction[0].text.strip() if fraction else ''
                        if whole_text:
                            price_text = f"{symbol_text} {whole_text}"
                            if fraction_text:
                                price_text += f",{fraction_text}"
                            return price_text
            except Exception:
                continue

        # 3) Fallback: apex_price (às vezes usado no centro)
        offscreen_text = self.first_text_by_selectors([
            '#apex_desktop #apex_price .aok-offscreen',
            '#apex_desktop #apex_price .a-offscreen',
            '#priceblock_ourprice',
            '#priceblock_dealprice',
            '#priceblock_saleprice',
        ], min_len=2)
        if offscreen_text:
            return offscreen_text

        # 4) Fallback final: meta tags (podem existir em alguns layouts)
        try:
            meta_price = self.driver.execute_script(
                "var m = document.querySelector('meta[property=\"product:price:amount\"], meta[property=\"og:price:amount\"]');"
                "return m ? m.getAttribute('content') : null;"
            )
            if meta_price:
                return f"R$ {meta_price}"
        except Exception:
            pass

        return None

    def scrape_amazon_requests(self, url):
        """Extrai dados da Amazon via requests (mais rápido que Selenium)"""
        self.clear_last_error()
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Connection": "close"
        }
        try:
            start = time.time()
            response = requests.get(url, headers=headers, timeout=12, allow_redirects=True)
            elapsed_ms = int((time.time() - start) * 1000)
            log_event(
                logging.INFO,
                "amazon_requests_response",
                status=response.status_code,
                elapsed_ms=elapsed_ms,
                final_url=response.url,
                content_length=len(response.text or "")
            )
            if response.status_code != 200:
                log_event(logging.WARNING, "amazon_requests_non_200", status=response.status_code, final_url=response.url)
                self.set_last_error("AMAZON_REQUESTS_NON_200", "Resposta não-200 da Amazon (requests)", status=response.status_code, final_url=response.url)
                return None

            html = response.text
            lower_html = html.lower()
            if 'captcha' in lower_html or 'robot check' in lower_html or 'validatecaptcha' in lower_html:
                log_event(logging.WARNING, "amazon_requests_blocked", reason="captcha_or_robot_check", final_url=response.url)
                self.set_last_error("AMAZON_REQUESTS_BLOCKED", "Bloqueio/captcha detectado (requests)", final_url=response.url)
                return None
            log_event(
                logging.INFO,
                "amazon_requests_html_markers",
                has_product_title=("productTitle" in html),
                has_core_price=("corePriceDisplay" in html),
                has_meta_price=('property="product:price:amount"' in html or 'property="og:price:amount"' in html),
                has_og_image=('property="og:image"' in html),
                final_url=response.url
            )

            soup = BeautifulSoup(html, 'html.parser')
            data = {'url': url, 'resolved_url': response.url or url}

            title_el = soup.select_one('#productTitle') or soup.select_one('#title span') or soup.select_one('#title')
            if title_el:
                title = title_el.get_text(strip=True)
                if title:
                    data['title'] = title

            price_el = soup.select_one('#corePriceDisplay_desktop_feature_div .priceToPay .aok-offscreen') \
                or soup.select_one('#corePriceDisplay_desktop_feature_div .priceToPay .a-offscreen') \
                or soup.select_one('#corePriceDisplay_desktop_feature_div .a-price .aok-offscreen') \
                or soup.select_one('#corePriceDisplay_desktop_feature_div .a-price .a-offscreen')
            price_text = price_el.get_text(strip=True) if price_el else None
            if not price_text:
                symbol = soup.select_one('#corePriceDisplay_desktop_feature_div .a-price-symbol')
                whole = soup.select_one('#corePriceDisplay_desktop_feature_div .a-price-whole')
                fraction = soup.select_one('#corePriceDisplay_desktop_feature_div .a-price-fraction')
                if whole:
                    symbol_text = symbol.get_text(strip=True) if symbol else 'R$'
                    whole_text = whole.get_text(strip=True).rstrip(',.')
                    fraction_text = fraction.get_text(strip=True) if fraction else ''
                    price_text = f"{symbol_text} {whole_text}"
                    if fraction_text:
                        price_text += f",{fraction_text}"
            if not price_text:
                # Fallback: apex_price (às vezes aparece no centro do ATF)
                apex_offscreen = soup.select_one('#apex_desktop #apex_price .aok-offscreen') \
                    or soup.select_one('#apex_desktop #apex_price .a-offscreen')
                if apex_offscreen:
                    price_text = apex_offscreen.get_text(strip=True)
            if not price_text:
                # Fallback final: meta tags
                meta_price = soup.select_one('meta[property="product:price:amount"]') or soup.select_one('meta[property="og:price:amount"]')
                if meta_price and meta_price.get('content'):
                    price_text = f"R$ {meta_price.get('content')}"

            if price_text:
                formatted, price_val = self.clean_price(price_text)
                if formatted:
                    data['price'] = formatted
                    data['price_value'] = price_val

            image_el = soup.select_one('#landingImage') or soup.select_one('img[data-a-hires]') or soup.select_one('img[data-old-hires]')
            img_src = None
            if image_el:
                img_src = image_el.get('data-old-hires') or image_el.get('data-a-hires') or image_el.get('src')
            if not img_src:
                og_img = soup.select_one('meta[property="og:image"]')
                if og_img:
                    img_src = og_img.get('content')
            if img_src and 'http' in img_src:
                data['image_url'] = img_src

            if any(data.get(k) for k in ('title', 'price', 'image_url')):
                log_event(logging.INFO, "amazon_requests_success", has_title=bool(data.get("title")), has_price=bool(data.get("price")), has_image=bool(data.get("image_url")))
                return data
            log_event(logging.WARNING, "amazon_requests_no_data", final_url=response.url)
            self.set_last_error("AMAZON_REQUESTS_NO_DATA", "Nenhum dado encontrado (requests)", final_url=response.url)
        except Exception as e:
            log_event(logging.ERROR, "amazon_requests_exception", error=str(e))
            self.set_last_error("AMAZON_REQUESTS_EXCEPTION", "Erro ao requisitar Amazon (requests)", error=str(e))

        return None

    def resolve_amazon_url(self, url):
        """Resolve URLs encurtadas da Amazon (ex: amzn.to)"""
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Connection": "close"
        }
        try:
            response = requests.head(url, headers=headers, timeout=8, allow_redirects=True)
            if response.url:
                return response.url
        except Exception:
            pass
        try:
            response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
            if response.url:
                return response.url
        except Exception:
            pass
        return url

    def try_accept_amazon_cookies(self):
        """Tenta aceitar banner de cookies da Amazon (quando aparece)"""
        selectors = [
            '#sp-cc-accept',
            'input#sp-cc-accept',
            'button#sp-cc-accept',
            'input[name="accept"]',
            'button[name="accept"]',
        ]
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    elements[0].click()
                    time.sleep(0.5)
                    return True
            except Exception:
                continue
        return False

    def scrape_mercadolivre_requests(self, url):
        """Extrai dados do Mercado Livre via requests"""
        self.clear_last_error()
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Connection": "close"
        }
        try:
            start = time.time()
            response = requests.get(url, headers=headers, timeout=12, allow_redirects=True)
            elapsed_ms = int((time.time() - start) * 1000)
            log_event(
                logging.INFO,
                "mercadolivre_requests_response",
                status=response.status_code,
                elapsed_ms=elapsed_ms,
                final_url=response.url,
                content_length=len(response.text or "")
            )
            if response.status_code != 200:
                log_event(logging.WARNING, "mercadolivre_requests_non_200", status=response.status_code, final_url=response.url)
                self.set_last_error("MERCADOLIVRE_REQUESTS_NON_200", "Resposta não-200 do Mercado Livre (requests)", status=response.status_code, final_url=response.url)
                return None

            html = response.text
            lower_html = html.lower()
            if 'captcha' in lower_html or 'robot' in lower_html:
                log_event(logging.WARNING, "mercadolivre_requests_blocked", reason="captcha_or_robot", final_url=response.url)
                self.set_last_error("MERCADOLIVRE_REQUESTS_BLOCKED", "Bloqueio/captcha detectado (requests)", final_url=response.url)
                return None
            log_event(
                logging.INFO,
                "mercadolivre_requests_html_markers",
                has_ui_pdp_title=("ui-pdp-title" in html),
                has_meta_price=('itemprop="price"' in html),
                has_andes_money_amount=("andes-money-amount" in html),
                has_og_image=('property="og:image"' in html),
                final_url=response.url
            )

            soup = BeautifulSoup(html, 'html.parser')
            data = {'url': url, 'resolved_url': response.url or url}

            title_el = soup.select_one('h1.ui-pdp-title') or soup.select_one('.ui-pdp-title') or soup.select_one('h1')
            if title_el:
                title = title_el.get_text(strip=True)
                if title:
                    data['title'] = title

            price_text = None
            price_meta = soup.select_one('meta[itemprop="price"]')
            if price_meta and price_meta.get('content'):
                price_text = f"R$ {price_meta.get('content')}"
            if not price_text:
                price_container = soup.select_one('#price .andes-money-amount') or soup.select_one('.ui-pdp-price .andes-money-amount')
                if price_container:
                    symbol = price_container.select_one('.andes-money-amount__currency-symbol')
                    fraction = price_container.select_one('.andes-money-amount__fraction')
                    cents = price_container.select_one('.andes-money-amount__cents')
                    symbol_text = symbol.get_text(strip=True) if symbol else 'R$'
                    fraction_text = fraction.get_text(strip=True) if fraction else ''
                    cents_text = cents.get_text(strip=True) if cents else ''
                    if fraction_text:
                        price_text = f"{symbol_text} {fraction_text}"
                        if cents_text:
                            price_text += f",{cents_text}"

            if price_text:
                formatted, price_val = self.clean_price(price_text)
                if formatted:
                    data['price'] = formatted
                    data['price_value'] = price_val

            img_src = None
            og_img = soup.select_one('meta[property="og:image"]')
            if og_img:
                img_src = og_img.get('content')
            if not img_src:
                img_el = soup.select_one('img.ui-pdp-image') or soup.select_one('img[src*="http2.mlstatic.com"]')
                if img_el:
                    img_src = img_el.get('src') or img_el.get('data-src')
            if img_src and 'http' in img_src:
                data['image_url'] = img_src

            if any(data.get(k) for k in ('title', 'price', 'image_url')):
                log_event(logging.INFO, "mercadolivre_requests_success", has_title=bool(data.get("title")), has_price=bool(data.get("price")), has_image=bool(data.get("image_url")))
                return data
            log_event(logging.WARNING, "mercadolivre_requests_no_data", final_url=response.url)
            self.set_last_error("MERCADOLIVRE_REQUESTS_NO_DATA", "Nenhum dado encontrado (requests)", final_url=response.url)
        except Exception as e:
            log_event(logging.ERROR, "mercadolivre_requests_exception", error=str(e))
            self.set_last_error("MERCADOLIVRE_REQUESTS_EXCEPTION", "Erro ao requisitar Mercado Livre (requests)", error=str(e))

        return None

    def scrape_shopee_requests(self, url):
        """Extrai dados do Shopee via requests"""
        self.clear_last_error()
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Connection": "close"
        }
        try:
            start = time.time()
            response = requests.get(url, headers=headers, timeout=12, allow_redirects=True)
            elapsed_ms = int((time.time() - start) * 1000)
            log_event(
                logging.INFO,
                "shopee_requests_response",
                status=response.status_code,
                elapsed_ms=elapsed_ms,
                final_url=response.url,
                content_length=len(response.text or "")
            )
            if response.status_code != 200:
                log_event(logging.WARNING, "shopee_requests_non_200", status=response.status_code, final_url=response.url)
                self.set_last_error("SHOPEE_REQUESTS_NON_200", "Resposta não-200 da Shopee (requests)", status=response.status_code, final_url=response.url)
                return None

            html = response.text
            lower_html = html.lower()
            if 'captcha' in lower_html or 'robot' in lower_html:
                log_event(logging.WARNING, "shopee_requests_blocked", reason="captcha_or_robot", final_url=response.url)
                self.set_last_error("SHOPEE_REQUESTS_BLOCKED", "Bloqueio/captcha detectado (requests)", final_url=response.url)
                return None
            log_event(
                logging.INFO,
                "shopee_requests_html_markers",
                has_vR6K3w=("vR6K3w" in html),
                has_IZPeQz_B67UQ0=("IZPeQz B67UQ0" in html),
                has_IZPeQz=("IZPeQz" in html),
                has_pdp_product_title=('data-testid="pdp-product-title"' in html),
                has_pdp_price=('data-testid="pdp-price"' in html),
                has_og_title=('property="og:title"' in html),
                has_og_image=('property="og:image"' in html),
                final_url=response.url
            )

            soup = BeautifulSoup(html, 'html.parser')
            data = {'url': url, 'resolved_url': response.url or url}

            title_el = (
                soup.select_one('meta[property="og:title"]')
                or soup.select_one('h1.vR6K3w')
                or soup.select_one('span[data-testid="pdp-product-title"]')
                or soup.select_one('h1')
            )
            if title_el:
                title = title_el.get('content') if title_el.name == 'meta' else title_el.get_text(strip=True)
                if title:
                    data['title'] = title

            price_text = None
            meta_price = soup.select_one('meta[property="product:price:amount"]') or soup.select_one('meta[property="og:price:amount"]')
            if meta_price and meta_price.get('content'):
                price_text = f"R$ {meta_price.get('content')}"
            if not price_text:
                price_el = soup.select_one('div.IZPeQz.B67UQ0') or soup.select_one('div.IZPeQz') or soup.select_one('span[data-testid="pdp-price"]')
                if price_el:
                    price_text = self.normalize_price_text(price_el.get_text(strip=True))

            if price_text:
                formatted, price_val = self.clean_price(price_text)
                if formatted:
                    data['price'] = formatted
                    data['price_value'] = price_val

            img_src = None
            og_img = soup.select_one('meta[property="og:image"]')
            if og_img:
                img_src = og_img.get('content')
            if not img_src:
                img_el = soup.select_one('img[src*="susercontent.com/file"]')
                if img_el:
                    img_src = img_el.get('src') or img_el.get('data-src')
            if img_src and 'http' in img_src:
                data['image_url'] = img_src

            if any(data.get(k) for k in ('title', 'price', 'image_url')):
                log_event(logging.INFO, "shopee_requests_success", has_title=bool(data.get("title")), has_price=bool(data.get("price")), has_image=bool(data.get("image_url")))
                return data
            log_event(logging.WARNING, "shopee_requests_no_data", final_url=response.url)
            self.set_last_error("SHOPEE_REQUESTS_NO_DATA", "Nenhum dado encontrado (requests)", final_url=response.url)
        except Exception as e:
            log_event(logging.ERROR, "shopee_requests_exception", error=str(e))
            self.set_last_error("SHOPEE_REQUESTS_EXCEPTION", "Erro ao requisitar Shopee (requests)", error=str(e))

        return None
    
    def scrape_amazon(self, url):
        """Extrai dados da Amazon com Selenium"""
        try:
            self.clear_last_error()
            # Primeiro tentar via requests (mais rápido e evita timeout do renderer)
            if not ALWAYS_USE_SELENIUM:
                requests_data = self.scrape_amazon_requests(url)
                if requests_data:
                    return requests_data
            if IS_PRODUCTION and not ALLOW_SELENIUM_IN_PROD:
                # Em produção, evitar Selenium se explicitamente desabilitado
                requests_data = self.scrape_amazon_requests(url)
                if requests_data:
                    return requests_data
                return {'error': 'Amazon bloqueou ou conteúdo indisponível', 'url': url, 'error_code': 'AMAZON_BLOCKED_OR_EMPTY'}

            if not self.ensure_driver():
                requests_data = self.scrape_amazon_requests(url)
                if requests_data:
                    return requests_data
                if self.last_error:
                    return {'url': url, **self.last_error}
                return {'error': 'WebDriver não inicializado', 'url': url, 'error_code': 'WEBDRIVER_UNAVAILABLE'}

            resolved_url = self.resolve_amazon_url(url)
            logger.info(f"Acessando Amazon: {url} -> {resolved_url}")
            if not self.navigate_with_wait(resolved_url, wait_seconds=2, ready_timeout=8):
                requests_data = self.scrape_amazon_requests(resolved_url or url)
                if requests_data:
                    requests_data.setdefault('original_url', url)
                    return requests_data
                if self.last_error:
                    return {'url': url, **self.last_error}
                return {'error': 'Falha ao abrir página no Selenium', 'url': url, 'error_code': 'AMAZON_NAV_FAIL'}
            self.try_accept_amazon_cookies()

            # Detectar possível captcha/bloqueio
            try:
                page_source = self.driver.page_source
                if self.is_blocked_page(page_source) or 'type the characters you see' in page_source.lower():
                    if self.retry_if_blocked(wait_seconds=2, ready_timeout=8):
                        requests_data = self.scrape_amazon_requests(resolved_url or url)
                        if requests_data:
                            requests_data.setdefault('original_url', url)
                            return requests_data
                        if self.last_error:
                            return {'url': url, **self.last_error}
                        return {'error': 'Amazon apresentou captcha/bloqueio', 'url': url, 'error_code': 'AMAZON_CAPTCHA'}
                    page_source = self.driver.page_source
                if self.is_blocked_page(page_source) or 'type the characters you see' in page_source.lower():
                    requests_data = self.scrape_amazon_requests(resolved_url or url)
                    if requests_data:
                        requests_data.setdefault('original_url', url)
                        return requests_data
                    if self.last_error:
                        return {'url': url, **self.last_error}
                    return {'error': 'Amazon apresentou captcha/bloqueio', 'url': url, 'error_code': 'AMAZON_CAPTCHA'}
            except Exception:
                pass
            
            data = {'url': url, 'resolved_url': resolved_url}
            
            # Título
            title = self.extract_title_from_selectors([
                '#productTitle',
                'h1#productTitle',
                '.a-size-large.product-title-word-break',
                'h1.a-size-large',
                'h1[data-asin]',
                '#title span',
                '#title'
            ], min_len=5)
            if title:
                data['title'] = title
                logger.info(f"Título encontrado: {title}")
            
            # Preço
            price_text = self.extract_amazon_price()
            if price_text:
                formatted, price_val = self.clean_price(price_text)
                if formatted:
                    data['price'] = formatted
                    data['price_value'] = price_val
                    logger.info(f"Preço encontrado: {price_text} -> {formatted}")
            
            # Imagem
            img_src = self.extract_image_from_selectors([
                '#landingImage',
                '#imgTagWrapperId img',
                '.a-dynamic-image',
                'img[data-a-hires]',
                'img[data-old-hires]'
            ])
            if img_src:
                data['image_url'] = img_src
                logger.info(f"Imagem encontrada: {img_src}")

            if self.has_any_data(data):
                return data

            # Fallback com requests quando Selenium não retorna dados
            fallback_url = resolved_url or url
            requests_data = self.scrape_amazon_requests(fallback_url)
            if requests_data:
                requests_data.setdefault('original_url', url)
                return requests_data

            if self.last_error:
                return {'url': url, **self.last_error}
            return {'error': 'Nenhum dado encontrado na Amazon', 'url': url, 'error_code': 'AMAZON_NO_DATA'}
            
        except Exception as e:
            logger.error(f"Erro ao extrair dados da Amazon: {e}")
            self.set_last_error("AMAZON_SCRAPE_EXCEPTION", "Erro ao extrair dados da Amazon", error=str(e))
            return {'error': str(e), 'url': url, 'error_code': 'AMAZON_SCRAPE_EXCEPTION'}
    
    def scrape_mercadolivre(self, url):
        """Extrai dados do Mercado Livre com Selenium"""
        try:
            self.clear_last_error()
            # Primeiro tentar via requests
            if not ALWAYS_USE_SELENIUM:
                requests_data = self.scrape_mercadolivre_requests(url)
                if requests_data:
                    return requests_data
            if IS_PRODUCTION and not ALLOW_SELENIUM_IN_PROD:
                requests_data = self.scrape_mercadolivre_requests(url)
                if requests_data:
                    return requests_data
                return {'error': 'Mercado Livre bloqueou ou conteúdo indisponível', 'url': url, 'error_code': 'MERCADOLIVRE_BLOCKED_OR_EMPTY'}

            if not self.ensure_driver():
                requests_data = self.scrape_mercadolivre_requests(url)
                if requests_data:
                    return requests_data
                if self.last_error:
                    return {'url': url, **self.last_error}
                return {'error': 'WebDriver não inicializado', 'url': url, 'error_code': 'WEBDRIVER_UNAVAILABLE'}

            logger.info(f"Acessando Mercado Livre: {url}")
            if not self.navigate_with_wait(url, wait_seconds=2, ready_timeout=8):
                requests_data = self.scrape_mercadolivre_requests(url)
                if requests_data:
                    requests_data.setdefault('original_url', url)
                    return requests_data
                if self.last_error:
                    return {'url': url, **self.last_error}
                return {'error': 'Falha ao abrir página no Selenium', 'url': url, 'error_code': 'MERCADOLIVRE_NAV_FAIL'}

            try:
                page_source = self.driver.page_source
                if self.is_blocked_page(page_source):
                    if self.retry_if_blocked(wait_seconds=2, ready_timeout=8):
                        requests_data = self.scrape_mercadolivre_requests(url)
                        if requests_data:
                            requests_data.setdefault('original_url', url)
                            return requests_data
                        if self.last_error:
                            return {'url': url, **self.last_error}
                        return {'error': 'Mercado Livre apresentou captcha/bloqueio', 'url': url, 'error_code': 'MERCADOLIVRE_CAPTCHA'}
                    page_source = self.driver.page_source
                if self.is_blocked_page(page_source):
                    requests_data = self.scrape_mercadolivre_requests(url)
                    if requests_data:
                        requests_data.setdefault('original_url', url)
                        return requests_data
                    if self.last_error:
                        return {'url': url, **self.last_error}
                    return {'error': 'Mercado Livre apresentou captcha/bloqueio', 'url': url, 'error_code': 'MERCADOLIVRE_CAPTCHA'}
            except Exception:
                pass
            
            data = {'url': url}
            
            # Título
            title_selectors = [
                '.poly-component__title',
                'h1.ui-pdp-title',
                '.ui-pdp-title'
            ]
            title = self.extract_title_from_selectors(title_selectors, min_len=5)
            if title:
                data['title'] = title
                logger.info(f"Título encontrado: {title}")
            
            # Preço
            price_selectors = [
                '.poly-price__current .andes-money-amount--cents-superscript .andes-money-amount__fraction',
                '.poly-price__current .andes-money-amount__fraction',
                '.ui-pdp-price__current .andes-money-amount__fraction'
            ]
            formatted, price_val = self.extract_price_from_selectors(price_selectors)
            if formatted:
                data['price'] = formatted
                data['price_value'] = price_val
                logger.info(f"Preço encontrado: {formatted}")
            
            # Imagem
            image_selectors = [
                '.poly-component__picture',
                '.ui-pdp-gallery__figure__image',
                'img[src*="http2.mlstatic.com"]'
            ]
            img_src = self.extract_image_from_selectors(image_selectors)
            if img_src:
                data['image_url'] = img_src
                logger.info(f"Imagem encontrada: {img_src}")

            if self.has_any_data(data):
                return data

            # Fallback com requests quando Selenium não retorna dados
            requests_data = self.scrape_mercadolivre_requests(url)
            if requests_data:
                requests_data.setdefault('original_url', url)
                return requests_data

            if self.last_error:
                return {'url': url, **self.last_error}
            return {'error': 'Nenhum dado encontrado no Mercado Livre', 'url': url, 'error_code': 'MERCADOLIVRE_NO_DATA'}
            
        except Exception as e:
            logger.error(f"Erro ao extrair dados do Mercado Livre: {e}")
            self.set_last_error("MERCADOLIVRE_SCRAPE_EXCEPTION", "Erro ao extrair dados do Mercado Livre", error=str(e))
            return {'error': str(e), 'url': url, 'error_code': 'MERCADOLIVRE_SCRAPE_EXCEPTION'}
    
    def scrape_magazineluiza(self, url):
        """Extrai dados do Magazine Luiza com Selenium - Versão Simplificada"""
        try:
            self.clear_last_error()
            if IS_PRODUCTION and not ALLOW_SELENIUM_IN_PROD:
                return {'error': 'Magazine Luiza bloqueou ou conteúdo indisponível', 'url': url, 'error_code': 'MAGALU_BLOCKED_OR_EMPTY'}

            if not self.ensure_driver():
                if self.last_error:
                    return {'url': url, **self.last_error}
                return {'error': 'WebDriver não inicializado', 'url': url, 'error_code': 'WEBDRIVER_UNAVAILABLE'}

            logger.info(f"Acessando Magazine Luiza: {url}")
            
            # Configurar driver para Magazine Luiza
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            if not self.navigate_with_wait(url, wait_seconds=3, ready_timeout=10):
                if self.last_error:
                    return {'url': url, **self.last_error}
                return {'error': 'Falha ao abrir página no Selenium', 'url': url, 'error_code': 'MAGALU_NAV_FAIL'}

            try:
                page_source = self.driver.page_source
                if self.is_blocked_page(page_source):
                    if self.retry_if_blocked(wait_seconds=2, ready_timeout=8):
                        return {'error': 'Magazine Luiza apresentou captcha/bloqueio', 'url': url, 'error_code': 'MAGALU_CAPTCHA'}
                    page_source = self.driver.page_source
                if self.is_blocked_page(page_source):
                    return {'error': 'Magazine Luiza apresentou captcha/bloqueio', 'url': url, 'error_code': 'MAGALU_CAPTCHA'}
            except Exception:
                pass
            
            # Esperar carregamento completo
            try:
                WebDriverWait(self.driver, 8).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
            except TimeoutException:
                logger.warning("Timeout aguardando carregamento completo, continuando...")
            
            # Verificar se houve redirecionamento
            current_url = self.driver.current_url
            logger.info(f"URL atual após carregamento: {current_url}")
            
            # Se já está na página do produto, não precisa procurar botões
            if '/p/' in current_url:
                logger.info("Já está na página do produto, extraindo dados diretamente...")
            else:
                # Procurar por links diretos do produto na página
                try:
                      all_links = self.driver.find_elements(By.TAG_NAME, 'a')
                      logger.info(f"Verificando {len(all_links)} links na página...")

                      for link in all_links:
                          try:
                              href = link.get_attribute('href')
                              if href and ('/p/' in href and ('magazineluiza' in href or 'magalu' in href)):
                                  logger.info(f"Link do produto encontrado: {href}")
                                  self.navigate_with_wait(href, wait_seconds=3, ready_timeout=8)
                                  break
                          except:
                              continue
                except Exception as e:
                    logger.debug(f"Erro ao procurar links: {e}")
            
            data = {'url': url}
            
            # Título - seletores baseados no HTML real da página de divulgador
            title_selectors = [
                # HTML real da página de divulgador - prioridade máxima
                'h2[data-testid="heading"]',
                'h2.break-words.text-on-surface-2.font-xsm-regular',
                'h2.break-words.text-on-surface-2',
                'h2.text-on-surface-2.font-xsm-regular',
                'h2[data-testid="heading"]',
                
                # Página de produto (fallback)
                'h1[data-testid="heading-product-title"]',
                'h1.sc-dcJsrY.jjGTqv',
                'h2[data-testid="heading-product-title"]',
                '[data-testid="product-title"]',
                
                # Genéricos
                '[data-testid="heading"]',
                '.break-words',
                '.text-on-surface-2',
                '[class*="heading"]',
                '[class*="title"]',
                '[class*="product"]',
                '[class*="name"]',
                'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                'title',
                'div', 'span', 'p'
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
            
            # Preço - seletores baseados no HTML real da página de divulgador
            price_selectors = [
                # HTML real da página de divulgador - prioridade máxima
                'p[data-testid="price-value"]',
                'p.text-on-surface-2.font-xlg-bold.md\\:font-2xlg-bold',
                'p[data-testid="price-original"]',
                'p.text-on-surface-3.font-xsm-regular',
                
                # Página de produto (fallback)
                'p.sc-dcJsrY.hsCKLu.sc-cXPBUD.kYFKbo',
                'p.sc-dcJsrY.cHdUaZ.sc-cezyBN.kwGnVt',
                '[data-testid="price-value"]',
                '[data-testid="price"]',
                '[data-testid="price-current"]',
                
                # Genéricos
                '.font-xlg-bold',
                '.font-2xlg-bold',
                '.font-bold',
                '[class*="price"]',
                '[data-testid*="price"]',
                '[class*="valor"]',
                '[class*="money"]',
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
            
            # Imagem - seletores baseados no HTML real da página de divulgador
            image_selectors = [
                # HTML real da página de divulgador - prioridade máxima
                'img[data-testid="image"][alt*="Imagem do produto"]',
                'img[data-testid="image"][alt*="produto"]',
                'img[alt*="Imagem do produto"]',
                'img[alt*="imagem do produto"]',
                'img[alt*="produto"]',
                'img[alt*="Produto"]',
                
                # Página de produto (fallback)
                'img[data-testid="image-selected-thumbnail"]',
                'img.sc-hzhJZQ.knorgy',
                'img[data-testid="media-gallery-image"]',
                'img.sc-hzhJZQ.dCUEWm',
                
                # Domínios específicos - prioridade para a-static.mlcdn.com.br
                'img[src*="a-static.mlcdn.com.br"]',
                'img[src*="mlcdn.com.br"]',
                'img[src*="wx.mlcdn.com.br"]',
                'img[src*="magazineluiza.com.br"]',
                'img[src*="magalu.com.br"]',
                
                # Genéricos
                'img[decoding="auto"]',
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
            
            if self.has_any_data(data):
                return data
            if self.last_error:
                return {'url': url, **self.last_error}
            return {'error': 'Nenhum dado encontrado no Magazine Luiza', 'url': url, 'error_code': 'MAGALU_NO_DATA'}
            
        except Exception as e:
            logger.error(f"Erro ao extrair dados do Magazine Luiza: {e}")
            self.set_last_error("MAGALU_SCRAPE_EXCEPTION", "Erro ao extrair dados do Magazine Luiza", error=str(e))
            return {'error': str(e), 'url': url}
    
    def scrape_shopee(self, url):
        """Extrai dados do Shopee com Selenium"""
        try:
            self.clear_last_error()
            # Primeiro tentar via requests
            if not ALWAYS_USE_SELENIUM:
                requests_data = self.scrape_shopee_requests(url)
                if requests_data:
                    return requests_data
            if IS_PRODUCTION and not ALLOW_SELENIUM_IN_PROD:
                requests_data = self.scrape_shopee_requests(url)
                if requests_data:
                    return requests_data
                return {'error': 'Shopee bloqueou ou conteúdo indisponível', 'url': url, 'error_code': 'SHOPEE_BLOCKED_OR_EMPTY'}

            if not self.ensure_driver():
                requests_data = self.scrape_shopee_requests(url)
                if requests_data:
                    return requests_data
                if self.last_error:
                    return {'url': url, **self.last_error}
                return {'error': 'WebDriver não inicializado', 'url': url, 'error_code': 'WEBDRIVER_UNAVAILABLE'}

            logger.info(f"Acessando Shopee: {url}")
            if not self.navigate_with_wait(url, wait_seconds=3, ready_timeout=10):
                requests_data = self.scrape_shopee_requests(url)
                if requests_data:
                    requests_data.setdefault('original_url', url)
                    return requests_data
                if self.last_error:
                    return {'url': url, **self.last_error}
                return {'error': 'Falha ao abrir página no Selenium', 'url': url, 'error_code': 'SHOPEE_NAV_FAIL'}

            try:
                page_source = self.driver.page_source
                if self.is_blocked_page(page_source):
                    if self.retry_if_blocked(wait_seconds=2, ready_timeout=10):
                        requests_data = self.scrape_shopee_requests(url)
                        if requests_data:
                            requests_data.setdefault('original_url', url)
                            return requests_data
                        if self.last_error:
                            return {'url': url, **self.last_error}
                        return {'error': 'Shopee apresentou captcha/bloqueio', 'url': url, 'error_code': 'SHOPEE_CAPTCHA'}
                    page_source = self.driver.page_source
                if self.is_blocked_page(page_source):
                    requests_data = self.scrape_shopee_requests(url)
                    if requests_data:
                        requests_data.setdefault('original_url', url)
                        return requests_data
                    if self.last_error:
                        return {'url': url, **self.last_error}
                    return {'error': 'Shopee apresentou captcha/bloqueio', 'url': url, 'error_code': 'SHOPEE_CAPTCHA'}
            except Exception:
                pass
            
            data = {'url': url}
            
            # Título
            title_selectors = [
                'span[data-testid="pdp-product-title"]',
                '.product-briefing__title',
                'h1'
            ]
            title = self.extract_title_from_selectors(title_selectors, min_len=5)
            if title:
                data['title'] = title
                logger.info(f"Título encontrado: {title}")
            
            # Preço
            price_selectors = [
                'span[data-testid="pdp-price"]',
                'div.IZPeQz.B67UQ0',
                'div.IZPeQz',
                '.current-price',
                '.product-briefing__price .current-price'
            ]
            formatted, price_val = self.extract_price_from_selectors(price_selectors)
            if formatted:
                data['price'] = formatted
                data['price_value'] = price_val
                logger.info(f"Preço encontrado: {formatted}")
            
            # Imagem
            image_selectors = [
                'img[data-testid="pdp-product-image"]',
                '.product-briefing__image',
                'img[src*="susercontent"]'
            ]
            img_src = self.extract_image_from_selectors(image_selectors)
            if img_src:
                data['image_url'] = img_src
                logger.info(f"Imagem encontrada: {img_src}")

            if self.has_any_data(data):
                return data

            # Fallback com requests quando Selenium não retorna dados
            requests_data = self.scrape_shopee_requests(url)
            if requests_data:
                requests_data.setdefault('original_url', url)
                return requests_data

            if self.last_error:
                return {'url': url, **self.last_error}
            return {'error': 'Nenhum dado encontrado na Shopee', 'url': url, 'error_code': 'SHOPEE_NO_DATA'}
            
        except Exception as e:
            logger.error(f"Erro ao extrair dados do Shopee: {e}")
            self.set_last_error("SHOPEE_SCRAPE_EXCEPTION", "Erro ao extrair dados da Shopee", error=str(e))
            return {'error': str(e), 'url': url, 'error_code': 'SHOPEE_SCRAPE_EXCEPTION'}
    
    def scrape_product(self, url):
        """Função principal de scraping"""
        try:
            site = self.identify_site(url)
            logger.info(f"Site identificado: {site}")
            if BASE_SCRAPE_DELAY_SECONDS > 0:
                logger.info(f"Aguardando base delay de {BASE_SCRAPE_DELAY_SECONDS}s antes do scraping")
                time.sleep(BASE_SCRAPE_DELAY_SECONDS)
            
            if site == 'amazon':
                return self.scrape_amazon(url)
            elif site == 'mercadolivre':
                return self.scrape_mercadolivre(url)
            elif site == 'magazineluiza':
                return self.scrape_magazineluiza(url)
            elif site == 'shopee':
                return self.scrape_shopee(url)
            else:
                return {'error': f'Site não suportado: {site}', 'url': url, 'error_code': 'SITE_UNSUPPORTED'}
                
        except Exception as e:
            logger.error(f"Erro no scraping: {e}")
            return {'error': str(e), 'url': url}
    
    def generate_message(self, product_data, free_shipping=False, coupon_name=None, coupon_discount=None):
        """Gera mensagem padronizada para WhatsApp com emojis"""
        try:
            title = product_data.get('title', 'Produto não encontrado')
            price = product_data.get('price', 'Preço não encontrado')
            
            # Usar strings Unicode diretas para garantir emojis
            fire = "🔥"
            shopping = "🛍️"
            diamond = "💎"
            truck = "🚚"
            brazil = "🇧🇷"
            ticket = "🎟️"
            clock = "⏰"
            finger = "👇"
            island = "🏝️"
            link = "🔗"
            sparkles = "✨"
            
            message = f"{fire}{fire} *SUPER OFERTA EXCLUSIVA!* {fire}{fire}\n\n"
            message += f"{shopping} *PRODUTO:* {title}\n\n"
            message += f"{diamond} *PREÇO ESPECIAL:* {price}\n"
            
            if free_shipping:
                message += f"{truck} *FRETE GRÁTIS* para todo Brasil! {brazil}\n"
            
            if coupon_name and coupon_discount:
                message += f"{ticket} *CUPOM EXTRA:* {coupon_name} - {coupon_discount}% DE DESCONTO!\n"
            
            message += f"\n{clock} *CORRA! OFERTA POR TEMPO LIMITADO!* {clock}\n\n"
            message += f"{finger} *GARANTA JÁ O SEU:* {finger}\n"
            message += f"{product_data.get('original_url', product_data.get('url', ''))}\n\n"
            message += f"{island} *Free Island - As melhores ofertas da internet!* {island}\n"
            message += f"{link} *Mais promoções:* {LINKTREE_URL}\n\n"
            message += f"{sparkles} *Aproveite! Compre agora e economize muito!* {sparkles}"
            
            return message
            
        except Exception as e:
            logger.error(f"Erro ao gerar mensagem: {e}")
            return "Erro ao gerar mensagem"
    
    def save_to_supabase(self, product_data, message):
        """Salva no Supabase"""
        try:
            if not SUPABASE_URL or not SUPABASE_KEY_SERVICE:
                logger.error("Supabase não configurado no ambiente")
                return False

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
    
    if not LOGIN_EMAIL or not LOGIN_SENHA:
        logger.error("Credenciais de login não configuradas no ambiente")
        return render_template('login.html', error='Login indisponível. Configure as credenciais no ambiente.')

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
        request_id = str(uuid.uuid4())
        start = time.time()
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            payload, status = error_response("URL_MISSING", "URL não fornecida", 400, request_id=request_id)
            return jsonify(payload), status
        
        # Fazer scraping
        product_data = scraper.scrape_product(url)
        
        if 'error' in product_data:
            details = {
                "source": "scrape_product",
                "site": scraper.identify_site(url),
                "error_code": product_data.get("error_code")
            }
            payload, status = error_response("SCRAPE_FAILED", product_data['error'], 502, details=details, request_id=request_id)
            log_event(logging.ERROR, "scrape_failed", request_id=request_id, url=url, details=details)
            return jsonify(payload), status
        
        # Gerar mensagem
        free_shipping = data.get('free_shipping', False)
        coupon_name = data.get('coupon_name')
        coupon_discount = data.get('coupon_discount')
        
        if isinstance(product_data, dict):
            product_data.setdefault('original_url', url)
        message = scraper.generate_message(
            product_data, 
            free_shipping, 
            coupon_name, 
            coupon_discount
        )

        elapsed_ms = int((time.time() - start) * 1000)
        missing_fields = [k for k in ("title", "price", "image_url") if not product_data.get(k)]
        if missing_fields:
            log_event(
                logging.WARNING,
                "scrape_partial",
                request_id=request_id,
                url=url,
                site=scraper.identify_site(url),
                missing=missing_fields
            )
        log_event(logging.INFO, "scrape_success", request_id=request_id, url=url, elapsed_ms=elapsed_ms)
        return jsonify({
            'product': product_data,
            'message': message,
            'success': True,
            'request_id': request_id
        })
        
    except Exception as e:
        log_event(logging.ERROR, "scrape_exception", error=str(e))
        payload, status = error_response("SCRAPE_EXCEPTION", str(e), 500)
        return jsonify(payload), status

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
