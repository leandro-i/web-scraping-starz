#!/usr/bin/env python
# -*- coding: utf-8 -*-

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import InvalidArgumentException
from time import sleep
import re
from urllib.parse import unquote
from datetime import date
import json


# Declaración de variables

URL_SERIES = 'https://www.starz.com/ar/es/series'
URL_PELICULAS = 'https://www.starz.com/ar/es/movies'

SELECTOR_CSS_VER_TODO = 'a.view-all'
SELECTOR_CSS_LINKS = 'starz-content-item article div a:first-of-type'

RUTA_PELICULAS_JSON = 'peliculas.json'
RUTA_SERIES_JSON = 'series.json'
RUTA_CATALOGO_JSON = 'catalogo.json'

tiempo_default = 6


# Opciones del driver

options = Options()
# options.add_argument('--start-maximized')
options.add_argument('--disable-extensions')
options.add_experimental_option("detach", True)
options.add_experimental_option('excludeSwitches', ['enable-logging'])


# Funciones

def obtener_links(url, css_selector, tiempo=tiempo_default):
    """Función obtener_links: Extrae los links de los elementos accedidos, mediante css_selector, de una URL.

    Args:
        url (str): URL de la página a realizar el scraping.
        css_selector (str): Selector CSS de los elementos a capturar.
        tiempo (int, optional): Tiempo de espera para la carga de la página. Default: tiempo_default.

    Returns:
        lista_links (list): Lista de los links de los elementos.

    Raises:
        NoSuchElementException: En caso de que no existan o no carguen los elementos en el tiempo especificado.
        Suma 10 segundos al tiempo de espera y vuelve a ejecutar la función, hasta un máximo de 30 segundos.
        
        InvalidArgumentException: Si la URL no es válida, retorna una lista vacía.
    """
    
    # Limpiar URL
    url = unquote(url)
    
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.set_window_size(1024, 600)
        driver.maximize_window()
        driver.get(url)
        sleep(tiempo)
        
        lista_elementos = driver.find_elements(By.CSS_SELECTOR, css_selector)
                
        
        # Scrollear hacia abajo y cargar los elementos dinámicos
        i = 1
        alto_ventana = driver.execute_script('return window.innerHeight;')
        alto_pagina = driver.execute_script('return document.documentElement.scrollHeight;')
        
        while alto_ventana*i < alto_pagina:
            alto_pagina = driver.execute_script('return document.documentElement.scrollHeight;')
            driver.execute_script(f'window.scrollTo(0, {alto_ventana * i});')
            sleep(tiempo/2)
            
            lista_elementos.extend(driver.find_elements(By.CSS_SELECTOR, css_selector))
            
            i = i + 1
        
        
        # Obtener los href de los elementos a        
        lista_links = []
        
        for elemento in lista_elementos:
            link = elemento.get_attribute('href')
            lista_links.append(link)
            
        driver.quit()
        
        # Filtrar los links repetidos
        lista_links = list(set(lista_links))
        
        return lista_links
    
    except NoSuchElementException:
        if tiempo >= 30:
            return []
        obtener_links(url, css_selector, tiempo + 10)
    
    except InvalidArgumentException:
        return []


