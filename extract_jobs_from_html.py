#!/usr/bin/env python3
"""
Extract job IDs from saved HTML files in the html/ folder.
Saves all unique job IDs to new_jobs.csv for processing.
"""
import os
import re
import csv
from pathlib import Path

def extract_job_ids_from_html(html_content):
    """
    Extract all job IDs from Handshake HTML content.
    Looks for patterns like /jobs/12345 in URLs.
    """
    job_ids = set()
    
    # Pattern 1: Direct job URLs like href="/jobs/12345" or href="https://app.joinhandshake.com/jobs/12345"
    pattern1 = r'/jobs/(\d+)'
    matches1 = re.findall(pattern1, html_content)
    job_ids.update(matches1)
    
    # Pattern 2: Data attributes that might contain job IDs
    pattern2 = r'data-job-id="(\d+)"'
    matches2 = re.findall(pattern2, html_content)
    job_ids.update(matches2)
    
    # Pattern 3: Job IDs in JavaScript/JSON data
    pattern3 = r'"job_id["\s:]+(\d+)'
    matches3 = re.findall(pattern3, html_content)
    job_ids.update(matches3)
    
    # Pattern 4: ID fields in JSON
    pattern4 = r'"id"\s*:\s*(\d+)'
    matches4 = re.findall(pattern4, html_content)
    # Filter to only IDs that look like job IDs (7-9 digits typically)
    job_ids.update([m for m in matches4 if len(m) >= 6 and len(m) <= 10])
    
    return sorted([int(job_id) for job_id in job_ids])


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

