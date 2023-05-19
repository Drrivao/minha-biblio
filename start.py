"Minha Biblioteca downloader"

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support.expected_conditions import (
	frame_to_be_available_and_switch_to_it,
	presence_of_all_elements_located
)

from os import name as os_name
from urllib.parse import unquote
from bs4 import BeautifulSoup

from pathlib import Path
from time import sleep
from confs import *

import subprocess
import pyautogui
import requests
import json
import html

import base64
import io
from PIL import Image

import logging
from rich.logging import RichHandler
from rich.console import Console


headers = {
    "Host": "jigsaw.minhabiblioteca.com.br",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/111.0",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.5",
    "x-vitalsource-secure-token": "",
    "x-vitalsource-brand": "integradaminhabiblioteca",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "TE": "trailers"
}


headers_login = {
    "Host": "biblioteca-virtual.com",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/111.0",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Length": "33",
    "Origin": "https://biblioteca-virtual.com",
    "Connection": "keep-alive",
    "Referer": "https://biblioteca-virtual.com/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "TE": "trailers",
}


def livro_tipo(livro_url: str) -> str:
    """
    O código de identificação das páginas segue um padrão
    específico para cada formato disponível do livro.
    """

    epubcfi = None
    if 'epubcfi' in livro_url:
        epubcfi = livro_url.split('epubcfi')[1]
        page_id = None
    else:
        page_id = livro_url.split('/')[-1]

    return epubcfi, page_id


def page_info(livro_url: str) -> tuple[str, str]:
    """
    Iterar todas as páginas do livro até encontrar o capítulo
    correspondente a página a ser baixada.
    """

    epubcfi, page_id = livro_tipo(livro_url)
    for page in pages:
        index = pages.index(page)
        if epubcfi:
            if page["cfi"] == unquote(epubcfi).strip():
                chapter_title = page["chapterTitle"]
                break
        else:
            if page["cfi"] == "/" + page_id:
                chapter_title = page["chapterTitle"]
                break

    return index, chapter_title


def extrair_info_do_livro():
    """
    Esta função irá procurar por informações sobre o conteúdo do livro, incluindo
    os códigos de identificação das páginas.

    - Note que antes é necessário extrair os cookies dentro do frame.
    """

    global pages

    WebDriverWait(driver, 10).until(
        frame_to_be_available_and_switch_to_it(
            (By.CSS_SELECTOR,'iframe[allow="fullscreen"]')
        )
    )

    cookies = driver.get_cookies()
    cookies = {c['name']: c['value'] for c in cookies}

    driver.switch_to.default_content()

    livro_url = driver.current_url
    livro_url = livro_url.split('!')[0]
    livro_id = livro_url.split('/')[5]

    with requests.Session() as session:
        session.headers.update(headers)
        session.cookies.update(cookies)
        r = session.get(f'https://jigsaw.minhabiblioteca.com.br/books/{livro_id}/pages')
        pages = json.loads(r.content)


def escolher_livro():
    # Fazer login
    with requests.Session() as session:
        session.headers.update(headers_login)
        r = session.post('https://biblioteca-virtual.com/authentication', data = f"cpf={CPF}&senha={SENHA}")
        cookies = r.cookies.get_dict()

    # Limpar e adicionar cookies
    biblioteca_url = "https://biblioteca-virtual.com/parceiro/minha-biblioteca/regular"
    driver.get(biblioteca_url)
    driver.delete_all_cookies()
    for cookie_name in cookies:
        driver.add_cookie(
            {
                'name': cookie_name,
                'value': cookies[cookie_name],
            }
        )

    # Abrir biblioteca
    driver.get(biblioteca_url)
    logging.info("Escolha um livro e mantenha a janela do Chrome focada enquanto o download não é iniciado.")
    WebDriverWait(driver, 1800).until(presence_of_all_elements_located((By.XPATH, "//iframe[@allow='fullscreen']")))
    sleep(8)


