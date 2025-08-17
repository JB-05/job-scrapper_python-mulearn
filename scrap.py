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
    """Scrape detailed job information from the job details page."""
    data = {
        'JobTitle': 'Not Available',
        'Location': '',  # Empty string as per requirements if not found
        'ExperienceRequired': 'Not Available',
        'SkillsRequired': 'Not Available',
        'Salary': '',  # Empty string as per requirements if not found
        'JobDescriptionSummary': 'Not Available'
    }

    if not details_url:
        return data

    try:
        response = requests.get(details_url, headers=HEADERS, verify=False, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find all possible job details containers
        details_container = (
            soup.find('div', class_='job-detail-sec') or
            soup.find('div', class_='job-info-sec') or
            soup.find('div', class_='content-area')
        )
        if not details_container:
            return data

        # Find job title
        title_tag = details_container.find(['h1', 'h2']) or soup.find(['h1', 'h2'])
        if title_tag:
            data['JobTitle'] = title_tag.get_text(strip=True)

        # Look for job details in structured formats
        for container in [details_container, soup]:
            # Look for details in definition lists
            for dl in container.find_all('dl'):
                for dt in dl.find_all('dt'):
                    label = dt.get_text(strip=True).lower()
                    dd = dt.find_next_sibling('dd')
                    if dd:
                        value = dd.get_text(strip=True)
                        if any(key in label for key in ['location', 'place', 'city']):
                            data['Location'] = value
                        elif any(key in label for key in ['experience', 'exp', 'years']):
                            data['ExperienceRequired'] = value
                        elif any(key in label for key in ['skills', 'skill', 'requirements', 'qualifications']):
                            skills = value.replace('•', ',').replace('·', ',').split(',')
                            skills = [s.strip() for s in skills if s.strip()]
                            data['SkillsRequired'] = ', '.join(skills)
                        elif any(key in label for key in ['salary', 'ctc', 'package', 'compensation']):
                            data['Salary'] = value

            # Look for details in tables
            for table in container.find_all('table'):
                for row in table.find_all('tr'):
                    cells = row.find_all(['th', 'td'])
                    if len(cells) >= 2:
                        label = cells[0].get_text(strip=True).lower()
                        value = cells[1].get_text(strip=True)
                        if any(key in label for key in ['location', 'place', 'city']):
                            data['Location'] = value
                        elif any(key in label for key in ['experience', 'exp', 'years']):
                            data['ExperienceRequired'] = value
                        elif any(key in label for key in ['skills', 'skill', 'requirements', 'qualifications']):
                            skills = value.replace('•', ',').replace('·', ',').split(',')
                            skills = [s.strip() for s in skills if s.strip()]
                            data['SkillsRequired'] = ', '.join(skills)
                        elif any(key in label for key in ['salary', 'ctc', 'package', 'compensation']):
                            data['Salary'] = value

            # Look for a dedicated skills section with bullet points
            skills_section = container.find(lambda tag: tag.name in ['div', 'section'] and 
                                         any(key in tag.get_text().lower() for key in ['required skills', 'skill requirements']))
            if skills_section:
                skills_list = skills_section.find_all(['li', 'p'])
                if skills_list:
                    skills = [item.get_text(strip=True) for item in skills_list]
                    data['SkillsRequired'] = ', '.join(filter(None, skills))

        # Look for job description
        desc_section = None
        # Try different ways to find the job description
        for container in [details_container, soup]:
            # Look for sections with specific class names
            desc_section = (
                container.find('div', class_='job-description') or
                container.find('div', class_='description') or
                # Look for sections with "job description" in the text
                container.find(lambda tag: tag.name in ['div', 'section'] and
                             tag.get_text() and
                             'job description' in tag.get_text().lower()) or
                # Look for sections with description-like content
                container.find(lambda tag: tag.name in ['div', 'section'] and
                             len(tag.get_text()) > 100 and
                             any(key in tag.get_text().lower() 
                                 for key in ['responsibilities', 'requirements', 'about the role']))
            )
            if desc_section:
                break

        if desc_section:
            # Clean and format the description
            description = desc_section.get_text(separator=' ', strip=True)
            description = ' '.join(description.split())  # Normalize whitespace
            if description:
                if len(description) > 300:
                    # Try to find a good breakpoint near 300 characters
                    breakpoint = description[:300].rfind('.')
                    if breakpoint == -1:
                        breakpoint = description[:300].rfind(' ')
                    if breakpoint != -1:
                        data['JobDescriptionSummary'] = description[:breakpoint + 1] + '...'
                    else:
                        data['JobDescriptionSummary'] = description[:300] + '...'
                else:
                    data['JobDescriptionSummary'] = description

    except Exception as e:
        print(f"Error fetching job details from {details_url}: {e}")

    return data

def fetch_jobs_from_page(url):
    """Fetch and parse jobs from a single page."""
    jobs = []
    try:
        response = requests.get(url, headers=HEADERS, verify=False, timeout=10)
        response.raise_for_status()
        print(f"Successfully fetched page {url}")
    except Exception as e:
        print(f"Failed to get page {url}: {e}")
        return jobs

    soup = BeautifulSoup(response.text, 'html.parser')
    job_table = soup.find('table', class_='table')
    if not job_table:
        print("No job table found.")
        return jobs

    tbody = job_table.find('tbody')
    if not tbody:
        print("No table body found.")
        return jobs

    rows = tbody.find_all('tr')
    for row in rows:
        cols = row.find_all('td')
        if len(cols) >= 5:
            posting_date = cols[0].get_text(strip=True)
            job_title = cols[1].get_text(strip=True)
            company_name = cols[2].get_text(strip=True)
            last_date = cols[3].get_text(strip=True)
            
            details_url = None
            details_link = cols[4].find('a', href=True)
            if details_link:
                details_url = details_link['href']
                if details_url.startswith('/'):
                    details_url = 'https://infopark.in' + details_url
                print(f"Processing job: {job_title} at {company_name}")

                job_details = fetch_job_details(details_url)
                
                job_data = {
                    'PostingDate': posting_date,
                    'JobTitle': job_title,
                    'CompanyName': company_name,
                    'LastDate': last_date,
                    'Location': job_details.get('Location', 'Not Available'),
                    'ExperienceRequired': job_details.get('ExperienceRequired', 'Not Available'),
                    'SkillsRequired': job_details.get('SkillsRequired', 'Not Available'),
                    'Salary': job_details.get('Salary', 'Not Available'),
                    'JobURL': details_url,
                    'JobDescriptionSummary': job_details.get('JobDescriptionSummary', 'Not Available')
                }
                jobs.append(job_data)
                time.sleep(1)  # Be nice to the server

    return jobs

def scrape_all_jobs(base_url, max_pages=3):
    """Scrape jobs from multiple pages."""
    all_jobs = []
    for page in range(1, max_pages + 1):
        url = base_url if page == 1 else f"{base_url}?page={page}"
        print(f"Scraping page {page}: {url}")
        jobs = fetch_jobs_from_page(url)
        if not jobs:
            print("No more jobs found, stopping.")
            break
        all_jobs.extend(jobs)
    return all_jobs

def save_to_excel(jobs, filename='infopark_jobs_detailed.xlsx'):
    """Save the scraped jobs to an Excel file following the specified format."""
    # Create a new list with only the required fields in the specified order
    formatted_jobs = []
    for job in jobs:
        formatted_job = {
            'JobTitle': job['JobTitle'],
            'Location': job['Location'],
            'ExperienceRequired': job['ExperienceRequired'],
            'SkillsRequired': job['SkillsRequired'],
            'Salary': job['Salary'] if job['Salary'] != 'Not Available' else '',  # Leave blank if not available
            'JobURL': job['JobURL'],
            'JobDescriptionSummary': job['JobDescriptionSummary']
        }
        formatted_jobs.append(formatted_job)

    # Create DataFrame with exactly the specified columns in the correct order
    df = pd.DataFrame(formatted_jobs, columns=[
        'JobTitle',
        'Location',
        'ExperienceRequired',
        'SkillsRequired',
        'Salary',
        'JobURL',
        'JobDescriptionSummary'
    ])
    df.to_excel(filename, index=False)
    print(f"Saved {len(jobs)} job listings to {filename}")

if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    jobs = scrape_all_jobs(BASE_URL, max_pages=3)
    save_to_excel(jobs)
