import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

BASE_URL = "https://infopark.in/companies/job-search"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
                  " Chrome/116.0.0.0 Safari/537.36"
}

def fetch_job_details(details_url):
    """Scrape Job Title, Location, Experience, Salary, etc from the job details page."""
    data = {
        'Job Title': 'Not Available',
        'Location': 'Not Available',
        'Experience': 'Not Available',
        'Salary': 'Not Available'
    }

    try:
        response = requests.get(details_url, headers=HEADERS, verify=False, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Example assumptions based on common page layouts:
        # Adjust selectors below to match actual details page HTML structure!

        # Try to get Job Title from details page (fallback if differs from main page)
        title_tag = soup.find('h1') or soup.find('h2')
        if title_tag and title_tag.text.strip():
            data['Job Title'] = title_tag.text.strip()

        # Location, Experience, Salary might be in a details table or divs — let's look for labels

        # Find all rows or divs containing labels and values
        possible_rows = soup.find_all(['tr', 'div'], class_=lambda x: x and ('job-detail' in x or 'job-info' in x))

        # Sometimes the details are inside dl, dd/dt pairs or simple paragraphs; let's search more broadly:
        text_blocks = soup.find_all(text=True)

        # We'll try a simple heuristic search for keywords near text

        # Create a text blob of the page (lowercase) for keyword searches:
        page_text = soup.get_text(separator='\n').lower()

        # Location detection:
        if "location" in page_text:
            # Try to find a label and value
            loc = extract_detail_by_label(soup, ['location'])
            if loc:
                data['Location'] = loc

        # Experience detection:
        if "experience" in page_text:
            exp = extract_detail_by_label(soup, ['experience', 'exp'])
            if exp:
                data['Experience'] = exp

        # Salary detection:
        if "salary" in page_text:
            sal = extract_detail_by_label(soup, ['salary', 'pay', 'package'])
            if sal:
                data['Salary'] = sal

    except Exception as e:
        print(f"Failed to get job details from {details_url}: {e}")

    return data

def extract_detail_by_label(soup, labels):
    """
    Helper to extract info based on label keywords.
    Tries to find a label (e.g. 'Location') and gets the adjacent value.
    """
    # Find all elements that might contain label-value pairs
    # Try table rows first
    for tr in soup.find_all('tr'):
        tds = tr.find_all(['td', 'th'])
        if len(tds) >= 2:
            label = tds[0].get_text(strip=True).lower()
            for key in labels:
                if key in label:
                    value = tds[1].get_text(strip=True)
                    if value:
                        return value

    # Try dl/dt/dd pattern
    dts = soup.find_all('dt')
    for dt in dts:
        label = dt.get_text(strip=True).lower()
        for key in labels:
            if key in label:
                dd = dt.find_next_sibling('dd')
                if dd:
                    val = dd.get_text(strip=True)
                    if val:
                        return val

    # Try paragraphs or spans with label:
    texts = soup.find_all(text=True)
    for i, text in enumerate(texts):
        low_text = text.lower()
        for key in labels:
            if key in low_text:
                # Get next sibling text or parent sibling
                # Very heuristic approach:
                next_text = None
                if i + 1 < len(texts):
                    next_text = texts[i + 1].strip()
                if next_text:
                    return next_text
    return None

def fetch_jobs_from_page(url):
    jobs = []
    try:
        response = requests.get(url, headers=HEADERS, verify=False, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to get page {url}: {e}")
        return jobs

    soup = BeautifulSoup(response.text, 'html.parser')
    tbody = soup.find('tbody')
    if not tbody:
        print("No job table found.")
        return jobs

    rows = tbody.find_all('tr')
    for row in rows:
        cols = row.find_all('td')
        date_posting = cols[0].get_text(strip=True) if len(cols) > 0 else 'Not Available'
        job_title_main = cols[1].get_text(strip=True) if len(cols) > 1 else 'Not Available'
        company_name = cols[2].get_text(strip=True) if len(cols) > 2 else 'Not Available'
        last_date_apply = cols[3].get_text(strip=True) if len(cols) > 3 else 'Not Available'
        details_url = None
        if len(cols) > 4:
            a_tag = cols[4].find('a', href=True)
            if a_tag:
                details_url = a_tag['href']
                if details_url.startswith('/'):
                    details_url = 'https://infopark.in' + details_url

        # Fetch detailed info from details_url
        job_details = fetch_job_details(details_url) if details_url else {}

        jobs.append({
            'Date of Posting': date_posting,
            'Job Title': job_details.get('Job Title', job_title_main or 'Not Available'),
            'Company Name': company_name,
            'Last Date to Apply': last_date_apply,
            'Location': job_details.get('Location', 'Not Available'),
            'Experience': job_details.get('Experience', 'Not Available'),
            'Salary': job_details.get('Salary', 'Not Available'),
            'Details URL': details_url or 'Not Available'
        })

        # Polite delay to avoid hammering the server
        time.sleep(1)

    return jobs

def scrape_all_jobs(base_url, max_pages=3):
    all_jobs = []
    for page in range(1, max_pages + 1):
        if page == 1:
            url = base_url
        else:
            url = f"{base_url}?page={page}"
        print(f"Scraping page: {url}")
        jobs = fetch_jobs_from_page(url)
        if not jobs:
            print("No more jobs found, stopping.")
            break
        all_jobs.extend(jobs)

    return all_jobs

def save_to_excel(jobs, filename='infopark_jobs_detailed.xlsx'):
    df = pd.DataFrame(jobs)
    df.to_excel(filename, index=False)
    print(f"Saved {len(jobs)} job listings to {filename}")

if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)  # hide SSL warnings

    jobs = scrape_all_jobs(BASE_URL, max_pages=3)
    save_to_excel(jobs)
