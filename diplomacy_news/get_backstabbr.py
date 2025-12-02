import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from diplomacy_news.get_war_map import get_war_map


def get_backstabbr(force=False):
    print("Reading backstabbr...")
    base_url = "https://www.backstabbr.com"
    url = base_url + "/game/FHS-Kandidat/5160556830982144"
    res = requests.get(url)
    bs = BeautifulSoup(res.text, "lxml")
    stage = get_property("stage", res)
    if stage in ["SATISFIED", "NEEDS_BUILDS", "NEEDS_ORDERS"]:
        prev_season = bs.find("a", {"id": "history_previous_season"})["href"]
        url = base_url + prev_season
        res = requests.get(url)
        bs = BeautifulSoup(res.text, "lxml")

        #  stage = json.loads(re.search("var stage = (.*)", res.text)[1][:-1])
    season = bs.find("a", {"id": "history_current_season"})
    if season:
        season = season.text.strip().title()
    previous_news_season = get_previous_news_season()
    if not force and previous_news_season == season:
        return None, None, None, None
    get_war_map(url)
    orders = get_property("orders", res)
    units_by_player = get_property("units_by_player", res)
    territories = get_property("territories", res)
    units_by_player = get_property("unitsByPlayer", res)
    orders = get_property("orders", res)
    return orders, units_by_player, territories, season


def get_property(property_name, res):
    pattern = f"var {property_name} = (.*)"
    match = re.search(pattern, res.text)
    if match:
        property_raw = match[1][:-1]
        property = json.loads(property_raw)
    else:
        property = ""
    return property


def get_previous_news_season():
    print("Getting previous news season...")
    previous_news = Path("templates/index.html").read_text()
    bs = BeautifulSoup(previous_news, "lxml")
    previous_news_season = bs.find("span", {"id": "season"}).text
    return previous_news_season
