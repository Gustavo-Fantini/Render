import requests
import re
import json
import time
import logging
from urllib.parse import urljoin, urlparse
from typing import Dict, Optional, Tuple
from datetime import datetime
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class SimpleScraper:
    """Scraper simplificado para extrair apenas título, preço e imagem"""
    
    def __init__(self):
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Cria sessão HTTP robusta"""
        session = requests.Session()
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        session.headers.update(headers)
        session.timeout = 10
        
        return session
    
    def _identify_site(self, url: str) -> str:
        """Identifica o site pela URL"""
        domain = urlparse(url).netloc.lower()
        
        if any(d in domain for d in ['mercadolivre.com', 'mercadolivre.com.br', 'ml.com.br', 'ml.com']):
            return 'mercadolivre'
        elif any(d in domain for d in ['amazon.com.br', 'amzn.to']):
            return 'amazon'
        elif any(d in domain for d in ['shopee.com.br', 's.shopee.com.br']):
            return 'shopee'
        
        return 'unknown'
    
    def _clean_price(self, text: str) -> Tuple[Optional[str], Optional[float]]:
        """Limpa e formata preço"""
        if not text:
            return None, None
        
        original = text.strip()
        logger.info(f"Processando preço: '{original}'")
        
        # Limpar caracteres não numéricos
        clean = re.sub(r'[^\d.,]', '', text)
        
        if not clean:
            return original, None
        
        try:
            # Lógica para preços brasileiros
            if ',' in clean and '.' in clean:
                # Determinar separador decimal
                last_comma = clean.rfind(',')
                last_dot = clean.rfind('.')
                
                if last_comma > last_dot:
                    # Formato brasileiro: 1.234,89
                    clean = clean.replace('.', '').replace(',', '.')
                else:
                    # Formato americano: 1,234.89
                    clean = clean.replace(',', '')
            elif '.' in clean:
                # Verificar se é separador de milhares ou decimal
                parts = clean.split('.')
                if len(parts) == 2 and len(parts[1]) == 3:
                    # É separador de milhares: 1.099 -> 1099
                    clean = clean.replace('.', '')
                # Se tem múltiplos pontos, tratar como separadores de milhares
                elif len(parts) > 2:
                    clean = clean.replace('.', '')
            elif ',' in clean:
                # Verificar se é separador decimal ou de milhares
                parts = clean.split(',')
                if len(parts) == 2 and len(parts[1]) <= 2:
                    # É separador decimal: 1234,56
                    clean = clean.replace(',', '.')
                else:
                    # É separador de milhares: 1,234 ou 1,234,567
                    clean = clean.replace(',', '')
            
            # Converter para float
            price_float = float(clean)
            
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
    
    def _resolve_short_url(self, url: str) -> str:
        """Resolve URLs encurtadas"""
        try:
            logger.info(f"Resolvendo URL: {url}")
            response = self.session.head(url, allow_redirects=True, timeout=10)
            final_url = response.url
            logger.info(f"URL resolvida: {final_url}")
            return final_url
        except Exception as e:
            logger.warning(f"Erro ao resolver URL: {e}")
            return url
    
    def _scrape_amazon(self, soup: BeautifulSoup, url: str) -> Dict:
        """Extrai dados da Amazon (simplificado)"""
        data = {'url': url}
        
        logger.info("Iniciando scraping Amazon...")
        
        # Título - mais seletores
        title_selectors = [
            '#productTitle',  # ID principal
            '.a-size-large.product-title-word-break',  # Classe principal
            'h1.a-size-large',  # h1 com classe
            'h1[data-asin]',  # h1 com atributo ASIN
            '.product-title',
            'h1[id*="title"]',  # Qualquer h1 com title no ID
            '[data-automation-id="title"]',  # Elemento com automation ID
            'meta[property="og:title"]'  # Meta tag fallback
        ]
        
        for selector in title_selectors:
            try:
                if selector.startswith('meta'):
                    elem = soup.find('meta', property='og:title')
                    if elem and elem.get('content'):
                        data['title'] = elem.get('content').strip()
                        logger.info(f"Título encontrado via meta: {data['title']}")
                        break
                else:
                    elem = soup.select_one(selector)
                    if elem:
                        title = elem.get_text(strip=True)
                        if title and len(title) > 5:
                            data['title'] = title
                            logger.info(f"Título encontrado via {selector}: {title}")
                            break
            except Exception as e:
                logger.debug(f"Erro no seletor de título '{selector}': {e}")
                continue
        
        # Preço - mais abordagens
        price_selectors = [
            # Preço principal (com desconto)
            '.a-price.aok-align-center.reinventPricePriceToPayMargin.priceToPay',
            '.a-price.aok-align-center.reinventPricePriceToPayMargin.priceToPay .a-price-whole',
            '.a-price.aok-align-center.reinventPricePriceToPayMargin.priceToPay .a-price-fraction',
            # Preços alternativos
            '.a-price-current',
            '.a-price .a-offscreen',
            '.a-price-whole',
            '.a-price-fraction',
            'span.a-price-whole',
            '.a-price.a-size-medium.a-color-price',
            '.a-price.a-text-price.a-size-medium.apexPriceToPay',
            'span[data-a-color="price"]',
            'meta[property="product:price:amount"]'
        ]
        
        for selector in price_selectors:
            try:
                if selector.startswith('meta'):
                    elem = soup.find('meta', property='product:price:amount')
                    if elem and elem.get('content'):
                        price_text = f"R$ {elem.get('content')}"
                        formatted, price_val = self._clean_price(price_text)
                        if formatted:
                            data['price_current_text'] = formatted
                            data['price_current'] = price_val
                            logger.info(f"Preço encontrado via meta: {price_text}")
                            break
                else:
                    elem = soup.select_one(selector)
                    if elem:
                        price_text = elem.get_text(strip=True)
                        logger.info(f"Elemento de preço encontrado via {selector}: '{price_text}'")
                        
                        if 'R$' in price_text or any(c.isdigit() for c in price_text):
                            formatted, price_val = self._clean_price(price_text)
                            if formatted:
                                data['price_current_text'] = formatted
                                data['price_current'] = price_val
                                logger.info(f"Preço processado: {price_text} -> {formatted}")
                                break
            except Exception as e:
                logger.debug(f"Erro no seletor de preço '{selector}': {e}")
                continue
        
        # Imagem - mais seletores
        image_selectors = [
            '#landingImage',  # ID principal
            '.a-dynamic-image',  # Classe principal
            'img[data-testid="product-image"]',  # Imagem do produto
            '.a-spacing-small .imgTagWrapper img',  # Wrapper da imagem
            '#imgBlkFront',  # Imagem frontal
            '.a-dynamic-image-container img',  # Container dinâmico
            'img[alt*="Product"]',  # Qualquer imagem com Product no alt
            'img[src*="images"]',  # Qualquer imagem com images no src
            'meta[property="og:image"]'  # Meta tag fallback
        ]
        
        for selector in image_selectors:
            try:
                if selector.startswith('meta'):
                    elem = soup.find('meta', property='og:image')
                    if elem and elem.get('content'):
                        data['image_url'] = elem.get('content')
                        logger.info(f"Imagem encontrada via meta: {data['image_url']}")
                        break
                else:
                    elem = soup.select_one(selector)
                    if elem:
                        img_src = elem.get('src') or elem.get('data-src')
                        if img_src and 'http' in img_src:
                            data['image_url'] = img_src
                            logger.info(f"Imagem encontrada via {selector}: {img_src}")
                            break
            except Exception as e:
                logger.debug(f"Erro no seletor de imagem '{selector}': {e}")
                continue
        
        # Log do resultado
        title_found = bool(data.get('title'))
        price_found = bool(data.get('price_current'))
        image_found = bool(data.get('image_url'))
        
        logger.info(f"Scraping Amazon - Título: {title_found}, Preço: {price_found}, Imagem: {image_found}")
        
        if title_found and price_found:
            logger.info("Scraping Amazon bem-sucedido!")
        else:
            logger.warning("Scraping Amazon parcial ou falhou")
        
        return data
    
    def _scrape_mercadolivre(self, soup: BeautifulSoup, url: str) -> Dict:
        """Extrai dados do Mercado Livre (simplificado)"""
        data = {'url': url}
        
        # Título
        title_selectors = [
            '.ui-pdp-title',
            'h1.ui-pdp-title',
            '.ui-item__title',
            'meta[property="og:title"]'
        ]
        
        for selector in title_selectors:
            try:
                if selector.startswith('meta'):
                    elem = soup.find('meta', property='og:title')
                    if elem and elem.get('content'):
                        data['title'] = elem.get('content').strip()
                        break
                else:
                    elem = soup.select_one(selector)
                    if elem:
                        title = elem.get_text(strip=True)
                        if title and len(title) > 5:
                            data['title'] = title
                            break
            except Exception as e:
                logger.debug(f"Erro no seletor de título '{selector}': {e}")
                continue
        
        # Preço (priorizar preço com desconto)
        price_selectors = [
            # Preço com desconto (prioridade) - baseado no HTML real
            '.poly-price__current .andes-money-amount__fraction',
            '.poly-price__current .andes-money-amount',
            '.andes-money-amount--cents-superscript .andes-money-amount__fraction',
            '.ui-pdp-price__second-line .andes-money-amount__fraction',
            '.ui-pdp-price__second-line .price-tag-fraction',
            '.ui-pdp-price__current .andes-money-amount__fraction',
            '.ui-pdp-price__current .price-tag-fraction',
            '.andes-money-amount-combo__main .andes-money-amount__fraction',
            '.ui-pdp-price__discount-and-cents .andes-money-amount__fraction',
            '.price-tag-12 .price-tag-fraction',
            '.andes-money-amount__fraction[aria-hidden="true"]',
            # Preço padrão (fallback)
            '.andes-money-amount__fraction',
            '.price-tag-fraction',
            '.ui-item__price .price-tag-fraction'
        ]
        
        for selector in price_selectors:
            try:
                elem = soup.select_one(selector)
                if elem:
                    price_text = elem.get_text(strip=True)
                    if price_text.isdigit() or ',' in price_text:
                        # Tentar obter os centavos
                        cents_selector = selector.replace('fraction', 'cents')
                        cents_elem = soup.select_one(cents_selector)
                        if cents_elem:
                            cents_text = cents_elem.get_text(strip=True)
                            full_price = f"{price_text},{cents_text}"
                        else:
                            full_price = price_text
                        
                        formatted, price_val = self._clean_price(f"R$ {full_price}")
                        if formatted:
                            data['price_current_text'] = formatted
                            data['price_current'] = price_val
                            break
            except Exception as e:
                logger.debug(f"Erro no seletor de preço '{selector}': {e}")
                continue
        
        # Imagem
        image_selectors = [
            '.ui-pdp-gallery__figure__image',
            '.ui-pdp-gallery img',
            '.gallery-image-container img',
            'meta[property="og:image"]'
        ]
        
        for selector in image_selectors:
            try:
                if selector.startswith('meta'):
                    elem = soup.find('meta', property='og:image')
                    if elem and elem.get('content'):
                        data['image_url'] = elem.get('content')
                        break
                else:
                    elem = soup.select_one(selector)
                    if elem:
                        img_src = elem.get('src') or elem.get('data-src')
                        if img_src and 'http' in img_src:
                            data['image_url'] = img_src
                            break
            except Exception as e:
                logger.debug(f"Erro no seletor de imagem '{selector}': {e}")
                continue
        
        return data
    
    def _scrape_shopee(self, soup: BeautifulSoup, url: str) -> Dict:
        """Extrai dados do Shopee (simplificado)"""
        data = {'url': url}
        
        # Título
        title_selectors = [
            'span[data-testid="pdp-product-title"]',
            '.product-briefing__title',
            'h1',
            'meta[property="og:title"]'
        ]
        
        for selector in title_selectors:
            try:
                if selector.startswith('meta'):
                    elem = soup.find('meta', property='og:title')
                    if elem and elem.get('content'):
                        data['title'] = elem.get('content').strip()
                        break
                else:
                    elem = soup.select_one(selector)
                    if elem:
                        title = elem.get_text(strip=True)
                        if title and len(title) > 5:
                            data['title'] = title
                            break
            except Exception as e:
                logger.debug(f"Erro no seletor de título '{selector}': {e}")
                continue
        
        # Preço (priorizar preço com desconto)
        price_selectors = [
            # Preço com desconto (prioridade)
            'span[data-testid="pdp-price"]',
            '.current-price',
            '.product-briefing__price .current-price',
            '.price-with-discount',
            '[class*="current-price"]',
            # Preço padrão (fallback)
            '.product-briefing__price',
            '[class*="price"]'
        ]
        
        for selector in price_selectors:
            try:
                elem = soup.select_one(selector)
                if elem:
                    price_text = elem.get_text(strip=True)
                    if 'R$' in price_text or any(c.isdigit() for c in price_text):
                        formatted, price_val = self._clean_price(price_text)
                        if formatted:
                            data['price_current_text'] = formatted
                            data['price_current'] = price_val
                            break
            except Exception as e:
                logger.debug(f"Erro no seletor de preço '{selector}': {e}")
                continue
        
        # Imagem
        image_selectors = [
            'img[data-testid="pdp-product-image"]',
            '.product-briefing__image',
            'img[src*="susercontent"]',
            'meta[property="og:image"]'
        ]
        
        for selector in image_selectors:
            try:
                if selector.startswith('meta'):
                    elem = soup.find('meta', property='og:image')
                    if elem and elem.get('content'):
                        data['image_url'] = elem.get('content')
                        break
                else:
                    elem = soup.select_one(selector)
                    if elem:
                        img_src = elem.get('src') or elem.get('data-src')
                        if img_src and 'http' in img_src:
                            data['image_url'] = img_src
                            break
            except Exception as e:
                logger.debug(f"Erro no seletor de imagem '{selector}': {e}")
                continue
        
        return data
    
    def scrape_product(self, url: str) -> Dict:
        """Função principal de scraping simplificado"""
        try:
            logger.info(f"Iniciando scraping simplificado: {url}")
            
            # Manter URL original para retorno
            original_url = url
            
            # Resolver URL encurtada se necessário apenas para scraping
            scrape_url = url
            if any(domain in url.lower() for domain in ['amzn.to', 's.shopee.com.br']):
                scrape_url = self._resolve_short_url(url)
            
            # Identificar site
            site = self._identify_site(url)
            logger.info(f"Site identificado: {site}")
            
            # Fazer requisição com URL resolvida
            response = self.session.get(scrape_url, timeout=10)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extrair dados baseado no site
            if site == 'amazon':
                data = self._scrape_amazon(soup, original_url)  # Usar URL original
            elif site == 'mercadolivre':
                data = self._scrape_mercadolivre(soup, original_url)  # Usar URL original
            elif site == 'shopee':
                data = self._scrape_shopee(soup, original_url)  # Usar URL original
            else:
                logger.warning(f"Site não suportado: {site}")
                return {'error': f'Site não suportado: {site}'}
            
            # Adicionar informações adicionais
            data['original_url'] = original_url
            data['scrape_url'] = scrape_url
            data['site'] = site
            
            # Log do resultado
            title_found = bool(data.get('title'))
            price_found = bool(data.get('price_current'))
            image_found = bool(data.get('image_url'))
            
            logger.info(f"Scraping concluído - Sucesso: {title_found and price_found}")
            logger.info(f"Scraping bem-sucedido - Título: {title_found}, Preço: {price_found}, Imagem: {image_found}")
            
            return data
            
        except requests.RequestException as e:
            logger.error(f"Erro de requisição: {e}")
            return {'error': f'Erro de requisição: {str(e)}'}
        except Exception as e:
            logger.error(f"Erro no scraping: {e}")
            return {'error': f'Erro no scraping: {str(e)}'}
