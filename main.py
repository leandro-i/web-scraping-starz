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
from unidecode import unidecode
import json
import sqlite3
import os

# Declaración de variables

URL_PELICULAS = 'https://www.starz.com/ar/es/movies'
URL_SERIES = 'https://www.starz.com/ar/es/series'

SELECTOR_CSS_VER_TODO = 'a.view-all'
SELECTOR_CSS_LINKS = 'starz-content-item article div a:first-of-type'

RUTA_PELICULAS_JSON = 'peliculas.json'
RUTA_SERIES_JSON = 'series.json'
RUTA_CATALOGO_JSON = 'catalogo.json'
RUTA_DB = 'db.sqlite3'

tiempo_default = 7
tiempo_maximo_espera = 30


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
        print('obtener_links url', url)
        if tiempo > tiempo_maximo_espera:
            return []
        obtener_links(url, css_selector, tiempo+10)
    
    except InvalidArgumentException:
        print('obtener_links url', url)
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
        
        # Click botón "ver más" si existe
        try:
            driver.find_element(By.CSS_SELECTOR,'div.metadata .more-link.show').click()
            sleep(tiempo/3)
        except NoSuchElementException:
            pass
            
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
        
        cargar_pelicula(datos_pelicula)
        driver.quit()
        return datos_pelicula
    
    except NoSuchElementException:
        if tiempo > tiempo_maximo_espera:
            print('obtener_datos_peliculas url', url)
            driver.quit()
            return []
        obtener_datos_peliculas(url, tiempo+10)
    
    except InvalidArgumentException:
        print('obtener_datos_peliculas url', url)
        driver.quit()
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
        
        meta_serie = driver.find_element(By.CSS_SELECTOR, 'div.metadata')
        titulo_serie = meta_serie.find_element(By.CSS_SELECTOR, '.series-title h1').text
        lista_li_serie = meta_serie.find_elements(By.CSS_SELECTOR, 'ul.meta-list li')
        calificacion_serie = lista_li_serie[0].text
        genero_serie = lista_li_serie[2].text
        año_serie = lista_li_serie[3].text
        año_serie = validar_año(año_serie)
        
        # Eliminar dobles espacios, tabulaciones y saltos de línea
        sinopsis_serie = re.sub(r'(\s{2,})|(\n)|(\t)', ' ', meta_serie.find_element(By.CSS_SELECTOR, 'div.logline p').text)
        
        
        temporadas = driver.find_elements(By.CSS_SELECTOR, 'div.episodes-container div.season-number a')
                
        dict_temporadas = {}
        
        for nro_temporada, temporada in enumerate(temporadas, 1):
            # Click botón "ver más" si existe
            try:
                driver.find_element(By.CSS_SELECTOR,'div.metadata .more-link.more-button.show').click()
                sleep(tiempo/3)
            except NoSuchElementException:
                pass
            
            meta = driver.find_element(By.CSS_SELECTOR, 'div.metadata')
            lista_li = meta.find_elements(By.CSS_SELECTOR, 'ul.meta-list li')
            año = lista_li[3].text
            año = validar_año(año)
            
            # Eliminar dobles espacios, tabulaciones y saltos de línea
            sinopsis = re.sub(r'(\s{2,})|(\n)|(\t)', ' ', meta.find_element(By.CSS_SELECTOR, 'div.logline p').text)
            
            lista_episodios = []    
                
            contenedor_episodios = driver.find_element(By.CSS_SELECTOR, 'div.episodes-container')
            episodios =  contenedor_episodios.find_elements(By.CSS_SELECTOR, 'div.episode-container')
            lista_links_temporadas = contenedor_episodios.find_elements(By.CSS_SELECTOR, 'div.season-number a')
            link_temporada  = unquote(lista_links_temporadas[nro_temporada-1].get_attribute('href'))
            
            for nro_episodio, episodio in enumerate(episodios, 1):
                episodio_titulo = episodio.find_element(By.CSS_SELECTOR, 'a .title').text
                episodio_meta = episodio.find_element(By.CSS_SELECTOR, 'a ul.meta-list')
                episodio_lista_li = episodio_meta.find_elements(By.CSS_SELECTOR, 'li')
                episodio_duracion = episodio_lista_li[1].text
                episodio_año = episodio_lista_li[2].text
                episodio_link = unquote(episodio.find_element(By.CSS_SELECTOR, 'a.episode-link').get_attribute('href'))
                
                # Verificar si es un tráiler
                if 'tráiler' in episodio_titulo.lower() and int(episodio_duracion.split()[0]) < 6:
                    continue
                
                lista_episodios.append({
                    'temporada': nro_temporada,
                    'numero_episodio': nro_episodio,
                    'titulo': episodio_titulo,
                    'año': episodio_año,
                    'duracion': episodio_duracion,
                    'link_episodio': episodio_link,
                })
            
            
            # Datos de cada temporada            
            dict_temporadas[nro_temporada] = {}
            dict_temporadas[nro_temporada]['sinopsis'] = sinopsis
            dict_temporadas[nro_temporada]['año'] = año
            dict_temporadas[nro_temporada]['cantidad_episodios'] = len(lista_episodios)
            dict_temporadas[nro_temporada]['episodios'] = lista_episodios
            dict_temporadas[nro_temporada]['link_temporada'] = link_temporada
                        
            # Si hay más temporadas    
            if len(temporadas) > nro_temporada:
                link_siguiente_temporada = unquote(lista_links_temporadas[nro_temporada].get_attribute('href'))
                driver.quit()                
                driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
                driver.set_window_size(1024, 600)
                driver.maximize_window()
                driver.get(link_siguiente_temporada)
                sleep(tiempo)
        
        # Sumar cantidad de episodios de la serie
        cantidad_episodios_total = 0
        for temporada in dict_temporadas:
            cantidad_episodios_total += dict_temporadas[temporada]['cantidad_episodios']
        
        datos_serie = {
            'titulo': titulo_serie,
            'calificacion': calificacion_serie,
            'genero': genero_serie,
            'año': año_serie,
            'sinopsis': sinopsis_serie,
            'cantidad_de_temporadas': len(temporadas),
            'cantidad_de_episodios': cantidad_episodios_total,
            'temporadas': dict_temporadas,
            'link': url,
        }
        
        cargar_serie(datos_serie)
                
        driver.quit()
        return datos_serie

    except NoSuchElementException:
        if tiempo > tiempo_maximo_espera:
            print('obtener_datos_series url', url)
            driver.quit()
            return []
        obtener_datos_series(url, tiempo + 10)
    
    except InvalidArgumentException:
        print('obtener_datos_series url', url)
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
    try:
        lista = re.findall('\d+', st)
        n = max([int(n) for n in lista if n.isdigit()])
        if 1900 < n <= date.today().year:
            return st
        else:
            return ''
    except ValueError:
        return st

