import requests
from bs4 import BeautifulSoup
import json
from time import sleep

# --- Selected URLs organized by category for easy processing ---
URL_DATA = {
    "Admissions": [
        'https://anurag.edu.in/admissions-policy/',
        'https://anurag.edu.in/scholarships/',
        'https://anurag.edu.in/undergraduate-admissions/',
        'https://anurag.edu.in/postgraduate-admissions/',
        'https://anurag.edu.in/ph-d-admissions/',
        'https://anurag.edu.in/important-dates/',
        'https://anurag.edu.in/tuition-fee/',
        'https://anurag.edu.in/entrance-tests/',
        'https://anurag.edu.in/counselling/',
        'https://anurag.edu.in/contacts/',
    ],
    "Academics": [
        'https://www.anurag.edu.in/anurag/school-of-engineering/',
        'https://www.anurag.edu.in/anurag/school-of-agriculture/',
        'https://anurag.edu.in/departments/school-of-management/',
        'https://anurag.edu.in/departments/school-of-pharmacy/',
        'https://www.anurag.edu.in/anurag/ug/',
        'https://www.anurag.edu.in/anurag/pg/',
        'https://www.anurag.edu.in/anurag/ph-d/',
        'https://www.anurag.edu.in/anurag/academic-calendar/',
        'https://www.anurag.edu.in/anurag/library/',
    ],
    "Placements": [
        'https://anurag.edu.in/placements/',
        'https://anurag.edu.in/placements-overview/',
        'https://anurag.edu.in/liaison-with-industry/',
        'https://anurag.edu.in/recruitment/',
        'https://anurag.edu.in/students-placement-testimonials/',
    ],
    "Facilities": [
        'https://anurag.edu.in/hostels-and-accomodation/',
        'https://anurag.edu.in/transportation/',
        'https://anurag.edu.in/medical-center/',
        'https://anurag.edu.in/other-facilities/',
        'https://anurag.edu.in/sports-and-fitness/',
    ]
}

def clean_text(soup):
    """
    Removes unwanted tags (scripts, styles, nav) and extracts clean text.
    Focuses on the main body content, often within main content tags.
    """
    # Remove unwanted elements
    for script_or_style in soup(["script", "style", "header", "footer", "nav", "aside", "form"]):
        script_or_style.decompose()

    # Try to find the main content area for better data quality
    main_content = soup.find(['main', 'article', 'body']) or soup

    # Get the clean text
    text = main_content.get_text()

    # Clean up whitespace, tabs, and newlines
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    cleaned_text = '\n'.join(chunk for chunk in chunks if chunk)

    return cleaned_text

def scrape_data(url_data):
    """
    Iterates through the URLs, scrapes content, and stores it in a list of dictionaries.
    """
    scraped_results = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    total_urls = sum(len(urls) for urls in url_data.values())
    processed_count = 0

    print(f"Starting scraping of {total_urls} URLs...")

    for category, urls in url_data.items():
        for url in urls:
            processed_count += 1
            print(f"[{processed_count}/{total_urls}] Scraping {category}: {url}")
            try:
                # Add a small delay to be polite to the server
                sleep(0.5) 
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status() # Raise an exception for bad status codes

                soup = BeautifulSoup(response.content, 'html.parser')
                content = clean_text(soup)

                scraped_results.append({
                    'category': category,
                    'url': url,
                    'content': content
                })

            except requests.exceptions.RequestException as e:
                print(f"ERROR: Could not fetch {url}. Error: {e}")
            except Exception as e:
                print(f"ERROR: An unexpected error occurred while processing {url}. Error: {e}")

    return scraped_results

if __name__ == '__main__':
    data = scrape_data(URL_DATA)
    
    # Save the structured data to a JSON file
    output_filename = 'scraped_data.json'
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    print(f"\nScraping complete! Data saved to {output_filename}")
    print(f"Total entries scraped successfully: {len(data)}")
    
    if len(data) > 0:
        # Print a snippet of the data for verification
        print("\n--- Example Data Snippet ---")
        print(json.dumps(data[0], ensure_ascii=False, indent=4)[:500] + "...")
