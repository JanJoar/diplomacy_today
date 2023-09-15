import json
import re
from collections import Counter
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader
from tqdm import tqdm

from diplomacy_news.get_backstabbr import get_backstabbr
from diplomacy_news.get_war_map import get_battles_coords, get_war_map
from diplomacy_news.ping_gpt import ping_gpt

countries = ["Austria", "England", "France", "Germany", "Italy", "Russia", "Turkey"]


def main():
    orders, units_by_player, territories, season = get_backstabbr()

    summaries = get_battles(orders, territories)
    news = get_news(summaries)
    #  main_headline = create_main_headline(news)
    main_headline = ""
    news_list = process_news(news)
    standing = get_standing(territories)
    generate_newspaper(news_list, main_headline, season, standing)


def get_battles(orders, territories):
    metadata = json.load(open("diplomacy_news/territories.json"))
    all_regions = get_all_regions(orders)
    battles = check_battles(all_regions, orders, territories)
    battles_orders = get_battles_orders(battles, orders)
    battles_possessions = get_battles_possessions(battles, territories)
    battles_coords = get_battles_coords(battles, metadata)
    summaries = get_summaries(
        battles, battles_orders, battles_possessions, battles_coords
    )
    return summaries


def get_all_regions(orders):
    all_regions = []
    for country, country_orders in orders.items():
        for source, order in country_orders.items():
            involved_regions = get_involved_regions(source, order)
            all_regions += involved_regions
    all_regions = list(set(all_regions))
    return all_regions


def check_battles(all_regions, orders, territories):
    unprocessed_regions = set(all_regions.copy())
    battles = []
    while unprocessed_regions:
        processed_region = unprocessed_regions.pop()

        unchecked_regions = {processed_region}
        checked_regions = set()
        while unchecked_regions:
            unchecked_region = unchecked_regions.pop()
            connected_regions = find_all_connected_regions(
                unchecked_region, orders, territories
            )
            new_regions = connected_regions - checked_regions - set([unchecked_region])
            unchecked_regions = unchecked_regions.union(new_regions)
            checked_regions = checked_regions.union(set([unchecked_region]))
        battles += [checked_regions]
        unprocessed_regions = unprocessed_regions - checked_regions
    battles.sort(key=lambda x: -len(x))
    return battles


def find_all_connected_regions(unchecked_region, orders, territories):
    connected_regions = []
    for country, country_orders in orders.items():
        for source, order in country_orders.items():
            involved_regions = get_involved_regions(source, order)
            if unchecked_region in involved_regions:
                connected_regions += involved_regions
    connected_regions = set(connected_regions)
    return connected_regions


def get_involved_regions(source, order):
    involved_regions = [source]
    if "from" in order:
        involved_regions += [order["from"]]
    if "to" in order:
        involved_regions += [order["to"]]
    return involved_regions


def get_battles_orders(battles, orders):
    battles_orders = []
    for battle in battles:
        battle_orders = get_battle_orders(battle, orders)
        battles_orders += [battle_orders]
    return battles_orders


def get_battle_orders(battle, orders):
    battle_orders = []
    for region in battle:
        for country, country_orders in orders.items():
            for source, order in country_orders.items():
                involved_regions = get_involved_regions(source, order)
                if region in involved_regions:
                    order["origin"] = source
                    order["country"] = country
                    battle_orders += [order]

    battle_orders = list(
        {v["origin"]: v for v in battle_orders}.values()
    )  # make unique
    return battle_orders


def get_battles_possessions(battles, territories):
    battles_possessions = []
    for battle in battles:
        battle_possessions = get_battle_possessions(battle, territories)
        battles_possessions += [battle_possessions]
    return battles_possessions


def get_battle_possessions(battle, territories):
    battle_possessions = []
    for region in battle:
        if region in territories:
            possession = {
                "type": "OCCUPIED",
                "country": territories[region],
                "origin": region,
            }
            battle_possessions += [possession]
    return battle_possessions


def get_summaries(battles, battles_orders, battles_possessions, battles_coords):
    summaries = []
    for i, battle, battle_orders, battle_possessions, battle_coords in zip(
        range(len(battles)),
        battles,
        battles_orders,
        battles_possessions,
        battles_coords,
    ):
        countries_involved = get_countries_involved(battle_orders, battle_possessions)
        pretty_battle_orders = get_pretty_battle_orders(battle_orders)
        pretty_battle_possessions = get_pretty_battle_possessions(battle_possessions)
        battle_map = get_battle_map(battle_coords, i)
        summary = dict(
            countries_involved=countries_involved,
            pretty_battle_orders=pretty_battle_orders,
            pretty_battle_possessions=pretty_battle_possessions,
            battle_map=battle_map,
        )
        summaries += [summary]
    return summaries


