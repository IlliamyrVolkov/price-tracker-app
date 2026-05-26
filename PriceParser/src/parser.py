from bs4 import BeautifulSoup
from curl_cffi import requests
import re
import json


class Parser:
    def __init__(self, url):
        self.headers = {"User-Agent":
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/120.0.0.0 Safari/537.36"}
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

        og_price = soup.find("meta", property="product:price:amount")
        if og_price and og_price.get("content"):
            return self._clean_price(og_price.get("content"))

        main_block = soup.find("div", class_="product-info-main")
        if main_block:
            price_wrapper = main_block.find("span", attrs={"data-price-type": "finalPrice"})
            if price_wrapper:
                price_span = price_wrapper.find("span", class_="price")
                if price_span:
                    raw_text = price_span.text.replace(" ", "").replace("\xa0", "").split(",")[0]
                    return self._clean_price(raw_text)

        scripts = soup.find_all("script", type="application/ld+json")
        for script in scripts:
            try:
                data = json.loads(script.text)
                items = []

                if isinstance(data, list):
                    items.extend(data)
                elif isinstance(data, dict):
                    if "@graph" in data:
                        items.extend(data["@graph"])
                    else:
                        items.append(data)

                for item in items:
                    if isinstance(item, dict) and item.get("@type") == "Product":
                        offers = item.get("offers")
                        if not offers:
                            continue

                        if isinstance(offers, list):
                            offer = offers[0]
                        else:
                            offer = offers

                        raw_price = offer.get("price")
                        if raw_price:
                            return self._clean_price(raw_price)

            except (json.JSONDecodeError, AttributeError):
                continue

        meta_price = soup.find("meta", attrs={"itemprop": "price"})
        if meta_price and meta_price.get("content"):
            return self._clean_price(str(meta_price.get("content")))

        raise ValueError("Unable to find price: site does not use standard SEO tags")
