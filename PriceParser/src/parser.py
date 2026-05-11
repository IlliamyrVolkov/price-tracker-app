from bs4 import BeautifulSoup
from curl_cffi import requests
import re
import json


class Parser:
    def __init__(self, url):
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        self.url = url

    def _get_html(self) -> str:
        return requests.get(self.url, headers=self.headers, impersonate="chrome110").text

    @staticmethod
    def _clean_price(raw_string: str | int | float) -> float:
        try:
            return int(float(raw_string))
        except ValueError:
            clean_string = "".join(re.findall(r'\d+', str(raw_string)))
            if clean_string:
                return int(clean_string)

        raise ValueError("A price value was found, but there is no number in it")

    def get_price(self) -> float:
        text = self._get_html()
        soup = BeautifulSoup(text, "html.parser")

        scripts = soup.find_all("script", type="application/ld+json")
        for script in scripts:
            try:
                data = json.loads(script.text)

                if isinstance(data, list):
                    item = data[0]
                else:
                    item = data

                if item.get("@type") == "Product":
                    offers = item.get("offers")
                    if offers:
                        if isinstance(offers, list):
                            raw_price = offers[0].get("price")
                        else:
                            raw_price = offers.get("price")

                        if raw_price:
                            return self._clean_price(raw_price)
            except json.JSONDecodeError:
                continue

        price_element = soup.find(attrs={"itemprop": "price"})
        if price_element:
            raw_price = price_element.get("content") or price_element.text
            return Parser._clean_price(str(raw_price))

        raise ValueError("Unable to find price: site does not use standard SEO tags")

