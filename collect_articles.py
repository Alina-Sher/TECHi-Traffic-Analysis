import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
from urllib.parse import urljoin, urlparse

BASE_URL = "https://www.techi.com"
DELAY = 2

SECTIONS = {
    "AI": "/category/ai-intelligence/",
    "Markets": "/category/markets-equities/",
    "Crypto": "/category/crypto-defi/",
    "Breakthroughs": "/category/tech-breakthroughs/",
    "Policy": "/category/policy-impact/",
    "Guides": "/category/research-tools-guides/",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/154.0.0.0 Safari/537.36"
    )
}

session = requests.Session()
session.headers.update(HEADERS)


# ---------------------------------------------------------
# BASIC HELPERS
# ---------------------------------------------------------

def clean_text(text):
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def absolute_url(href):
    return urljoin(BASE_URL, href)


def is_valid_article_url(url):
    """
    Reject navigation, category, author, tag, profile,
    system and other non-article URLs.
    """

    if not url:
        return False

    url = absolute_url(url)
    parsed = urlparse(url)

    # Must belong to TECHi
    if parsed.netloc not in ["www.techi.com", "techi.com"]:
        return False

    path = parsed.path.rstrip("/")

    if not path or path == "":
        return False

    # VERY IMPORTANT:
    # Reject author profile URLs such as:
    # /@fatimah-misbah
    # /@zeshan
    if path.startswith("/@"):
        return False

    # Reject any URL containing an @ profile path
    if "/@" in path:
        return False

    excluded_parts = [
        "/category/",
        "/author/",
        "/tag/",
        "/search/",
        "/puzzles/",
        "/members/",
        "/login/",
        "/privacy/",
        "/terms/",
        "/about/",
        "/contact/",
        "/careers/",
        "/advertise/",
        "/wp-",
        "/feed/",
        "/page/",
    ]

    for part in excluded_parts:
        if part in path.lower():
            return False

    # Reject obvious WordPress/system URLs
    if path.startswith("/wp-"):
        return False

    # Reject query-only/system URLs
    if parsed.query and not parsed.path:
        return False

    return True


# ---------------------------------------------------------
# GET PAGE
# ---------------------------------------------------------

def get_soup(url):
    time.sleep(DELAY)

    response = session.get(url, timeout=30)
    response.raise_for_status()

    return BeautifulSoup(response.text, "html.parser")


# ---------------------------------------------------------
# EXTRACT ARTICLE LINKS
# ---------------------------------------------------------

def extract_article_links(soup):
    """
    First try to extract links from actual <article> cards.
    This prevents author/navigation links from being selected.

    If that doesn't find enough articles, use a filtered fallback.
    """

    articles = []

    # -----------------------------------------------------
    # METHOD 1: actual <article> elements
    # -----------------------------------------------------

    for article in soup.find_all("article"):

        heading = article.find(["h1", "h2", "h3", "h4"])

        if not heading:
            continue

        link = heading.find("a", href=True)

        if not link:
            # Sometimes heading itself may be wrapped differently
            link = article.find("a", href=True)

        if not link:
            continue

        href = link.get("href", "")
        title = clean_text(heading.get_text(" ", strip=True))

        if not title:
            continue

        if not is_valid_article_url(href):
            continue

        full_url = absolute_url(href)

        item = {
            "url": full_url,
            "title": title
        }

        # Avoid duplicates
        if full_url not in [x["url"] for x in articles]:
            articles.append(item)

    # -----------------------------------------------------
    # METHOD 2: fallback
    # -----------------------------------------------------

    if len(articles) < 20:

        for a in soup.find_all("a", href=True):

            href = a.get("href", "")
            text = clean_text(a.get_text(" ", strip=True))

            if not text:
                continue

            # Need something that looks like an article headline
            if len(text.split()) < 3:
                continue

            if not is_valid_article_url(href):
                continue

            full_url = absolute_url(href)

            # Don't add duplicates
            if full_url in [x["url"] for x in articles]:
                continue

            articles.append({
                "url": full_url,
                "title": text
            })

            if len(articles) >= 20:
                break

    return articles


# ---------------------------------------------------------
# ARTICLE DETAILS
# ---------------------------------------------------------

