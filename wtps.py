from collections import namedtuple
import io
import time
from typing import List

from newspaper import Article
from PIL import Image
from selenium import webdriver
from selenium.webdriver.remote.webelement import WebElement
import yaml


Publisher = namedtuple("Publisher", ("name", "url", "selector", "remove"))


def all_publishers():
    with open("publishers.yml") as f:
        publishers = yaml.load(f)
    for name, pub in publishers.items():
        yield Publisher(name=name, **pub)


def get_article(url: str):
    article = Article(url)
    article.download()
    article.parse()
    article.nlp()
    return article


class PublisherScraper:

    def __init__(self):
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        self.browser = webdriver.Chrome(chrome_options=chrome_options)
        self.browser.set_window_size(1920, 1080)

    def get_teaser_for(self, *, article: Article, publisher: Publisher):
        self.browser.get(publisher.url)
        self._remove_obstructions(publisher.remove)
        teaser = self._get_teaser(article, publisher)
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

        # Ensure whole element is in viewport
        height = teaser_element.location["y"] + teaser_element.size["height"]
        self.browser.set_window_size(1920, height)

        img_data = self.browser.get_screenshot_as_png()
        image = self._crop_img_to_element(img_data, teaser_element)
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

    def _crop_img_to_element(self, img_data: bytes, el: WebElement):
        left = el.location["x"]
        top = el.location["y"]
        right = left + el.size["width"]
        bottom = top + el.size["height"]
        image = Image.open(io.BytesIO(img_data))
        image = image.crop((left, top, right, bottom))
        return image


def example():
    publishers = all_publishers()
    article = get_article("http://www.bbc.co.uk/news/world-asia-43921385")
    for pub in publishers:
        scraper = PublisherScraper()
        teaser = scraper.get_teaser_for(article=article, publisher=pub)
        if teaser:
            teaser.save(f"{pub.name}.png")


if __name__ == "__main__":
    example()
