"""
Scraper module for books.toscrape.com
Uses Selenium for JS-rendered pages + requests/BeautifulSoup for speed.
Falls back to Open Library API for richer descriptions.
"""
import time
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

BASE_URL = 'https://books.toscrape.com'
OPEN_LIBRARY_SEARCH = 'https://openlibrary.org/search.json'

# Maps star-word → float rating
RATING_MAP = {'One': 1.0, 'Two': 2.0, 'Three': 3.0, 'Four': 4.0, 'Five': 5.0}


def _get_soup(url: str, session: requests.Session) -> BeautifulSoup:
    """Fetch URL and parse with BeautifulSoup."""
    resp = session.get(url, timeout=15)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, 'html.parser')


def _parse_book_detail(url: str, session: requests.Session) -> dict:
    """
    Scrape full detail page for one book.
    Returns dict ready to pass to Book model.
    """
    soup = _get_soup(url, session)
    article = soup.find('article', class_='product_page')

    title = soup.find('h1').text.strip()

    # Rating: <p class="star-rating Three"> → 3.0
    rating_tag = article.find('p', class_='star-rating')
    rating_word = rating_tag['class'][1] if rating_tag else 'One'
    rating = RATING_MAP.get(rating_word, 1.0)

    # UPC, price, availability from the product info table
    table = {row.find('th').text: row.find('td').text for row in article.find_all('tr')}
    price_text = table.get('Price (incl. tax)', '0').replace('Â', '').replace('£', '').strip()
    availability_text = table.get('Availability', 'Unknown').strip()
    upc = table.get('UPC', '').strip()

    # Description (may not exist)
    desc_tag = soup.find('div', id='product_description')
    description = ''
    if desc_tag:
        sibling = desc_tag.find_next_sibling('p')
        if sibling:
            description = sibling.text.strip()

    # Cover image (relative URL → absolute)
    img_tag = article.find('img')
    cover_image_url = ''
    if img_tag:
        src = img_tag.get('src', '')
        cover_image_url = urljoin(BASE_URL, src.replace('../', ''))

    # Genre from breadcrumb: Home > Books > <Genre> > title
    breadcrumbs = soup.find_all('li')
    genre = ''
    if len(breadcrumbs) >= 3:
        genre = breadcrumbs[2].text.strip()

    try:
        price = float(price_text)
    except ValueError:
        price = None

    return {
        'title': title,
        'rating': rating,
        'description': description,
        'genre': genre,
        'price': price,
        'availability': availability_text,
        'book_url': url,
        'cover_image_url': cover_image_url,
        'upc': upc,
    }


def _enrich_from_open_library(title: str) -> dict:
    """
    Query Open Library API to get author + richer description.
    Returns partial dict; missing fields are empty strings.
    """
    try:
        resp = requests.get(
            OPEN_LIBRARY_SEARCH,
            params={'title': title, 'limit': 1, 'fields': 'author_name,first_sentence'},
            timeout=8
        )
        data = resp.json()
        docs = data.get('docs', [])
        if not docs:
            return {}
        doc = docs[0]
        author = ', '.join(doc.get('author_name', [])[:2]) or 'Unknown'
        # first_sentence gives a better description snippet
        first_sentence = doc.get('first_sentence', {})
        ol_description = first_sentence.get('value', '') if isinstance(first_sentence, dict) else ''
        return {'author': author, 'ol_description': ol_description}
    except Exception as e:
        logger.warning(f'Open Library lookup failed for "{title}": {e}')
        return {}


def scrape_catalogue(
    max_books: int = 50,
    progress_callback=None,
) -> list[dict]:
    """
    Scrape books.toscrape.com catalogue pages.

    Args:
        max_books: Stop after this many books (default 50 for speed).
        progress_callback: Optional callable(current, total, message) for WebSocket progress updates.

    Returns:
        List of book dicts ready to upsert into the DB.
    """
    session = requests.Session()
    session.headers.update({'User-Agent': 'BookIQ-Scraper/1.0'})

    book_links = []
    page_url = f'{BASE_URL}/catalogue/page-1.html'

    # --- Step 1: Collect all book-detail links across catalogue pages ---
    logger.info('Collecting book links...')
    while page_url and len(book_links) < max_books:
        soup = _get_soup(page_url, session)
        articles = soup.find_all('article', class_='product_pod')
        for article in articles:
            if len(book_links) >= max_books:
                break
            a_tag = article.find('h3').find('a')
            href = a_tag['href'].replace('../', '')
            full_url = urljoin(f'{BASE_URL}/catalogue/', href)
            book_links.append(full_url)

        next_btn = soup.find('li', class_='next')
        if next_btn:
            next_href = next_btn.find('a')['href']
            page_url = urljoin(page_url, next_href)
        else:
            page_url = None

        time.sleep(0.3)   # polite crawl delay

    total = len(book_links)
    logger.info(f'Found {total} book links. Scraping details...')

    books = []
    for i, url in enumerate(book_links):
        try:
            book_data = _parse_book_detail(url, session)

            # Enrich with author / Open Library description
            ol_data = _enrich_from_open_library(book_data['title'])
            book_data['author'] = ol_data.get('author', 'Unknown')

            # Prefer scrape description; use OL as fallback
            if not book_data['description'] and ol_data.get('ol_description'):
                book_data['description'] = ol_data['ol_description']

            books.append(book_data)

            if progress_callback:
                progress_callback(i + 1, total, f'Scraped: {book_data["title"][:50]}')

            time.sleep(0.2)
        except Exception as e:
            logger.error(f'Failed to scrape {url}: {e}')
            continue

    return books
