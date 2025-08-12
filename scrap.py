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
    """Scrape job details including JobTitle, Location, ExperienceRequired, SkillsRequired, Salary, and JobDescriptionSummary."""
    data = {
        'JobTitle': 'Not Available',
        'Location': 'Not Available',
        'ExperienceRequired': 'Not Available',
        'SkillsRequired': 'Not Available',
        'Salary': 'Not Available',
        'JobDescriptionSummary': 'Not Available'
    }

    try:
        response = requests.get(details_url, headers=HEADERS, verify=False, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Job title
        title_tag = soup.find('h1') or soup.find('h2')
        if title_tag and title_tag.text.strip():
            data['JobTitle'] = title_tag.text.strip()

        page_text = soup.get_text(separator='\n').lower()

        # Location
        if "location" in page_text:
            loc = extract_detail_by_label(soup, ['location'])
            if loc:
                data['Location'] = loc

        # Experience
        if "experience" in page_text or "exp" in page_text:
            exp = extract_detail_by_label(soup, ['experience', 'exp'])
            if exp:
                data['ExperienceRequired'] = exp

        # Salary
        if "salary" in page_text or "package" in page_text or "pay" in page_text:
            sal = extract_detail_by_label(soup, ['salary', 'package', 'pay'])
            if sal:
                data['Salary'] = sal

        # Skills
        if "skills" in page_text or "skill" in page_text:
            skills = extract_detail_by_label(soup, ['skills', 'skill'])
            if skills:
                data['SkillsRequired'] = skills

        # Job description summary
        desc_tag = soup.find('div', class_='job-description') or soup.find('p')
        if desc_tag:
            description = desc_tag.get_text(separator=' ', strip=True)
            if description:
                data['JobDescriptionSummary'] = description[:300]  # limit length if needed

    except Exception as e:
        print(f"Failed to get job details from {details_url}: {e}")

    return data

def extract_detail_by_label(soup, labels):
    """Finds details in <tr>/<dt> or nearby text based on label keywords."""
    # Table rows
    for tr in soup.find_all('tr'):
        tds = tr.find_all(['td', 'th'])
        if len(tds) >= 2:
            label = tds[0].get_text(strip=True).lower()
            for key in labels:
                if key in label:
                    value = tds[1].get_text(strip=True)
                    if value:
                        return value
    # Definition list
    for dt in soup.find_all('dt'):
        label = dt.get_text(strip=True).lower()
        for key in labels:
            if key in label:
                dd = dt.find_next_sibling('dd')
                if dd:
                    val = dd.get_text(strip=True)
                    if val:
                        return val
    # Loose text scanning
    texts = soup.find_all(text=True)
    for i, text in enumerate(texts):
        low_text = text.lower()
        for key in labels:
            if key in low_text:
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
        details_url = None
        if len(cols) > 4:
            a_tag = cols[4].find('a', href=True)
            if a_tag:
                details_url = a_tag['href']
                if details_url.startswith('/'):
                    details_url = 'https://infopark.in' + details_url

        job_details = fetch_job_details(details_url) if details_url else {}

        jobs.append({
            'JobTitle': job_details.get('JobTitle', 'Not Available'),
            'Location': job_details.get('Location', 'Not Available'),
            'ExperienceRequired': job_details.get('ExperienceRequired', 'Not Available'),
            'SkillsRequired': job_details.get('SkillsRequired', 'Not Available'),
            'Salary': job_details.get('Salary', 'Not Available'),
            'JobURL': details_url or 'Not Available',
            'JobDescriptionSummary': job_details.get('JobDescriptionSummary', 'Not Available')
        })
        time.sleep(1)

    return jobs

def scrape_all_jobs(base_url, max_pages=3):
    all_jobs = []
    for page in range(1, max_pages + 1):
        url = base_url if page == 1 else f"{base_url}?page={page}"
        print(f"Scraping page: {url}")
        jobs = fetch_jobs_from_page(url)
        if not jobs:
            print("No more jobs found, stopping.")
            break
        all_jobs.extend(jobs)
    return all_jobs

def save_to_excel(jobs, filename='infopark_jobs_detailed.xlsx'):
    df = pd.DataFrame(jobs, columns=[
        'JobTitle', 'Location', 'ExperienceRequired', 'SkillsRequired', 'Salary', 'JobURL', 'JobDescriptionSummary'
    ])
    df.to_excel(filename, index=False)
    print(f"Saved {len(jobs)} job listings to {filename}")

if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    jobs = scrape_all_jobs(BASE_URL, max_pages=3)
    save_to_excel(jobs)
