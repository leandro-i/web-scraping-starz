#!/usr/bin/env python
# -*- coding: utf-8 -*-

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from time import sleep


# Declaración de constantes

URL_SERIES = 'https://www.starz.com/ar/es/series'
URL_PELICULAS = 'https://www.starz.com/ar/es/movies'