def obtener_datos_series(url, tiempo=tiempo_default):
    """Función obtener_datos_series: Recoge los datos de la serie de la URL y los guarda en un diccionario.

    Args:
        url (str): URL de la serie.
        tiempo (int, optional): Tiempo de espera para la carga de la página. Default: tiempo_default.

    Returns:
        datos_serie (dict): Diccionario con los datos recogidos de la serie.
    
    Raises:
        NoSuchElementException: En caso de que no existan o no carguen los elementos en el tiempo especificado.
        Suma 10 segundos al tiempo de espera y vuelve a ejecutar la función, hasta un máximo de 30 segundos.
        
        InvalidArgumentException: Si la URL no es válida, retorna una lista vacía.
    """
    
    # Limpiar URL
    url = unquote(url)
    
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.set_window_size(1024, 600)
        driver.maximize_window()
        driver.get(url)
        sleep(tiempo)
        
        meta = driver.find_element(By.CSS_SELECTOR, 'div.metadata')
        lista_li = meta.find_elements(By.CSS_SELECTOR, 'ul.meta-list li')
        
        titulo = meta.find_element(By.CSS_SELECTOR, '.series-title h1').text
        calificacion = lista_li[0].text
        genero = lista_li[2].text
        año = lista_li[3].text
        año = validar_año(año)
        
        # Eliminar dobles espacios, tabulaciones y saltos de línea
        sinopsis = re.sub(r'(\s{2,})|(\n)|(\t)', ' ', meta.find_element(By.CSS_SELECTOR, 'div.logline p').text)
        
        contenedor_episodios = driver.find_element(By.CSS_SELECTOR, 'div.episodes-container')
        temporadas = contenedor_episodios.find_elements(By.CSS_SELECTOR, 'div.season-number a')
        
        dict_episodios = {}
        
        for i, temporada in enumerate(temporadas):
            lista_episodios = []
            
            episodios =  contenedor_episodios.find_elements(By.CSS_SELECTOR, 'div.episode-container')
            
            if i == 0:                
                link_temporada  = temporada.get_attribute('href')            
            
            for n, episodio in enumerate(episodios, 1):
                episodio_titulo = episodio.find_element(By.CSS_SELECTOR, 'a .title').text                
                episodio_meta = episodio.find_element(By.CSS_SELECTOR, 'a ul.meta-list')
                episodio_lista_li = episodio_meta.find_elements(By.CSS_SELECTOR, 'li')
                episodio_duracion = episodio_lista_li[1].text
                episodio_año = episodio_lista_li[2].text                
                
                # Verificar si es un tráiler
                if 'tráiler' in episodio_titulo.lower() and int(episodio_duracion.split()[0]) < 5:
                    continue
                
                lista_episodios.append({
                    'temporada': i+1,
                    'numero_episodio': n,
                    'titulo': episodio_titulo,
                    'año': episodio_año,
                    'duracion': episodio_duracion,
                    'link_temporada': link_temporada,
                })

            dict_episodios[i+1] = lista_episodios            
            
            # Si hay más temporadas            
            if len(temporadas) > i+1:
                lista_temporadas = contenedor_episodios.find_elements(By.CSS_SELECTOR, 'div.season-number a')
                link_temporada = lista_temporadas[i+1].get_attribute('href')
                
                driver.quit()
                
                driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
                driver.set_window_size(1024, 600)
                driver.maximize_window()
                driver.get(link_temporada)
                sleep(tiempo)
                
                contenedor_episodios = driver.find_element(By.CSS_SELECTOR, 'div.episodes-container')
            
        datos_serie = {
            'titulo': titulo,
            'calificacion': calificacion,
            'genero': genero,
            'año': año,
            'sinopsis': sinopsis,
            'temporadas': len(temporadas),
            'cantidad_de_episodios': len(episodios),
            'episodios': dict_episodios,
            'link': url,
        }
        
        driver.quit()
        print('datos_serie', datos_serie)
        return datos_serie

    except NoSuchElementException:
        if tiempo > 30:
            driver.quit()
            return []
        obtener_datos_series(url, tiempo + 10)
    
    except InvalidArgumentException:
        print('obtener_datos_series url', url)
        driver.quit()
        return []


