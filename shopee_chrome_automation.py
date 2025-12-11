#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Shopee Chrome Automation
Abre Chrome normal do usuário, navega para link encurtado, e faz scraping
"""

from flask import Flask, request, jsonify
import subprocess
import time
import logging
import os
import re
from typing import Dict, Optional
import pyautogui
import keyboard

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class ShopeeAutomation:
    """Automação do Shopee com Chrome normal do usuário"""
    
    def __init__(self):
        self.chrome_path = self._find_chrome_path()
        
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
        """Extrai dados do Shopee abrindo Chrome normal"""
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
            logger.info(f"Iniciando automação para: {url}")
            
            # Abrir Chrome com o link
            logger.info("Abrindo Chrome com link do Shopee...")
            self._open_chrome_with_url(url)
            
            # Aguardar carregamento
            logger.info("Aguardando carregamento da página...")
            time.sleep(8)
            
            # Extrair dados com Selenium
            logger.info("Extraindo dados com Selenium...")
            selenium_result = self._extract_with_selenium()
            
            if selenium_result['success']:
                return selenium_result
            else:
                data['errors'].extend(selenium_result['errors'])
            
            logger.warning("Nenhum método funcionou")
        
        except Exception as e:
            logger.error(f"Erro geral: {e}")
            data['errors'].append(f"Erro geral: {str(e)}")
        
        return data
    
    def _open_chrome_with_url(self, url: str):
        """Abre Chrome e navega para a URL"""
        if not self.chrome_path:
            raise Exception("Chrome não encontrado")
        
        try:
            # Abrir Chrome
            logger.info(f"Executando: {self.chrome_path}")
            subprocess.Popen([self.chrome_path])
            time.sleep(3)  # Aguardar Chrome abrir
            
            # Focar na barra de endereço (Ctrl+L)
            logger.info("Focando na barra de endereço...")
            pyautogui.hotkey('ctrl', 'l')
            time.sleep(0.5)
            
            # Digitar URL
            logger.info(f"Digitando URL: {url}")
            pyautogui.typewrite(url, interval=0.01)
            time.sleep(0.5)
            
            # Pressionar Enter
            logger.info("Pressionando Enter...")
            pyautogui.press('enter')
            
            logger.info("Chrome aberto com sucesso")
        
        except Exception as e:
            logger.error(f"Erro ao abrir Chrome: {e}")
            raise
    
    def _extract_with_selenium(self) -> Dict:
        """Extrai dados usando Selenium do Chrome aberto"""
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
            logger.info("Conectando ao Chrome via Selenium...")
            
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
            try:
                options = webdriver.ChromeOptions()
                options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
                driver = webdriver.Chrome(options=options)
                logger.info("Conectado ao Chrome existente")
            except Exception as e:
                logger.warning(f"Não conseguiu conectar: {e}")
                result['errors'].append(f"Não conseguiu conectar ao Chrome: {str(e)}")
                return result
            
            # Aguardar elemento de título
            logger.info("Aguardando elemento de título...")
            try:
                wait = WebDriverWait(driver, 10)
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "span[data-testid='pdp-product-title']")))
                logger.info("Elemento de título encontrado")
            except:
                logger.warning("Timeout aguardando elemento")
            
            # Extrair título
            try:
                title_elem = driver.find_element(By.CSS_SELECTOR, 'span[data-testid="pdp-product-title"]')
                title = title_elem.text.strip()
                if title and len(title) > 5:
                    result['title'] = title
                    logger.info(f"Título: {result['title'][:60]}...")
            except Exception as e:
                logger.debug(f"Erro ao extrair título: {e}")
            
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
            except Exception as e:
                logger.debug(f"Erro ao extrair preço: {e}")
            
            # Extrair rating
            try:
                rating_elem = driver.find_element(By.CSS_SELECTOR, '[data-testid="pdp-review-summary-rating"]')
                rating_text = rating_elem.text.strip()
                match = re.search(r'(\d+[.,]?\d*)', rating_text)
                if match:
                    result['rating'] = float(match.group(1).replace(',', '.'))
                    logger.info(f"Rating: {result['rating']}")
            except Exception as e:
                logger.debug(f"Erro ao extrair rating: {e}")
            
            # Extrair imagem
            try:
                img_elem = driver.find_element(By.CSS_SELECTOR, 'img[data-testid="pdp-product-image"]')
                result['image_url'] = img_elem.get_attribute('src')
                logger.info("Imagem extraída")
            except Exception as e:
                logger.debug(f"Erro ao extrair imagem: {e}")
            
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
automation = ShopeeAutomation()

@app.route('/analyze', methods=['POST'])
def analyze():
    """Endpoint principal de análise"""
    try:
        data = request.get_json()
        url = data.get('url', '')
        
        if not url:
            return jsonify({'success': False, 'error': 'URL não fornecida'}), 400
        
        logger.info(f"Requisição recebida: {url}")
        
        result = automation.extract(url)
        
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
        'version': '3.0-automation',
        'chrome_found': automation.chrome_path is not None
    })

if __name__ == '__main__':
    logger.info("Iniciando Shopee Chrome Automation...")
    if not automation.chrome_path:
        logger.error("Chrome não encontrado! Instale o Chrome antes de continuar.")
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False, threaded=True)