def extract_article_details(url, section):
    soup = get_soup(url)

    # -------------------------
    # HEADLINE
    # -------------------------

    headline = ""

    h1 = soup.find("h1")

    if h1:
        headline = clean_text(h1.get_text(" ", strip=True))

    if not headline:
        og_title = soup.find("meta", property="og:title")

        if og_title:
            headline = clean_text(og_title.get("content", ""))

    # -------------------------
    # AUTHOR
    # -------------------------

    author = ""

    # First try common author elements
    author_selectors = [
        '[rel="author"]',
        ".author",
        ".author-name",
        ".post-author",
        ".article-author",
        '[class*="author"]',
    ]

    for selector in author_selectors:

        try:
            element = soup.select_one(selector)

            if element:
                text = clean_text(element.get_text(" ", strip=True))

                if text:
                    author = text
                    break

        except Exception:
            pass

    # Meta fallback
    if not author:
        meta_author = soup.find("meta", attrs={"name": "author"})

        if meta_author:
            author = clean_text(meta_author.get("content", ""))

    # -------------------------
    # DATE SHOWN
    # -------------------------

    date_shown = ""

    # Prefer visible <time>
    time_tag = soup.find("time")

    if time_tag:
        date_shown = clean_text(time_tag.get_text(" ", strip=True))

    # Fallback to visible date-like text
    if not date_shown:

        date_patterns = [
            r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4}\b",
            r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b",
        ]

        page_text = clean_text(soup.get_text(" ", strip=True))

        for pattern in date_patterns:

            match = re.search(pattern, page_text, flags=re.I)

            if match:
                date_shown = match.group(0)
                break

    # -------------------------
    # HEADLINE WORD COUNT
    # -------------------------

    headline_word_count = len(headline.split())

    # -------------------------
    # FORMAT
    # -------------------------

    # Start conservatively.
    # We will review these after collecting the dataset.
    page_text_lower = clean_text(
        soup.get_text(" ", strip=True)
    ).lower()

    if "review" in headline.lower():
        article_format = "Review"
    elif "how to" in headline.lower():
        article_format = "How-to"
    elif "guide" in headline.lower():
        article_format = "Guide"
    elif "analysis" in headline.lower():
        article_format = "Analysis"
    elif "interview" in headline.lower():
        article_format = "Interview"
    elif "explainer" in headline.lower():
        article_format = "Explainer"
    elif "opinion" in page_text_lower:
        article_format = "Opinion"
    else:
        article_format = "News"

    # -------------------------
    # COMPANY NAMES
    # -------------------------

    # Conservative list.
    # TRUE only when the headline explicitly contains
    # one of these company/organization names.

    company_names = [
        "Apple",
        "Amazon",
        "Google",
        "Microsoft",
        "Meta",
        "OpenAI",
        "Nvidia",
        "NVIDIA",
        "Tesla",
        "Netflix",
        "Intel",
        "AMD",
        "Samsung",
        "IBM",
        "Oracle",
        "Palantir",
        "Anthropic",
        "DeepMind",
        "ByteDance",
        "TikTok",
        "YouTube",
        "Facebook",
        "Instagram",
        "X",
        "Twitter",
        "Coinbase",
        "Binance",
        "MicroStrategy",
        "SpaceX",
        "Qualcomm",
        "Micron",
        "Broadcom",
        "Cisco",
        "Adobe",
        "Salesforce",
        "Uber",
        "Airbnb",
        "PayPal",
        "Visa",
        "Mastercard",
        "Sony",
        "Nintendo",
        "Huawei",
        "Dell",
        "HP",
        "IBM",
    ]

    names_a_company = False

    for company in company_names:

        pattern = r"\b" + re.escape(company) + r"\b"

        if re.search(pattern, headline, flags=re.I):
            names_a_company = True
            break

    # -------------------------
    # CONTAINS A NUMBER
    # -------------------------

    contains_a_number = bool(
        re.search(r"\d", headline)
    )

    return {
        "url": url,
        "section": section,
        "headline": headline,
        "author": author,
        "date_shown": date_shown,
        "headline_word_count": headline_word_count,
        "format": article_format,
        "names_a_company": names_a_company,
        "contains_a_number": contains_a_number,
    }


# ---------------------------------------------------------
# MAIN COLLECTION
# ---------------------------------------------------------

all_rows = []

for section, category_path in SECTIONS.items():

    category_url = urljoin(BASE_URL, category_path)

    print("\n" + "=" * 70)
    print(f"SECTION: {section}")
    print(f"PAGE: {category_url}")
    print("=" * 70)

    try:
        soup = get_soup(category_url)

    except Exception as e:
        print(f"ERROR loading section: {e}")
        continue

    article_links = extract_article_links(soup)

    print(f"Candidate article links found: {len(article_links)}")

    # We need exactly the newest 20
    selected = article_links[:20]

    print("\nSelected links:")

    for i, item in enumerate(selected, start=1):
        print(f"{i:02d}. {item['title']}")
        print(f"    {item['url']}")

    # If less than 20, report it
    if len(selected) < 20:
        print(
            f"\nWARNING: Only {len(selected)} article links "
            f"were found for {section}."
        )

    # Get article details
    for i, item in enumerate(selected, start=1):

        print(
            f"\n[{section}] "
            f"{i}/{len(selected)} -> {item['url']}"
        )

        try:

            row = extract_article_details(
                item["url"],
                section
            )

            all_rows.append(row)

        except Exception as e:

            print(
                f"ERROR extracting article: {e}"
            )

            # Keep a row so we can identify the failure
            all_rows.append({
                "url": item["url"],
                "section": section,
                "headline": item["title"],
                "author": "",
                "date_shown": "",
                "headline_word_count": len(
                    item["title"].split()
                ),
                "format": "",
                "names_a_company": False,
                "contains_a_number": bool(
                    re.search(r"\d", item["title"])
                ),
            })


