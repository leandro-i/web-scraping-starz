#!/usr/bin/env python
# -*- coding: utf-8 -*-

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from time import sleep


# Declaración de variables

URL_SERIES = 'https://www.starz.com/ar/es/series'
URL_PELICULAS = 'https://www.starz.com/ar/es/movies'

tiempo_default = 10


# Opciones del driver

options = Options()
options.add_argument('--start-maximized')
options.add_argument('--disable-extensions')
options.add_experimental_option("detach", True)
options.add_experimental_option('excludeSwitches', ['enable-logging'])


def obtener_links(url, css_selector, tiempo=tiempo_default):
    """Función obtener_links: Extrae los links de los elementos accedidos, mediante css_selector, de una URL.

    Args:
        url (str): URL de la página a realizar el scraping
        css_selector (str): Selector CSS de los elementos a capturar.
        tiempo (int, optional): Tiempo de espera para la carga de la página. Default: tiempo_default.

    Returns:
        list: Lista de los links de los elementos.

    Raises:
        NoSuchElementException: En caso de que no existan o no carguen los elementos en el tiempo especificado.
        Suma 10 segundos al tiempo de espera y vuelve a ejecutar la función, hasta un máximo de 30 segundos.
    """
    
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get(url)
        
        sleep(tiempo)
        
        lista_elementos = driver.find_elements(By.CSS_SELECTOR, css_selector)
        
        
        # Scrollear hacia abajo y cargar los elementos
        
        i = 1
        alto_ventana = driver.execute_script('return window.innerHeight;')
        alto_pagina = driver.execute_script('return document.documentElement.scrollHeight;')
        
        while alto_ventana*i < alto_pagina:
            alto_pagina = driver.execute_script('return document.documentElement.scrollHeight;')
            driver.execute_script(f'window.scrollTo(0, {alto_ventana * i});')
            sleep(3)
            
            lista_elementos.extend(driver.find_elements(By.CSS_SELECTOR, css_selector))
            
            i = i + 1
        
        
        # Obtener los href de los elementos a
        
        lista_links = []
        
        for elemento in lista_elementos:
            link = elemento.get_attribute('href')
            lista_links.append(link)
            
        driver.quit()
        
        lista_links = list(set(lista_links))
        
        return lista_links
    
    except NoSuchElementException:
        if tiempo >= 30:
            return
        obtener_links(url, css_selector, tiempo + 10)


def obtener_datos_series(url, tiempo=tiempo_default):
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get(url)
        
        sleep(tiempo)
    except NoSuchElementException:
        if tiempo >= 30:
            return
        obtener_datos_series(url, tiempo + 10)