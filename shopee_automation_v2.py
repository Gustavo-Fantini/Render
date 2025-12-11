#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Shopee Automation V2
Inicia Chrome com debug port, abre link encurtado, faz scraping com Selenium
"""

from flask import Flask, request, jsonify
import subprocess
import time
import logging
import os
import re
from typing import Dict, Optional
import threading

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class ShopeeAutomationV2:
    """Automação Shopee com Chrome debug port"""
    
    def __init__(self):
        self.chrome_path = self._find_chrome_path()
        self.debug_port = 9222
        self.chrome_process = None
        
    def _find_chrome_path(self) -> Optional[str]:
        """Encontra o caminho do Chrome"""
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
        ]
        
        for path in chrome_paths:
            if os.path.exists(path):
                logger.info(f"Chrome encontrado em: {path}")
                return path
        
        logger.error("Chrome não encontrado")
        return None
    
    def extract(self, url: str) -> Dict:
        """Extrai dados do Shopee"""
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
            
            # Iniciar Chrome com debug port
            logger.info("Iniciando Chrome com debug port...")
            self._start_chrome_with_debug()
            time.sleep(3)
            
            # Navegar para URL
            logger.info("Navegando para URL...")
            self._navigate_to_url(url)
            time.sleep(8)
            
            # Extrair com Selenium
            logger.info("Extraindo com Selenium...")
            selenium_result = self._extract_with_selenium()
            
            if selenium_result['success']:
                return selenium_result
            else:
                data['errors'].extend(selenium_result['errors'])
            
            logger.warning("Extração falhou")
        
        except Exception as e:
            logger.error(f"Erro: {e}")
            data['errors'].append(str(e))
        
        finally:
            self._cleanup_chrome()
        
        return data
    
    def _start_chrome_with_debug(self):
        """Inicia Chrome com debug port"""
        if not self.chrome_path:
            raise Exception("Chrome não encontrado")
        
        try:
            # Matar Chrome existente
            try:
                subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe'], 
                             capture_output=True, timeout=5)
                time.sleep(1)
            except:
                pass
            
            # Iniciar Chrome com debug port
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
            
            logger.info("Iniciando Chrome...")
            self.chrome_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            logger.info("Chrome iniciado com sucesso")
        
        except Exception as e:
            logger.error(f"Erro ao iniciar Chrome: {e}")
            raise
    
    def _navigate_to_url(self, url: str):
        """Navega para URL usando Selenium"""
        try:
            from selenium import webdriver
            
            options = webdriver.ChromeOptions()
            options.add_experimental_option("debuggerAddress", f"127.0.0.1:{self.debug_port}")
            
            driver = webdriver.Chrome(options=options)
            logger.info(f"Navegando para: {url}")
            driver.get(url)
            driver.quit()
            
            logger.info("Navegação concluída")
        
        except Exception as e:
            logger.error(f"Erro ao navegar: {e}")
            raise
    
    def _extract_with_selenium(self) -> Dict:
        """Extrai dados com Selenium"""
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
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            logger.info("Conectando ao Chrome...")
            options = webdriver.ChromeOptions()
            options.add_experimental_option("debuggerAddress", f"127.0.0.1:{self.debug_port}")
            
            driver = webdriver.Chrome(options=options)
            logger.info("Conectado ao Chrome")
            
            # Aguardar título
            logger.info("Aguardando carregamento...")
            try:
                wait = WebDriverWait(driver, 10)
                wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "span[data-testid='pdp-product-title']")
                ))
            except:
                logger.warning("Timeout aguardando elemento")
            
            # Extrair título
            try:
                title_elem = driver.find_element(By.CSS_SELECTOR, 'span[data-testid="pdp-product-title"]')
                title = title_elem.text.strip()
                if title and len(title) > 5:
                    result['title'] = title
                    logger.info(f"Título: {title[:60]}...")
            except Exception as e:
                logger.debug(f"Erro título: {e}")
            
            # Extrair preço
            try:
                price_elem = driver.find_element(By.CSS_SELECTOR, 'span[data-testid="pdp-price"]')
                price_text = price_elem.text.strip()
                if 'R$' in price_text:
                    result['price_current_text'] = price_text
                    match = re.search(r'R\$\s*(\d+[.,]\d+)', price_text)
                    if match:
                        result['price_current'] = float(
                            match.group(1).replace('.', '').replace(',', '.')
                        )
                    logger.info(f"Preço: {price_text}")
            except Exception as e:
                logger.debug(f"Erro preço: {e}")
            
            # Extrair rating
            try:
                rating_elem = driver.find_element(By.CSS_SELECTOR, '[data-testid="pdp-review-summary-rating"]')
                rating_text = rating_elem.text.strip()
                match = re.search(r'(\d+[.,]?\d*)', rating_text)
                if match:
                    result['rating'] = float(match.group(1).replace(',', '.'))
                    logger.info(f"Rating: {result['rating']}")
            except Exception as e:
                logger.debug(f"Erro rating: {e}")
            
            # Extrair imagem
            try:
                img_elem = driver.find_element(By.CSS_SELECTOR, 'img[data-testid="pdp-product-image"]')
                result['image_url'] = img_elem.get_attribute('src')
                logger.info("Imagem extraída")
            except Exception as e:
                logger.debug(f"Erro imagem: {e}")
            
            result['success'] = bool(result['title'] or result['price_current'])
            logger.info(f"Extração: sucesso={result['success']}")
        
        except Exception as e:
            logger.error(f"Erro Selenium: {e}")
            result['errors'].append(str(e))
        
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
        
        return result
    
    def _cleanup_chrome(self):
        """Limpa processo Chrome"""
        try:
            if self.chrome_process:
                self.chrome_process.terminate()
                self.chrome_process.wait(timeout=5)
        except:
            try:
                subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe'], 
                             capture_output=True, timeout=5)
            except:
                pass

# Instância global
automation = ShopeeAutomationV2()

@app.route('/analyze', methods=['POST'])
def analyze():
    """Endpoint de análise"""
    try:
        data = request.get_json()
        url = data.get('url', '')
        
        if not url:
            return jsonify({'success': False, 'error': 'URL não fornecida'}), 400
        
        logger.info(f"Requisição: {url}")
        
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
        logger.error(f"Erro: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'version': '2.0-automation',
        'chrome_found': automation.chrome_path is not None
    })

if __name__ == '__main__':
    logger.info("Iniciando Shopee Automation V2...")
    if not automation.chrome_path:
        logger.error("Chrome não encontrado!")
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False, threaded=True)
