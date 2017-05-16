import io
from typing import List

from PIL import Image
from selenium.webdriver.remote.webelement import WebElement
from selenium import webdriver

from scraper import publisher


def get_story_teaser(story: str, pub: publisher.Publisher):
    browser = webdriver.PhantomJS()

    browser.set_window_size(1920, 1080)
    browser.get(pub.url)
    browser.execute_script('return document.body.scrollHeight;')

    candidates = browser.find_elements_by_css_selector(pub.selector)
    teaser_element = _best_candidate(story, candidates)

    if not teaser_element:
        return None

    img_data = browser.get_screenshot_as_png()
    teaser = _crop_img_to_element(img_data, teaser_element)
    teaser.show()


def _best_candidate(story: str, elements: List[WebElement]):
    scores = {}
    tokens = story.split()
    for e in elements:
        html = e.get_attribute('innerHTML').lower()
        scores[e] = sum(1 for t in tokens if t in html)
    best = max(scores, key=(lambda k: scores[k]))
    scores = {e: s for e, s in scores.items() if s == scores[best]}
    best = max(scores, key=(lambda e: _element_area(e)))
    return best if scores[best] >= len(tokens) / 2 else None


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

    image = Image.open(io.BytesIO(img_data))
    return image.crop((left, top, right, bottom))


def example():
    publishers = publisher.all_publishers()
    for pub in publishers:
        get_story_teaser('election manifesto pledges almost labour fully new top rate tax', pub)

if __name__ == '__main__':
    example()
