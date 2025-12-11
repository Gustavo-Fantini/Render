#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ProScraper - Shopee Extractor Final
Usa Chrome normal do usuário com Selenium para extração robusta
"""

from flask import Flask, request, jsonify
import subprocess
import time
import logging
import os
import re
from typing import Dict, Optional
import json

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class ShopeeExtractorFinal:
    """Extrator final para Shopee usando Chrome do usuário"""
    
    def __init__(self):
        self.chrome_path = self._find_chrome_path()
        self.debug_port = 9222
        
    def _find_chrome_path(self) -> Optional[str]:
        """Encontra o caminho do Chrome no sistema"""
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
        ]
        
        for path in chrome_paths:
            if os.path.exists(path):
                logger.info(f"Chrome encontrado em: {path}")
                return path
        
        logger.error("Chrome não encontrado no sistema")
        return None
    
    def extract(self, url: str) -> Dict:
        """Extrai dados do Shopee usando Chrome do usuário"""
        data = {
            'success': False,
            'title': None,
            'price_current': None,
            'price_original': None,
            'rating': None,
            'image_url': None,
            'errors': []
        }
        
        try:
            logger.info(f"Iniciando extração: {url}")
            
            # Resolver URL encurtada
            if 's.shopee.com.br' in url or 's.shopee.com' in url:
                logger.info("Resolvendo URL encurtada...")
                try:
                    import requests
                    response = requests.get(url, timeout=5, allow_redirects=True)
                    url = response.url
                    logger.info(f"URL resolvida: {url[:80]}...")
                except Exception as e:
                    logger.warning(f"Erro ao resolver URL: {e}")
                    data['errors'].append(f"Erro ao resolver URL: {str(e)}")
                    return data
            
            # Tentar com Selenium conectado ao Chrome existente
            logger.info("Tentando extração com Selenium...")
            selenium_result = self._extract_with_selenium(url)
            if selenium_result['success']:
                return selenium_result
            else:
                data['errors'].extend(selenium_result['errors'])
            
            logger.warning("Nenhum método funcionou")
        
        except Exception as e:
            logger.error(f"Erro geral: {e}")
            data['errors'].append(f"Erro geral: {str(e)}")
        
        return data
    
    def _extract_with_selenium(self, url: str) -> Dict:
        """Extrai usando Selenium conectado ao Chrome existente"""
        result = {
            'success': False,
            'title': None,
            'price_current': None,
            'price_original': None,
            'rating': None,
            'image_url': None,
            'errors': []
        }
        
        driver = None
        try:
            logger.info("Iniciando extração com Selenium...")
            
            try:
                from selenium import webdriver
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
            except ImportError:
                logger.error("Selenium não instalado")
                result['errors'].append("Selenium não disponível")
                return result
            
            # Conectar ao Chrome existente via debug port
            logger.info("Conectando ao Chrome via debug port...")
            try:
                options = webdriver.ChromeOptions()
                options.add_experimental_option("debuggerAddress", f"127.0.0.1:{self.debug_port}")
                driver = webdriver.Chrome(options=options)
                logger.info("Conectado ao Chrome existente")
            except Exception as e:
                logger.warning(f"Não conseguiu conectar ao Chrome existente: {e}")
                logger.info("Iniciando novo Chrome com debug port...")
                
                # Iniciar Chrome com debug port
                if not self.chrome_path:
                    result['errors'].append("Chrome não encontrado")
                    return result
                
                cmd = [
                    self.chrome_path,
                    f"--remote-debugging-port={self.debug_port}",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-popup-blocking",
                    "--disable-prompt-on-repost",
                    "--disable-background-networking",
                    "--disable-client-side-phishing-detection",
                    "--disable-component-extensions-with-background-pages",
                    "--disable-default-apps",
                    "--disable-extensions",
                    "--disable-sync",
                    "--metrics-recording-only",
                    "--mute-audio",
                    "--no-service-autorun",
                    "--password-store=basic",
                    "--use-mock-keychain",
                ]
                
                logger.info(f"Iniciando Chrome: {' '.join(cmd[:3])}")
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(5)  # Aguardar Chrome iniciar
                
                # Conectar ao Chrome
                options = webdriver.ChromeOptions()
                options.add_experimental_option("debuggerAddress", f"127.0.0.1:{self.debug_port}")
                driver = webdriver.Chrome(options=options)
                logger.info("Chrome iniciado e conectado")
            
            # Navegar para a URL
            logger.info(f"Navegando para: {url}")
            driver.get(url)
            
            # Aguardar carregamento
            logger.info("Aguardando carregamento da página...")
            time.sleep(3)
            
            # Extrair dados do HTML
            logger.info("Extraindo dados...")
            
            # Extrair título
            try:
                title_elem = driver.find_element(By.CSS_SELECTOR, 'span[data-testid="pdp-product-title"]')
                title = title_elem.text.strip()
                if title and len(title) > 5 and 'Verifique' not in title:
                    result['title'] = title
                    logger.info(f"Título: {result['title'][:60]}...")
            except:
                try:
                    title_elem = driver.find_element(By.TAG_NAME, 'h1')
                    title = title_elem.text.strip()
                    if title and len(title) > 5:
                        result['title'] = title
                        logger.info(f"Título (fallback): {result['title'][:60]}...")
                except:
                    logger.debug("Título não encontrado")
            
            # Extrair preço
            try:
                price_elem = driver.find_element(By.CSS_SELECTOR, 'span[data-testid="pdp-price"]')
                price_text = price_elem.text.strip()
                if 'R$' in price_text:
                    result['price_current_text'] = price_text
                    match = re.search(r'R\$\s*(\d+[.,]\d+)', price_text)
                    if match:
                        result['price_current'] = float(match.group(1).replace('.', '').replace(',', '.'))
                    logger.info(f"Preço: {price_text}")
            except:
                logger.debug("Preço não encontrado")
            
            # Extrair rating
            try:
                rating_elem = driver.find_element(By.CSS_SELECTOR, '[data-testid="pdp-review-summary-rating"]')
                rating_text = rating_elem.text.strip()
                match = re.search(r'(\d+[.,]?\d*)', rating_text)
                if match:
                    result['rating'] = float(match.group(1).replace(',', '.'))
                    logger.info(f"Rating: {result['rating']}")
            except:
                logger.debug("Rating não encontrado")
            
            # Extrair imagem
            try:
                img_elem = driver.find_element(By.CSS_SELECTOR, 'img[data-testid="pdp-product-image"]')
                result['image_url'] = img_elem.get_attribute('src')
                logger.info("Imagem extraída")
            except:
                logger.debug("Imagem não encontrada")
            
            result['success'] = bool(result['title'] or result['price_current'])
            logger.info(f"Extração concluída: sucesso={result['success']}")
        
        except Exception as e:
            logger.error(f"Erro no Selenium: {e}")
            result['errors'].append(f"Erro no Selenium: {str(e)}")
        
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
        
        return result

# Instância global
extractor = ShopeeExtractorFinal()

@app.route('/analyze', methods=['POST'])
def analyze():
    """Endpoint principal de análise"""
    try:
        data = request.get_json()
        url = data.get('url', '')
        
        if not url:
            return jsonify({'success': False, 'error': 'URL não fornecida'}), 400
        
        logger.info(f"Requisição recebida: {url}")
        
        result = extractor.extract(url)
        
        return jsonify({
            'success': result['success'],
            'data': {
                'fields': {
                    'title': {'value': result['title']},
                    'price_current': {'value': result['price_current']},
                    'price_original': {'value': result['price_original']},
                    'rating': {'value': result['rating']},
                    'image_url': {'value': result['image_url']}
                }
            },
            'errors': result['errors']
        })
    
    except Exception as e:
        logger.error(f"Erro no endpoint: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'version': '2.0-final',
        'chrome_found': extractor.chrome_path is not None
    })

if __name__ == '__main__':
    logger.info("Iniciando ProScraper Final com Chrome do Usuário...")
    if not extractor.chrome_path:
        logger.error("Chrome não encontrado! Instale o Chrome antes de continuar.")
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False, threaded=True)