# ---------------------------------------------------------
# CREATE DATAFRAME
# ---------------------------------------------------------

columns = [
    "url",
    "section",
    "headline",
    "author",
    "date_shown",
    "headline_word_count",
    "format",
    "names_a_company",
    "contains_a_number",
]

df = pd.DataFrame(all_rows)

# Make sure columns are in exact required order
df = df[columns]


# ---------------------------------------------------------
# SAVE
# ---------------------------------------------------------

output_file = "techi_articles.csv"

df.to_csv(
    output_file,
    index=False,
    encoding="utf-8-sig"
)

print("\n" + "=" * 70)
print("FINAL VALIDATION")
print("=" * 70)

print(f"\nTotal rows: {len(df)}")

print("\nRows per section:")
print(df["section"].value_counts().sort_index())


# ---------------------------------------------------------
# MISSING VALUES
# ---------------------------------------------------------

print("\nMissing values:")
print(df.isna().sum())


# Blank strings
print("\nBlank strings:")

for col in columns:

    blank_count = (
        df[col]
        .astype(str)
        .str.strip()
        .eq("")
        .sum()
    )

    print(f"{col}: {blank_count}")


# ---------------------------------------------------------
# DUPLICATE URL CHECK
# ---------------------------------------------------------

duplicate_mask = df["url"].duplicated(keep=False)

print(
    "\nDuplicate URLs across sections:",
    duplicate_mask.sum()
)

if duplicate_mask.sum() > 0:

    print("\nDuplicate URL details:")

    duplicate_rows = df.loc[
        duplicate_mask,
        ["section", "headline", "url"]
    ].sort_values("url")

    print(
        duplicate_rows.to_string(index=False)
    )


# ---------------------------------------------------------
# AUTHOR PROFILE SAFETY CHECK
# ---------------------------------------------------------

profile_urls = df[
    df["url"].str.contains(
        r"/@",
        case=False,
        na=False,
        regex=True
    )
]

print(
    "\nAuthor profile URLs found:",
    len(profile_urls)
)

if len(profile_urls) > 0:

    print(profile_urls[
        ["section", "headline", "url"]
    ].to_string(index=False))


# ---------------------------------------------------------
# CATEGORY / SYSTEM URL SAFETY CHECK
# ---------------------------------------------------------

bad_url_patterns = [
    "/category/",
    "/author/",
    "/tag/",
    "/search/",
    "/members/",
    "/login/",
    "/privacy/",
    "/terms/",
    "/about/",
    "/contact/",
    "/careers/",
    "/wp-",
    "/feed/",
]

bad_rows = []

for _, row in df.iterrows():

    url_lower = row["url"].lower()

    for pattern in bad_url_patterns:

        if pattern in url_lower:

            bad_rows.append(row)
            break


print(
    "\nObvious non-article/system URLs found:",
    len(bad_rows)
)

if bad_rows:

    bad_df = pd.DataFrame(bad_rows)

    print(
        bad_df[
            ["section", "headline", "url"]
        ].to_string(index=False)
    )


# ---------------------------------------------------------
# BLANK DATE CHECK
# ---------------------------------------------------------

blank_dates = df[
    df["date_shown"]
    .astype(str)
    .str.strip()
    .eq("")
]

print(
    "\nRows with blank date_shown:",
    len(blank_dates)
)

if len(blank_dates) > 0:

    print(
        blank_dates[
            ["section", "headline", "url"]
        ].to_string(index=False)
    )


# ---------------------------------------------------------
# HEADLINE CHECK
# ---------------------------------------------------------

blank_headlines = df[
    df["headline"]
    .astype(str)
    .str.strip()
    .eq("")
]

print(
    "\nRows with blank headlines:",
    len(blank_headlines)
)


# ---------------------------------------------------------
# FINAL STATUS
# ---------------------------------------------------------

expected_rows = 120

if len(df) == expected_rows:
    print(
        f"\nPASS: Total rows = {expected_rows}"
    )
else:
    print(
        f"\nWARNING: Expected {expected_rows} "
        f"rows but got {len(df)}"
    )


section_counts = df["section"].value_counts()

all_sections_have_20 = all(
    section_counts.get(section, 0) == 20
    for section in SECTIONS
)

if all_sections_have_20:
    print(
        "PASS: Every section has exactly 20 rows."
    )
else:
    print(
        "WARNING: One or more sections do not have 20 rows."
    )


if len(profile_urls) == 0:
    print(
        "PASS: No author profile URLs detected."
    )
else:
    print(
        "WARNING: Author profile URLs still detected."
    )


print(
    f"\nSaved final dataset as: {output_file}"
)

print("\nDone.")