"""
playwright_link_extractor.py

Purpose:
    Render a webpage using Playwright and extract all discovered links.

Outputs:
    artifacts/
        page.html
        homepage.png
        links.txt
        links.csv
"""

from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

URL = "https://www.msme.gov.in/"

OUTPUT_DIR = Path("artifacts")
OUTPUT_DIR.mkdir(exist_ok=True)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False
        )

        page = browser.new_page()

        print(f"Opening {URL}")

        page.goto(
            URL,
            wait_until="networkidle",
            timeout=60000
        )

        print(f"Title : {page.title()}")

        html = page.content()

        # Save rendered HTML
        (OUTPUT_DIR / "page.html").write_text(
            html,
            encoding="utf-8"
        )

        # Save screenshot
        page.screenshot(
            path=str(OUTPUT_DIR / "homepage.png"),
            full_page=True
        )

        browser.close()

    soup = BeautifulSoup(html, "lxml")

    urls = set()

    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()

        if not href:
            continue

        absolute = urljoin(URL, href)

        urls.add(absolute)

    urls = sorted(urls)

    # Save txt
    with open(OUTPUT_DIR / "links.txt", "w", encoding="utf-8") as f:
        for url in urls:
            f.write(url + "\n")

    # Save csv
    with open(OUTPUT_DIR / "links.csv", "w", encoding="utf-8") as f:
        f.write("url\n")

        for url in urls:
            f.write(f'"{url}"\n')

    print()
    print("=" * 50)
    print(f"Total unique links : {len(urls)}")
    print("=" * 50)

    for url in urls[:50]:
        print(url)


if __name__ == "__main__":
    main()