def activate_auto_save():
    """
    Função para abrir o menu de contexto do browser e ativar o salvamento
    automático da extensão SingleFile.
    """

    element = driver.find_element(By.XPATH, "//iframe[@allow='fullscreen']")
    ActionChains(driver).move_to_element(element).context_click().perform()

    livro_url = driver.current_url.split('!')[0]
    epubcfi, page_id = livro_tipo(livro_url)

    if os_name == "nt":
        d = 9 if epubcfi else 7
    else:
        d = 8 if epubcfi else 7

    for i in range(d):
        pyautogui.press('down')

    pyautogui.press('enter')

    for i in range(7):
        pyautogui.press('down')

    pyautogui.press('enter')
    pyautogui.press('down')
    pyautogui.press('enter')


def baixar_livro():
    global new_dest_path

    while True:
        # Baixar o html ao trocar de página usando a extensão SingleFile
        click_seguinte = "document.querySelector('button[aria-label=\"Seguinte\"]').click()"
        driver.execute_script(click_seguinte)
        sleep(5)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        page_title = soup.title.string.lstrip('Minha Biblioteca: ')

        new_dest_path = down_path.joinpath(page_title)
        new_dest_path.mkdir(parents = True, exist_ok = True)

        livro_url = driver.current_url.split('!')[0]
        index, chapter_title = page_info(livro_url)

        sleep(5)

        file_path = Path(next(down_path.glob('Minha Biblioteca*')))
        new_file_path = Path(new_dest_path).joinpath(f"[{index}] {chapter_title}.html")

        # Extrair o conteúdo de dentro do frame no caso de epubs. Para outros formatos,
        # converter a imagem da página para pdf.
        h_content = html.unescape(file_path.read_bytes().decode())
        soup = BeautifulSoup(h_content, 'html.parser')
        iframe = soup.find('iframe', {'class': 'favre'})
        srcdoc = iframe['srcdoc']

        soup = BeautifulSoup(srcdoc, 'html.parser')
        img = soup.find('img', {'id': 'pbk-page'})

        if img:
            image_data = base64.b64decode(img['src'].split(',')[1])
            image = Image.open(io.BytesIO(image_data))
            image.save(str(new_file_path.with_suffix(".pdf")), "PDF", resolution=100.0)
        else:
            new_file_path.write_text(str(srcdoc), encoding = "utf-8")

        file_path.unlink()

        if index == len(pages) - 1:
            break

    logging.info('Download finalizado!')
    driver.quit()


def main():
    """
    Verificar primeiro se o chromedriver está instalado para, então, prosseguir.
    Lembre-se de que, em algumas distros linux, o chromedriver está disponível
    como pacote.
    """
    global driver

    console.clear()
    try:
        driver = webdriver.Chrome(
            executable_path = 'chromedriver',
            options = options
        )
    except WebDriverException:
        logging.warning("Nenhum chromedriver disponível localmente.")
        driver = webdriver.Chrome(
            service = Service(ChromeDriverManager().install()), options = options
        )

    escolher_livro()
    extrair_info_do_livro()
    activate_auto_save()
    baixar_livro()

    prompt = input("\nConverter todas as partes para um único pdf? S/n: ")
    if prompt != "n":
        subprocess.run(f'python join_parts.py --path {new_dest_path}', shell = True)


console = Console()
logging.basicConfig(
    level=logging.INFO, format="%(message)s",
    handlers=[RichHandler(console=console, markup=True)]
)

if down_path:
    down_path = Path(down_path)
else:
    down_path = Path.home().joinpath("Downloads")
down_path.mkdir(parents = True, exist_ok = True)

options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
options.add_argument(f"--user-data-dir={Path.cwd().joinpath('data')}")
options.add_experimental_option('excludeSwitches', ['enable-logging','enable-automation'])
options.add_experimental_option("prefs", {"download.default_directory" : str(down_path)})

if __name__ == "__main__":
    main()