def get_countries_involved(battle_orders, battle_possessions):
    countries_ordering = {order["country"] for order in battle_orders}
    countries_possessing = {possession["country"] for possession in battle_possessions}
    countries_involved_list = countries_ordering.union(countries_possessing)
    countries_involved = yaml.dump(list(countries_involved_list))
    return countries_involved


def get_pretty_battle_orders(battle_orders):
    pretty_battle_orders = yaml.dump(battle_orders)
    return pretty_battle_orders


def get_pretty_battle_possessions(battle_possessions):
    territories_by_country = {
        country: get_territories_by_country(country, battle_possessions)
        for country in countries
    }
    territories_by_country = {c: t for c, t in territories_by_country.items() if t}
    pretty_battle_possessions = yaml.dump(territories_by_country)
    return pretty_battle_possessions


def get_territories_by_country(country, battle_possessions):
    territories_by_country = [
        possession["origin"]
        for possession in battle_possessions
        if possession["country"] == country
    ]
    return territories_by_country


def get_news(summaries):
    news = []
    battle_summaries = [s for s in summaries if s["countries_involved"].count("-") > 1]

    for summary in tqdm(battle_summaries):
        piece_of_news = create_piece_of_news_prompt(summary)
        news += [{"newsline": piece_of_news, "summary": summary}]
    other_summaries = "\n".join(
        [
            s["pretty_battle_orders"]
            for s in summaries
            if s["countries_involved"].count("-") == 1
        ]
    )
    other_news = create_other_news_prompt(other_summaries)
    other_news_format = f"Title: In other news...\nSubtitle: Other movements around Europe\nParagraph: {other_news}"
    news += [{"newsline": other_news_format, "summary": other_summaries}]
    return news


def create_piece_of_news_prompt(summary):
    prompt = f"""I will share with you the adjudication of orders from a Diplomacy game.
You will invent the headline for a newspaper that covers European Geopolitics that airs in an alternative 1903. Some territories might be owned by different countries than they were in history.
Invent extra drama and fake people involved.
For each headline, provide a title, subtitle and a paragraph.

Report:
---
Countries_involved:
{summary['countries_involved']}
Territories before the battles:
{summary['pretty_battle_possessions']}
Orders:
{summary['pretty_battle_orders']}
---
Output example:
---
Title: title goes here
Subtitle: subtitle goes here
Paragraph: paragraph goes here
---

Output:"""
    answer = ping_gpt(prompt, temp=1)
    return answer


def create_other_news_prompt(other_summaries):
    prompt = f"""I will share with you the adjudication of orders from a Diplomacy game.
These are only the moves that did not involve any conflict between countries, but these countries could have been in conflicts elsewhere.
You will write a paragraph that will go to the "In other news" section of a newspaper. Try to briefly describe what happened.

Report:
---
{other_summaries}
---

Output:"""
    other_news = ping_gpt(prompt, temp=1)

    return other_news


def create_main_headline(news):
    prompt = f"""I will share with you a series of news from a newspaper covering a Europe at war.
You will invent the main headline for this edition of the newspaper and a sentence briefly listing the news.
Make it dramatic and sensational.

News:
---
{yaml.dump(news)}
---
Output example:
---
Headline: title goes here
Sentence: sentence goes here
---

Output:"""
    answer = ping_gpt(prompt)
    return answer


def process_news(news):
    news_list = []
    for news_meta in news:
        news_piece = news_meta["newsline"]
        news_piece = news_piece.split("Title: ")[1]
        title, news_piece = news_piece.split("Subtitle: ", 1)
        subtitle, paragraph = news_piece.split("Paragraph: ", 1)
        title = title.strip().strip('"')
        subtitle = subtitle.strip().strip('"')
        paragraph = paragraph.strip().strip('"')
        paragraph = re.sub("^In a.*?, ", "", paragraph)
        paragraph = paragraph[0].upper() + paragraph[1:]
        news_list += [
            {"newsline": (title, subtitle, paragraph), "summary": news_meta["summary"]}
        ]
    return news_list


def get_standing(territories):
    standing_list = Counter(territories.values()).most_common()
    standing = [s[0] + " " + str(s[1]) for s in standing_list]
    return standing


def generate_newspaper(news_list, main_headline, season, standing):
    env = Environment(loader=FileSystemLoader("."))
    template = env.get_template("template.html")

    newspaper = template.render(
        news_list=news_list,
        main_headline=main_headline,
        season=season,
        standing=standing,
    )
    Path("index.html").write_text(newspaper)
