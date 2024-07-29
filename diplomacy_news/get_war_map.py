import os
import io
from pathlib import Path

import cairosvg
from bs4 import BeautifulSoup
from PIL import Image

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.firefox.service import Service as FirefoxService

service = FirefoxService(executable_path=GeckoDriverManager().install())
driver = webdriver.Firefox(service=service)

def get_war_map(url):
    svg_element = get_svg_element(url)

    #  Path("/tmp/lol.svg").write_text(str(svg_element))
    background_image = Image.open("assets/map_background.png")
    png_data = cairosvg.svg2png(
        str(svg_element),
        parent_width=background_image.size[0],
        parent_height=background_image.size[1],
    )
    png_image = Image.open(io.BytesIO(png_data))
    background_image = background_image.resize(png_image.size)
    composite_image = Image.alpha_composite(
        background_image.convert("RGBA"), png_image.convert("RGBA")
    )
    output_image = "assets/map.png"
    composite_image.save(output_image, "PNG")


def get_svg_element(url):
    options = Options()
    options.add_argument("headless")
    s = FirefoxService(executable_path=GeckoDriverManager().install())
    driver = webdriver.Firefox(service=s, options=options)
    driver.maximize_window()
    driver.get(url)
    element = driver.find_element(By.XPATH, '//*[@id="map"]').get_attribute("innerHTML")
    driver.quit()

    if element:
        bs = BeautifulSoup(element, "lxml")
        svg_element = bs.find("svg")
    else:
        svg_element = ""

    return svg_element


def get_battle_map(battle_coords, i):
    image = Image.open("assets/map.png")
    cropped_image = image.crop(battle_coords)
    filename = f"assets/battle{i}.png"
    cropped_image.save(filename)
    return filename


def get_battles_coords(battles, metadata):
    battles_coords = [get_battle_coords(battle, metadata) for battle in battles]
    return battles_coords


def get_battle_coords(battle, metadata):
    battle_coords = [
        get_territoritory_coords(territory, metadata) for territory in battle
    ]
    battle_coords = get_4_extremes(battle_coords)
    battle_coords = make_square(battle_coords)
    return battle_coords


def get_territoritory_coords(territory, metadata):
    img_width = 604
    width = 609
    img_height = 560
    height = 559
    ter_path = metadata[territory]["path"]
    full_ter_path = [t[1:].split(",") for t in ter_path.split()]
    full_ter_path = [[int(i.replace("Z", "")) for i in t] for t in full_ter_path]
    full_ter_path = [t for t in full_ter_path if len(t) == 2]
    full_ter_path = [
        [t[0] / width * img_width, t[1] / height * img_height] for t in full_ter_path
    ]
    coords = get_2_extremes(full_ter_path)
    return coords


def get_2_extremes(full_ter_path):
    x1 = min([t[0] for t in full_ter_path])
    x2 = max([t[0] for t in full_ter_path])
    y1 = min([t[1] for t in full_ter_path])
    y2 = max([t[1] for t in full_ter_path])
    coords = (x1, y1, x2, y2)
    return coords


def get_4_extremes(battle_coords):
    x1 = min([t[0] for t in battle_coords])
    y1 = min([t[1] for t in battle_coords])
    x2 = max([t[2] for t in battle_coords])
    y2 = max([t[3] for t in battle_coords])
    coords = (x1, y1, x2, y2)
    return coords


def make_square(battle_coords):
    img_width = 604
    img_height = 560
    new_battle_coords = list(battle_coords)
    coord_width = battle_coords[2] - battle_coords[0]
    coord_height = battle_coords[3] - battle_coords[1]
    diff = coord_height - coord_width
    if diff > 0:
        new_battle_coords[0] -= diff / 2
        new_battle_coords[2] += diff / 2
        if new_battle_coords[0] < 0:
            new_battle_coords[2] -= new_battle_coords[0]
            new_battle_coords[0] = 0
        if new_battle_coords[2] > img_width:
            new_battle_coords[0] -= new_battle_coords[2] - img_width
            new_battle_coords[2] = img_width
    if diff < 0:
        new_battle_coords[1] -= abs(diff) / 2
        new_battle_coords[3] += abs(diff) / 2
        if new_battle_coords[1] < 0:
            new_battle_coords[3] -= new_battle_coords[1]
            new_battle_coords[1] = 0
        if new_battle_coords[3] > img_height:
            new_battle_coords[1] -= new_battle_coords[3] - img_height
            new_battle_coords[3] = img_height
    return tuple(new_battle_coords)
