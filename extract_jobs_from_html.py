#!/usr/bin/env python3
"""
Extract job IDs from saved HTML files in the html/ folder.
Saves all unique job IDs to new_jobs.csv for processing.
"""
import os
import re
import csv
from pathlib import Path
from bs4 import BeautifulSoup

def extract_job_ids_from_html(html_content):
    """
    Extract all job IDs from Handshake HTML content.
    Job IDs are 8-digit numbers in URLs like: job-search/10410427?
    """
    job_ids = set()
    
    # Primary pattern: job-search/XXXXXXXX (8 digits)
    # This matches: /job-search/10410427? or /job-search/10410427 or job-search/10410427
    pattern = r'job-search/(\d{8})'
    
    try:
        # Method 1: Use BeautifulSoup to find the Jobs List region first
        soup = BeautifulSoup(html_content, 'html.parser')
        
        jobs_list_region = soup.find('div', attrs={'data-hook': 'left-content', 'role': 'region', 'aria-label': 'Jobs List'})
        
        if jobs_list_region:
            # Extract from Jobs List region only (most accurate)
            region_html = str(jobs_list_region)
            matches = re.findall(pattern, region_html)
            job_ids.update(matches)
            print(f"   📍 Found {len(matches)} job IDs in Jobs List region")
        
        # Method 2: Extract from entire HTML (fallback)
        if not job_ids:
            print(f"   📍 Jobs List region not found, searching entire HTML")
            matches = re.findall(pattern, html_content)
            job_ids.update(matches)
        
        # Method 3: Also look for any links with job-search pattern
        all_links = soup.find_all('a', href=re.compile(r'job-search/\d{8}'))
        for link in all_links:
            href = link.get('href', '')
            match = re.search(pattern, href)
            if match:
                job_ids.add(match.group(1))
    
    except Exception as e:
        print(f"   ⚠️  Error parsing with BeautifulSoup: {e}")
        # Fallback to simple regex if BeautifulSoup fails
        print(f"   📍 Using regex fallback on entire HTML")
        matches = re.findall(pattern, html_content)
        job_ids.update(matches)
    
    # Remove duplicates and sort (convert to int then back to ensure 8 digits)
    unique_ids = sorted(list(set(job_ids)))
    
    # Filter to ensure only 8-digit numbers
    valid_ids = [job_id for job_id in unique_ids if len(job_id) == 8 and job_id.isdigit()]
    
    return [int(job_id) for job_id in valid_ids]


def process_html_folder(html_folder='html'):
    """
    Process all HTML files in the html/ folder and extract job IDs.
    Returns a list of unique job IDs and statistics.
    """
    html_path = Path(html_folder)
    
    if not html_path.exists():
        print(f"❌ Folder '{html_folder}' does not exist!")
        print(f"   Please create it and add HTML files: mkdir {html_folder}")
        return []
    
    html_files = list(html_path.glob('*.html')) + list(html_path.glob('*.htm'))
    
    if not html_files:
        print(f"❌ No HTML files found in '{html_folder}/' folder!")
        print(f"   Please save job search HTML pages to this folder.")
        return []
    
    print(f"📂 Found {len(html_files)} HTML file(s) in '{html_folder}/' folder")
    print()
    
    all_job_ids = set()
    file_stats = {}
    
    for html_file in html_files:
        print(f"📄 Processing: {html_file.name}")
        try:
            with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
                html_content = f.read()
            
            job_ids = extract_job_ids_from_html(html_content)
            file_stats[html_file.name] = len(job_ids)
            all_job_ids.update(job_ids)
            
            print(f"   ✅ Extracted {len(job_ids)} job ID(s)")
            
        except Exception as e:
            print(f"   ❌ Error reading file: {e}")
    
    print()
    print("="*70)
    print(f"📊 Summary:")
    for filename, count in file_stats.items():
        print(f"   {filename}: {count} jobs")
    print(f"   Total unique jobs: {len(all_job_ids)}")
    print("="*70)
    print()
    
    return sorted(all_job_ids)


def save_job_ids_to_csv(job_ids, output_file='new_jobs.csv'):
    """
    Save job IDs to a CSV file for processing.
    """
    if not job_ids:
        print("⚠️  No job IDs to save!")
        return False
    
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['job_id'])  # Header
            for job_id in job_ids:
                writer.writerow([job_id])
        
        print(f"✅ Saved {len(job_ids)} job IDs to '{output_file}'")
        return True
    
    except Exception as e:
        print(f"❌ Error saving to CSV: {e}")
        return False


if __name__ == '__main__':
    print("="*70)
    print("🔍 Job ID Extractor from HTML Files")
    print("="*70)
    print()
    
    # Process all HTML files
    job_ids = process_html_folder('html')
    
    if job_ids:
        # Save to CSV
        save_job_ids_to_csv(job_ids, 'new_jobs.csv')
        print()
        print("✅ Ready to apply! Run: python3 handshake.py")
    else:
        print()
        print("❌ No jobs found. Please:")
        print("   1. Go to Handshake job search")
        print("   2. Right-click → 'Save Page As' → Save to html/ folder")
        print("   3. Run this script again")

