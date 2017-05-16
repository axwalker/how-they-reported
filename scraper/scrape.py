import io
import time
from typing import List

from newspaper import Article
from PIL import Image
from selenium import webdriver
from selenium.webdriver.remote.webelement import WebElement

from scraper import publisher


def get_story_teaser(article: Article, pub: publisher.Publisher):
    browser = webdriver.PhantomJS()

    browser.set_window_size(1920, 1080)
    browser.get(pub.url)

    time.sleep(3)
    browser.execute_script('return document.body.scrollHeight;')
    time.sleep(3)

    candidates = browser.find_elements_by_css_selector(pub.selector)
    teaser_element = _best_candidate(article, candidates)

    if not teaser_element:
        return None

    img_data = browser.get_screenshot_as_png()
    return _crop_img_to_element(img_data, teaser_element)


def _best_candidate(article: Article, elements: List[WebElement]):
    scores = {}
    for e in elements:
        text = e.text.lower()
        score = sum(1 for t in article.keywords if t in text)
        scores[e] = score
    best = max(scores, key=(lambda k: scores[k]))
    scores = {e: s for e, s in scores.items() if s == scores[best]}
    best = max(scores, key=(lambda e: _element_area(e)))
    return best if scores[best] >= 2 else None


def _element_area(element: WebElement):
    size = element.size
    return size['width'] * size['height']


def _crop_img_to_element(img_data: bytes, element: WebElement):
    location = element.location
    size = element.size
    left = location['x']
    top = location['y']
    right = left + size['width']
    bottom = top + size['height']
    return (Image
            .open(io.BytesIO(img_data))
            .crop((left, top, right, bottom)))


def example():
    publishers = publisher.all_publishers()
    article = Article('https://t.co/eKrRfHuq0a')
    article.download()
    article.parse()
    article.nlp()
    for pub in publishers:
        teaser = get_story_teaser(article, pub)
        if teaser:
            teaser.show()

if __name__ == '__main__':
    example()
