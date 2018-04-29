from collections import namedtuple
import io
import os
import re
import time
from typing import List

from newspaper import Article
from PIL import Image
from pyvirtualdisplay import Display
import selenium
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.remote.webelement import WebElement
import twitter
import yaml


Publisher = namedtuple("Publisher", ("name", "url", "selector", "remove"))


def all_publishers():
    with open("publishers.yml") as f:
        publishers = yaml.load(f)
    for name, pub in publishers.items():
        pub["remove"] = pub.get("remove", [])
        yield Publisher(name=name, **pub)


def get_article(url: str):
    article = Article(url)
    article.download()
    article.parse()
    article.nlp()
    return article


class PublisherScraper:

    def __init__(self):
        self.display = Display(visible=0, size=(1920, 1080))
        self.display.start()
        options = Options()
        options.set_headless(headless=True)
        self.browser = webdriver.Firefox(firefox_options=options)

    def get_teaser_for(self, *, article: Article, publisher: Publisher):
        try:
            self.browser.get(publisher.url)
            self._remove_obstructions(publisher.remove)
            teaser = self._get_teaser(article, publisher)
        except:
            teaser = None
            print(f"Failed for {publisher.name}")
        finally:
            self.browser.quit()
        return teaser

    def _remove_obstructions(self, selectors: List[WebElement]):
        for selector in selectors:
            elements = self.browser.find_elements_by_css_selector(selector)
            for el in elements:
                script = (
                    "const element = arguments[0];"
                    "element.parentNode.removeChild(element);"
                )
                self.browser.execute_script(script, el)

    def _get_teaser(self, article: Article, publisher: Publisher):
        finder = TeaserFinder(browser=self.browser, article_selector=publisher.selector)
        teaser = finder.get_teaser(article)
        return teaser


class TeaserFinder:

    def __init__(self, *, browser, article_selector: str):
        self.browser = browser
        self.selector = article_selector

    def get_teaser(self, article: Article):
        candidates = self.browser.find_elements_by_css_selector(self.selector)
        teaser_element = self._find_best_candidate(article.keywords, candidates)

        if not teaser_element:
            return None

        img_data = teaser_element.screenshot_as_png
        image = Image.open(io.BytesIO(img_data))
        return image

    def _find_best_candidate(self, keywords: List[str], elements: List[WebElement]):
        scores = {}
        for e in elements:
            text = e.text.lower()
            score = sum(1 for t in keywords if t in text)
            scores[e] = score
        best = max(scores, key=(lambda k: scores[k]))
        scores = {e: s for e, s in scores.items() if s == scores[best]}
        best = max(scores, key=(lambda e: e.size["width"] * e.size["height"]))
        best = best if scores[best] >= 2 else None
        return best


Breaking = namedtuple("Breaking", ("text", "url"))


class Twitter:

    def __init__(self):
        self.api = twitter.Api(
            consumer_key=os.getenv("CONSUMER_KEY"),
            consumer_secret=os.getenv("CONSUMER_SECRET"),
            access_token_key=os.getenv("ACCESS_TOKEN"),
            access_token_secret=os.getenv("ACCESS_TOKEN_SECRET"),
        )

    def get_breaking_news(self):
        timeline = self.api.GetUserTimeline(screen_name="BBCBreaking")
        latest = timeline[0].text
        latest_url = latest.split(" ")[-1]
        text = latest.replace(latest_url, "").strip()
        breaking = Breaking(text, latest_url)
        return [breaking]

    def post_teasers(self, text: str, teasers: List[str]):
        self.api.PostUpdate(text, media=teasers)


def get_teasers(breaking: Breaking):
    publishers = all_publishers()
    article = get_article(breaking.url)
    teasers = []
    for pub in publishers:
        scraper = PublisherScraper()
        teaser = scraper.get_teaser_for(article=article, publisher=pub)
        if teaser:
            fname = f"{pub.name}.png"
            teaser.save(fname)
            yield fname


def main():
    tweet = Twitter()
    breaking_news = tweet.get_breaking_news()
    for breaking in breaking_news:
        teasers = list(get_teasers(breaking))
        if teasers:
            tweet.post_teasers(breaking.text, teasers)


if __name__ == "__main__":
    main()