def cargar_pelicula(datos_pelicula):
    """Función cargar_pelicula: Carga un diccionario de la película a la base de datos SQLite especificada.
    
    Args:
        datos_pelicula (dict): Diccionario con los datos de la película.
    
    Raises:
        sqlite3.IntegrityError: Si el link de la película no es UNIQUE.
    """
    
    if not os.path.exists(RUTA_DB):
        open(RUTA_DB, 'a').close()
        
    with sqlite3.connect(RUTA_DB) as con:
        try:
            cursor = con.cursor()
            cursor.execute("""CREATE TABLE IF NOT EXISTS peliculas (
                id_pelicula INTEGER PRIMARY KEY, 
                titulo TEXT, 
                calificacion TEXT, 
                genero TEXT, 
                año TEXT, 
                sinopsis TEXT, 
                duracion TEXT, 
                link TEXT UNIQUE
            );""")
                   
            tupla = (
                datos_pelicula['titulo'], 
                datos_pelicula['calificacion'], 
                datos_pelicula['genero'], 
                datos_pelicula['año'], 
                datos_pelicula['sinopsis'], 
                datos_pelicula['duracion'], 
                datos_pelicula['link']
            )
            cursor.execute("""INSERT INTO peliculas (
                titulo, 
                calificacion, 
                genero, 
                año, 
                sinopsis, 
                duracion, 
                link
            ) VALUES (?, ?, ?, ?, ?, ?, ?);""", tupla)
            con.commit()
        except sqlite3.IntegrityError:
            pass


