import json
import re
import time
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


class DarazScraper:
    """
    Cleaner Daraz scraper.
    - Gets title
    - Gets price
    - Gets rating
    - Gets total reviews
    - Gets all valid comments up to total review count
    """

    def __init__(self, url: str, headless: bool = True, timeout: int = 20):
        self.url = url
        self.headless = headless
        self.timeout = timeout
        self.driver: Optional[webdriver.Chrome] = None

    # -----------------------------
    # Basic helpers
    # -----------------------------
    @staticmethod
    def clean_text(text: Optional[str]) -> str:
        if not text:
            return ""
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def extract_first_price(text: str) -> str:
        if not text:
            return ""
        match = re.search(r"৳\s*([\d,]+)", text)
        return match.group(1).replace(",", "") if match else ""

    @staticmethod
    def extract_rating_value(text: str) -> str:
        """
        Examples:
        '4.8/5 82 Ratings' -> '4.8'
        '4.5 out of 5' -> '4.5'
        """
        if not text:
            return ""

        match = re.search(r"(\d+(?:\.\d+)?)\s*/\s*5", text)
        if match:
            return match.group(1)

        match = re.search(r"(\d+(?:\.\d+)?)\s*out of\s*5", text, re.I)
        if match:
            return match.group(1)

        return ""

    @staticmethod
    def extract_review_count(text: str) -> str:
        if not text:
            return ""

        patterns = [
            r"(\d+)\s*Ratings",
            r"Ratings\s*(\d+)",
            r"(\d+)\s*Reviews",
            r"Reviews\s*(\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match:
                return match.group(1)

        return ""

    @staticmethod
    def is_rating_summary(text: str) -> bool:
        """
        Ignore lines like:
        '4.8/5 82 Ratings 76 2 1 0 3'
        """
        if not text:
            return False

        if re.search(r"\d+(?:\.\d+)?\s*/\s*5", text) and re.search(r"Ratings?", text, re.I):
            return True

        if re.search(r"\d+(?:\.\d+)?\s*out of\s*5", text, re.I):
            return True

        return False

    @staticmethod
    def safe_int(value: Any, default: int = 0) -> int:
        try:
            return int(str(value).strip())
        except (ValueError, TypeError):
            return default

    @staticmethod
    def safe_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(str(value).strip())
        except (ValueError, TypeError):
            return default

    # -----------------------------
    # Requests part
    # -----------------------------
    def get_soup(self) -> BeautifulSoup:
        response = requests.get(self.url, headers=HEADERS, timeout=self.timeout)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")

    def extract_title_bs(self, soup: BeautifulSoup) -> str:
        h1 = soup.find("h1")
        if h1:
            return self.clean_text(h1.get_text(" ", strip=True))

        meta_title = soup.find("meta", attrs={"property": "og:title"})
        if meta_title and meta_title.get("content"):
            return self.clean_text(meta_title["content"])

        return ""

    def extract_price_bs(self, soup: BeautifulSoup) -> str:
        selectors = [
            "span.pdp-price",
            "span.pdp-price_type_normal",
            "div.pdp-product-price span",
            "span[data-spm='product-price']",
        ]

        for selector in selectors:
            tag = soup.select_one(selector)
            if tag:
                price = self.extract_first_price(tag.get_text(" ", strip=True))
                if price:
                    return price

        return self.extract_first_price(soup.get_text(" ", strip=True))

    def extract_rating_bs(self, soup: BeautifulSoup) -> str:
        page_text = soup.get_text(" ", strip=True)
        return self.extract_rating_value(page_text)

    def extract_total_reviews_bs(self, soup: BeautifulSoup) -> str:
        page_text = soup.get_text(" ", strip=True)
        return self.extract_review_count(page_text)

    def extract_comments_bs(self, soup: BeautifulSoup, review_limit: int) -> List[str]:
        """
        Static HTML comment extraction.
        Returns all valid comments up to review_limit.
        """
        selectors = [
            '[class*="review"]',
            '[class*="comment"]',
            '[class*="feedback"]',
            '[data-spm-anchor-id*="review"]',
        ]

        seen = set()
        comments = []

        for selector in selectors:
            try:
                nodes = soup.select(selector)
                for node in nodes:
                    text = self.clean_text(node.get_text(" ", strip=True))

                    if not text:
                        continue
                    if len(text) < 15:
                        continue
                    if text in seen:
                        continue
                    if self.is_rating_summary(text):
                        continue

                    seen.add(text)
                    comments.append(text)

                    if len(comments) >= review_limit:
                        return comments
            except Exception:
                continue

        return comments

    def scrape_with_requests(self) -> Dict[str, Any]:
        soup = self.get_soup()
        total_reviews = self.extract_total_reviews_bs(soup)
        review_limit = self.safe_int(total_reviews, 0)

        return {
            "title": self.extract_title_bs(soup),
            "price": self.extract_price_bs(soup),
            "rating": self.extract_rating_bs(soup),
            "total_reviews": total_reviews,
            "comments": self.extract_comments_bs(soup, review_limit) if review_limit > 0 else [],
        }

    # -----------------------------
    # Selenium part
    # -----------------------------
    def build_driver(self) -> webdriver.Chrome:
        options = Options()

        if self.headless:
            options.add_argument("--headless=new")

        options.add_argument("--window-size=1400,2000")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument(f"user-agent={HEADERS['User-Agent']}")

        return webdriver.Chrome(options=options)

    def safe_find_texts(self, by: By, selector: str) -> List[str]:
        if not self.driver:
            return []

        try:
            elements = self.driver.find_elements(by, selector)
            return [self.clean_text(el.text) for el in elements if self.clean_text(el.text)]
        except Exception:
            return []

    def extract_comments_selenium(self, review_limit: int) -> List[str]:
        """
        Returns all real comments up to review_limit.
        """
        if not self.driver or review_limit <= 0:
            return []

        seen = set()
        comments = []

        selectors = [
            (By.CSS_SELECTOR, '[class*="review"] [class*="content"]'),
            (By.CSS_SELECTOR, '[class*="comment"]'),
            (By.CSS_SELECTOR, '[class*="review"]'),
            (By.XPATH, "//*[contains(@class,'review') or contains(@class,'comment')]"),
        ]

        last_height = 0
        same_height_count = 0

        for _ in range(12):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            for by, selector in selectors:
                texts = self.safe_find_texts(by, selector)

                for text in texts:
                    if not text:
                        continue
                    if len(text) < 15:
                        continue
                    if text in seen:
                        continue
                    if self.is_rating_summary(text):
                        continue

                    seen.add(text)
                    comments.append(text)

                    if len(comments) >= review_limit:
                        return comments

            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                same_height_count += 1
            else:
                same_height_count = 0

            last_height = new_height

            if same_height_count >= 2:
                break

        return comments

    def scrape_with_selenium(self) -> Dict[str, Any]:
        self.driver = self.build_driver()

        try:
            self.driver.get(self.url)
            time.sleep(5)

            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, "html.parser")

            title = self.extract_title_bs(soup)
            price = self.extract_price_bs(soup)

            full_text = self.driver.find_element(By.TAG_NAME, "body").text
            rating = self.extract_rating_value(full_text)
            total_reviews = self.extract_review_count(full_text)

            review_limit = self.safe_int(total_reviews, 0)
            comments = self.extract_comments_selenium(review_limit)

            return {
                "title": title,
                "price": price,
                "rating": rating,
                "total_reviews": total_reviews,
                "comments": comments,
            }

        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None

    # -----------------------------
    # Main scrape
    # -----------------------------
    def scrape(self) -> Dict[str, Any]:
        empty_result = {
            "title": "",
            "price": 0,
            "rating": 0.0,
            "total_reviews": 0,
            "comments": [],
        }

        try:
            data = self.scrape_with_requests()

            # If comments or rating missing, use selenium fallback
            if not data["comments"] or not data["rating"]:
                selenium_data = self.scrape_with_selenium()

                return {
                    "title": data["title"] or selenium_data["title"],
                    "price": self.safe_int(data["price"] or selenium_data["price"]),
                    "rating": self.safe_float(data["rating"] or selenium_data["rating"]),
                    "total_reviews": self.safe_int(data["total_reviews"] or selenium_data["total_reviews"]),
                    "comments": data["comments"] if data["comments"] else selenium_data["comments"],
                }

            return {
                "title": data["title"],
                "price": self.safe_int(data["price"]),
                "rating": self.safe_float(data["rating"]),
                "total_reviews": self.safe_int(data["total_reviews"]),
                "comments": data["comments"],
            }

        except requests.RequestException as e:
            print(f"[WARN] Requests failed: {e}. Using Selenium fallback...")
            try:
                selenium_data = self.scrape_with_selenium()
                return {
                    "title": selenium_data["title"],
                    "price": self.safe_int(selenium_data["price"]),
                    "rating": self.safe_float(selenium_data["rating"]),
                    "total_reviews": self.safe_int(selenium_data["total_reviews"]),
                    "comments": selenium_data["comments"],
                }
            except Exception as selenium_error:
                print(f"[ERROR] Selenium failed: {selenium_error}")
                return empty_result

        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}")
            return empty_result


if __name__ == "__main__":
    URL = "https://www.daraz.com.bd/products/-i556942578-s2589951797.html?pvid=27124392-2fa7-4d61-bdad-162da09b0ae1&search=jfy&scm=1007.51705.413671.0&spm=a2a0e.tm80335411.just4u.d_556942578"

    if "?" in URL:
        URL = URL.split("?")[0]

    scraper = DarazScraper(URL, headless=True)
    result = scraper.scrape()
    print(json.dumps(result, ensure_ascii=False, indent=2))