def obtener_datos_peliculas(url, tiempo=tiempo_default):
    """Función obtener_datos_pelicula: Recoge los datos de la pelicula de la URL y los guarda en un diccionario.

    Args:
        url (str): URL de la pelicula.
        tiempo (int, optional): Tiempo de espera para la carga de la página. Default: tiempo_default.

    Returns:
        datos_pelicula (dict): Diccionario con los datos recogidos de la pelicula.
    
    Raises:
        NoSuchElementException: En caso de que no existan o no carguen los elementos en el tiempo especificado.
        Suma 10 segundos al tiempo de espera y vuelve a ejecutar la función, hasta un máximo de 30 segundos.
        
        InvalidArgumentException: Si la URL no es válida, retorna una lista vacía.
    """
    
    # Limpiar URL    
    url = unquote(url)
    
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.set_window_size(1024, 600)
        driver.maximize_window()
        driver.get(url)
        sleep(tiempo)
        
        meta = driver.find_element(By.CSS_SELECTOR, 'div.metadata')
        lista_li = meta.find_elements(By.CSS_SELECTOR, 'ul.meta-list li')        
        
        # Eliminar 'Ver' y 'Online' del título        
        titulo = meta.find_element(By.CSS_SELECTOR, 'h1.movie-title').text.split(' ', 1)[1].rsplit(' ', 1)[0]
        
        calificacion = lista_li[0].text
        duracion = lista_li[1].text
        genero = lista_li[2].text
        año = lista_li[3].text
        año = validar_año(año)
        
        # Eliminar dobles espacios, tabulaciones y saltos de línea
        sinopsis = re.sub(r'(\s{2,})|(\n)|(\t)', ' ', meta.find_element(By.CSS_SELECTOR, 'div.logline p').text)
        
        datos_pelicula = {
            'titulo': titulo,
            'calificacion': calificacion,
            'genero': genero,
            'año': año,
            'sinopsis': sinopsis,
            'duracion': duracion,
            'link': url,
        }        
        
        driver.quit()
        print('datos_pelicula', datos_pelicula)
        return datos_pelicula
    
    except NoSuchElementException:
        if tiempo > 30:
            driver.quit()
            return []
        obtener_datos_peliculas(url, tiempo + 10)
    
    except InvalidArgumentException:
        print('obtener_datos_peliculas url', url)
        driver.quit()
        return []


def validar_año(st):
    """Función validar_año: Verifica que los años sean entre 1900 y el año actual.
    Si no lo es, retorna un string vacío.

    Args:
        st (str): String del año o los años a validar.
    
    Returns:
        st (str): El mismo string del argumento.
    """
    
    lista = re.findall('\d+', st)
    n = max([int(n) for n in lista if n.isdigit()])
    if 1900 < n <= date.today().year:
        return st
    else:
        return ''



# PELÍCULAS

lista_links_categorias_peliculas = obtener_links(URL_PELICULAS, SELECTOR_CSS_VER_TODO)

lista_links_peliculas = []
for link in lista_links_categorias_peliculas:
    lista_links_peliculas.extend(obtener_links(link, SELECTOR_CSS_LINKS))

# Eliminar películas repetidas
lista_links_peliculas = set(lista_links_peliculas)

dict_peliculas = {}
for i, link in enumerate(lista_links_peliculas):
    dict_peliculas[i+1] = obtener_datos_peliculas(link)



# SERIES

lista_links_categorias_series = obtener_links(URL_SERIES, SELECTOR_CSS_VER_TODO)

lista_links_series = []
for link in lista_links_categorias_series:
    lista_links_series.extend(obtener_links(link, SELECTOR_CSS_LINKS))

# Eliminar series repetidas
lista_links_series = set(lista_links_series)
    
dict_series = {}
for i, link in enumerate(lista_links_series):
    dict_series[i+1] = obtener_datos_series(link)



# Exportar diccionarios a archivos json


with open(RUTA_PELICULAS_JSON, 'w+', encoding='utf8') as file:
    json.dump(dict_peliculas, file, ensure_ascii=False, indent=4)

with open(RUTA_SERIES_JSON, 'w+', encoding='utf8') as file:
    json.dump(dict_series, file, ensure_ascii=False, indent=4)

with open(RUTA_CATALOGO_JSON, 'w+', encoding='utf8') as file:
    dict_catalogo = {
        'series': dict_series,
        'peliculas': dict_peliculas,
    }    
    json.dump(dict_catalogo, file, ensure_ascii=False, indent=4)