def cargar_serie(datos_serie):
    """Función cargar_serie: Carga un diccionario de la serie a la base de datos SQLite especificada.
    
    Args:
        datos_serie (dict): Diccionario con los datos de la película.
    
    Raises:
        sqlite3.IntegrityError: Si el link de la serie no es UNIQUE.
    """
    
    if not os.path.exists(RUTA_DB):
        open(RUTA_DB, 'a').close()
        
    with sqlite3.connect(RUTA_DB) as con:
        try:
            cursor = con.cursor()
            cursor.execute("""CREATE TABLE IF NOT EXISTS series (
                id_serie INTEGER PRIMARY KEY, 
                titulo TEXT, calificacion TEXT, 
                genero TEXT, 
                año TEXT, 
                sinopsis TEXT, 
                cantidad_de_temporadas INTEGER, 
                cantidad_de_episodios INTEGER, 
                link TEXT UNIQUE
            );""")
            
            tupla = (
                datos_serie['titulo'], 
                datos_serie['calificacion'], 
                datos_serie['genero'], 
                datos_serie['año'], 
                datos_serie['sinopsis'], 
                datos_serie['cantidad_de_temporadas'], 
                datos_serie['cantidad_de_episodios'], 
                datos_serie['link']
            )
            cursor.execute("""INSERT INTO series (
                titulo, 
                calificacion, 
                genero, 
                año, 
                sinopsis, 
                cantidad_de_temporadas, 
                cantidad_de_episodios, 
                link
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);""", tupla)
            con.commit()
        except sqlite3.IntegrityError:
            pass



# SERIES

lista_links_categorias_series = obtener_links(URL_SERIES, SELECTOR_CSS_VER_TODO)

lista_links_series = []
for link in lista_links_categorias_series:
    lista_links_series.extend(obtener_links(link, SELECTOR_CSS_LINKS))

# Eliminar series repetidas
lista_links_series = set(lista_links_series)

lista_series = []
for link in lista_links_series:
    lista_series.append(obtener_datos_series(link))

# Ordenar lista de series alfabéticamente
lista_series = sorted(lista_series, key=lambda x: unidecode(x['titulo'].lower()))

dict_series = {}
for i, serie in enumerate(lista_series, 1):
    dict_series[i] = serie



# PELÍCULAS

lista_links_categorias_peliculas = obtener_links(URL_PELICULAS, SELECTOR_CSS_VER_TODO)

lista_links_peliculas = []
for link in lista_links_categorias_peliculas:
    lista_links_peliculas.extend(obtener_links(link, SELECTOR_CSS_LINKS))

# Eliminar películas repetidas
lista_links_peliculas = set(lista_links_peliculas)

lista_peliculas = []
for link in lista_links_peliculas:
    lista_peliculas.append(obtener_datos_peliculas(link))

# Ordenar lista de peliculas alfabéticamente
lista_peliculas = sorted(lista_peliculas, key=lambda x: unidecode(x['titulo'].lower()))

dict_peliculas = {}
for i, pelicula in enumerate(lista_peliculas, 1):
    dict_peliculas[i] = pelicula



# Exportar diccionarios a archivos json

with open(RUTA_PELICULAS_JSON, 'w+', encoding='utf8') as file:
    json.dump(dict_peliculas, file, ensure_ascii=False, indent=4)

with open(RUTA_SERIES_JSON, 'w+', encoding='utf8') as file:
    json.dump(dict_series, file, ensure_ascii=False, indent=4)

with open(RUTA_CATALOGO_JSON, 'w+', encoding='utf8') as file:
    dict_catalogo = {
        'peliculas': dict_peliculas,
        'series': dict_series,
    }    
    json.dump(dict_catalogo, file, ensure_ascii=False, indent=4)








