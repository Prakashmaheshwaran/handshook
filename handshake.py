import requests
import json
import datetime
import csv
import os
import subprocess
from pathlib import Path

CONF_FILE = "conf.json"
JOBS_FILE = "jobs.csv"
WAIT_FILE = "wait.json"
NEW_JOBS_FILE = "new_jobs.csv"
HTML_FOLDER = "html"
EXTRACTOR_SCRIPT = "extract_jobs_from_html.py"
LEN_CSRF = 88
HOST = "app.joinhandshake.com"  # Changed from binghamton.joinhandshake.com
ACCEPT_GET = "application/json"
ACCEPT_POST = "application/json, text/javascript, */*; q=0.01"
CONTENT_TYPE = "application/json; charset=utf-8"
RESUME_TYPE_ID = 1
COVER_TYPE_ID = 2
TRANSCRIPT_TYPE_ID = 3
OTHER_DOCUMENT_TYPE_ID = 5


def sanitize_url(url):
    left = url.find("page=")
    if left != -1:
        right = url.find('&', left)
        if right != -1:
            return url[:left] + url[right + 1:]
        return url[:left]
    return url


def check_and_extract_html():
    """Check for HTML files and auto-extract job IDs if found."""
    html_path = Path(HTML_FOLDER)
    
    # Check if html folder exists and has HTML files
    if not html_path.exists():
        return False
    
    html_files = list(html_path.glob('*.html')) + list(html_path.glob('*.htm'))
    if not html_files:
        return False
    
    print("="*70)
    print(f"📂 Found {len(html_files)} HTML file(s) in '{HTML_FOLDER}/' folder")
    print("🔄 Auto-extracting job IDs...")
    print("="*70)
    print()
    
    # Run the extraction script
    try:
        result = subprocess.run(
            ['python3', EXTRACTOR_SCRIPT],
            capture_output=True,
            text=True,
            check=True
        )
        print(result.stdout)
        
        # Clean up HTML files after successful extraction
        print("🧹 Cleaning up HTML files...")
        for html_file in html_files:
            try:
                html_file.unlink()
                print(f"   ✅ Deleted: {html_file.name}")
            except Exception as e:
                print(f"   ⚠️  Could not delete {html_file.name}: {e}")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Error running extraction: {e}")
        print(e.stderr)
        return False
    except Exception as e:
        print(f"⚠️  Unexpected error: {e}")
        return False


def read_new_jobs():
    """Read job IDs from new_jobs.csv if it exists.
    After reading, the file will be cleaned up by the main function after processing."""
    if not os.path.exists(NEW_JOBS_FILE):
        return None
    
    try:
        job_ids = []
        with open(NEW_JOBS_FILE, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                job_id = row.get('job_id', '').strip()
                if job_id and job_id.isdigit():
                    job_ids.append(int(job_id))
        
        return job_ids if job_ids else None
    except Exception as e:
        print(f"⚠️  Error reading {NEW_JOBS_FILE}: {e}")
        return None


def cleanup_new_jobs_file():
    """Clean up new_jobs.csv before processing fresh data.
    Archives old file if it exists, then deletes it."""
    if os.path.exists(NEW_JOBS_FILE):
        try:
            # Archive the old file
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            archive_name = f"new_jobs_archived_{timestamp}.csv"
            os.rename(NEW_JOBS_FILE, archive_name)
            print(f"🧹 Cleaned up old {NEW_JOBS_FILE} → {archive_name}")
            return True
        except Exception as e:
            print(f"⚠️  Could not clean up {NEW_JOBS_FILE}: {e}")
            return False
    return True


def read_conf():
    """Read the configuration file and return the dictionary representation of configs."""
    with open(CONF_FILE, "r") as conf_file:
        configs = json.load(conf_file)
        configs["url"] = sanitize_url(configs["url"])
        return configs


def extract_graphql_filters(search_url):
    """Extract filters from search URL and convert to GraphQL filter format
    
    Handshake uses GraphQL API at /hs/graphql for job searches.
    This extracts URL params and converts them to the GraphQL filter structure.
    """
    from urllib.parse import urlparse, parse_qs
    
    if not search_url:
        return {}
    
    parsed = urlparse(search_url)
    params = parse_qs(parsed.query)
    
    # Build GraphQL filter object
    gql_filter = {}
    
    # Job Type IDs (jobType parameter)
    if 'jobType' in params:
        gql_filter['jobTypeIds'] = params['jobType']
    
    # Major IDs
    if 'majors' in params:
        gql_filter['majorIds'] = params['majors']
    
    # Employment Type IDs (full-time, part-time, etc.)
    if 'employmentTypes' in params:
        gql_filter['employmentTypeIds'] = params['employmentTypes']
    
    # Job Role Group IDs (e.g., Data Analyst = 64)
    if 'jobRoleGroups' in params:
        gql_filter['jobRoleGroupIds'] = params['jobRoleGroups']
    
    # Work Authorization Requirements
    if 'workAuthorization' in params:
        # Convert to GraphQL enum format
        work_auth_map = {
            'openToUSVisaSponsorship': 'OPEN_TO_US_VISA_SPONSORSHIP',
            'openToOptionalPracticalTraining': 'OPEN_TO_OPTIONAL_PRACTICAL_TRAINING',
            'openToCptCandidates': 'OPEN_TO_CPT_CANDIDATES'
        }
        work_auth = []
        for wa in params['workAuthorization']:
            if wa in work_auth_map:
                work_auth.append(work_auth_map[wa])
        if work_auth:
            gql_filter['workAuthorizationRequirements'] = work_auth
    
    # Qualifications Requirements
    if 'qualifications' in params:
        # Convert to uppercase enum format
        quals = [q.upper() for q in params['qualifications']]
        gql_filter['qualificationsRequirements'] = quals
    
    # Salary Type IDs
    if 'pay[salaryType]' in params or 'pay%5BsalaryType%5D' in params:
        salary_type = params.get('pay[salaryType]', params.get('pay%5BsalaryType%5D', []))
        if salary_type:
            gql_filter['salaryTypeIds'] = salary_type
    
    return gql_filter


def read_wait_file():
    """Read the wait file that contains jobs which were not applied to in the previous run."""
    try:
        wait_file = open(WAIT_FILE, 'r')
        waited_jobs = json.load(wait_file)
        wait_file.close()
    except FileNotFoundError:
        waited_jobs = list()
    return waited_jobs


def get_csrf_token(session):
    """Get the CSRF-Token, which is required when submitting an application"""
    page = session.get(f'https://{HOST}')
    index = page.text.find("<meta name=\"csrf-token\" content=\"") + len("<meta name=\"csrf-token\" content=\"")
    return page.text[index: index + LEN_CSRF]


def fetch_jobs_graphql(session, filters, csrf_token, page=1, per_page=25):
    """Fetch jobs using Handshake's GraphQL API with proper filtering
    
    Args:
        session: requests.Session with cookies
        filters: dict of GraphQL filter parameters
        csrf_token: CSRF token for authentication
        page: page number (used to calculate 'after' cursor)
        per_page: number of results per page
    
    Returns:
        dict with 'results' list and 'total' count, or None on error
    """
    import base64
    
    # Calculate cursor for pagination (GraphQL uses cursor-based pagination)
    # cursor = base64.encode((page - 1) * per_page)
    cursor_value = (page - 1) * per_page
    after_cursor = base64.b64encode(str(cursor_value).encode()).decode()
    
    # GraphQL query (simplified version focusing on job data we need)
    graphql_query = """query JobSearchQuery($first: Int, $after: String, $input: JobSearchInput) {
  jobSearch(first: $first, after: $after, input: $input) {
    totalCount
    searchId
    edges {
      node {
        id
        job {
          id
          title
          expirationDate
          applyStart
          createdAt
          employer {
            id
            name
          }
          jobType {
            id
            name
            behaviorIdentifier
          }
          employmentType {
            id
            name
          }
        }
      }
    }
  }
}"""
    
    payload = {
        "operationName": "JobSearchQuery",
        "variables": {
            "first": per_page,
            "after": after_cursor,
            "input": {
                "filter": filters,
                "sort": {
                    "direction": "DESC",
                    "field": "POSTED_DATE"
                }
            }
        },
        "query": graphql_query
    }
    
    headers = {
        "Accept": "*/*",
        "Content-Type": "application/json",
        "apollographql-client-name": "consumer",
        "apollographql-client-version": "1.2",
        "graphql-operation-type": "query",
        "Origin": f"https://{HOST}",
        "Referer": f"https://{HOST}/",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        "X-CSRF-Token": csrf_token,
        "sec-ch-ua": '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"'
    }
    
    try:
        # Use the same domain as HOST for GraphQL endpoint
        graphql_url = f"https://{HOST}/hs/graphql"
        response = session.post(
            graphql_url,
            json=payload,
            headers=headers
        )
        
        if response.status_code != 200:
            print(f"GraphQL API error: {response.status_code}")
            return None
        
        data = response.json()
        
        if 'errors' in data:
            print(f"GraphQL errors: {data['errors']}")
            return None
        
        # Convert GraphQL response to our expected format
        job_search = data.get('data', {}).get('jobSearch', {})
        edges = job_search.get('edges', [])
        
        results = []
        for edge in edges:
            node = edge.get('node', {})
            job_data = node.get('job', {})
            
            # Convert to format expected by Job class
            result = {
                'job_id': int(job_data.get('id', 0)),
                'job_name': job_data.get('title', ''),
                'apply_start': job_data.get('applyStart'),
                'created_at': job_data.get('createdAt'),
                'job': {
                    'id': int(job_data.get('id', 0)),
                    'employer_name': job_data.get('employer', {}).get('name', 'Unknown'),
                    'type': job_data.get('jobType', {}).get('name', 'Job')
                }
            }
            results.append(result)
        
        return {
            'results': results,
            'total': job_search.get('totalCount', 0),
            'searchId': job_search.get('searchId')
        }
        
    except Exception as e:
        print(f"Error fetching jobs via GraphQL: {e}")
        return None


class Job:

    def __init__(self, data, full_details=None):
        self.data = data
        self.start = data.get("apply_start")
        self.date = data.get("created_at", data.get("updated_at"))
        self.id = data.get("job_id")
        self.name = data.get("job_name")
        self.employer = data.get("job", {}).get("employer_name", data.get("employer_name", "Unknown"))
        self.type = data.get("job", {}).get("type", "Job")
        
        # For list view, we won't have full details yet
        self.full_details = full_details
        self.apply_type = None
        self.document_type_ids = []
        
        # If we have full details, extract apply settings
        if full_details and "job" in full_details:
            job_data = full_details["job"]
            if "job_apply_setting" in job_data:
                self.apply_type = job_data["job_apply_setting"].get("apply_type")
            if "required_job_document_types" in job_data:
                self.document_type_ids = [doc["document_type_id"] 
                                         for doc in job_data["required_job_document_types"]]

    @classmethod
    def set(cls, session, configs):
        """Set various attributes"""
        cls.session = session
        cls.date = configs["date"]
        cls.documents = {RESUME_TYPE_ID: configs["resume"], COVER_TYPE_ID: configs["cover"],
                         TRANSCRIPT_TYPE_ID: configs["transcript"], OTHER_DOCUMENT_TYPE_ID: configs.get("other")}
        cls.csrf_token = get_csrf_token(session)
        cls.now = datetime.datetime.utcnow().isoformat()
    
    def fetch_details(self):
        """Fetch full job details including apply settings and document requirements"""
        if self.full_details:
            return True
        
        try:
            url = f'https://{HOST}/stu/jobs/{self.id}'
            headers = {
                "Accept": ACCEPT_GET,
                "Host": HOST,
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
                "Referer": f"https://{HOST}/",
                "X-Requested-With": "XMLHttpRequest",
                "sec-ch-ua": '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"macOS"'
            }
            response = self.session.get(url, headers=headers)
            if response.status_code == 200:
                self.full_details = response.json()
                # Extract apply settings from full details
                if "job" in self.full_details:
                    job_data = self.full_details["job"]
                    if "job_apply_setting" in job_data:
                        self.apply_type = job_data["job_apply_setting"].get("apply_type")
                    if "required_job_document_types" in job_data:
                        self.document_type_ids = [doc["document_type_id"] 
                                                 for doc in job_data["required_job_document_types"]]
                return True
            else:
                # Silently skip 403s - they may be non-qualifying jobs
                if response.status_code != 403:
                    print(f"Failed to fetch details for job {self.id}: {response.status_code}")
                return False
        except Exception as e:
            print(f"Error fetching job details: {e}")
            return False

    def apply(self):
        """Apply to this job, return 0 if succeed, return 1 if cookie errors, 2 if not opened yet,
        3 if the job requires applying externally, 4 if the job required other documents, 5 if failed to fetch details"""
        
        # First, fetch full job details if we don't have them
        if not self.full_details:
            if not self.fetch_details():
                return 5
        
        if self.apply_type != "handshake":
            return 3
        if self.start and self.start > self.now:
            return 2
        
        headers = {"Accept": ACCEPT_POST, "Host": HOST, "X-CSRF-Token": self.csrf_token, "Content-Type": CONTENT_TYPE}
        document_ids = list()
        
        for document_type_id in self.document_type_ids:
            if document_type_id not in (RESUME_TYPE_ID, COVER_TYPE_ID, TRANSCRIPT_TYPE_ID, OTHER_DOCUMENT_TYPE_ID):
                print(f"Skipping job '{self.name}' - requires unsupported document type: {document_type_id}")
                return 4
            doc_id = self.documents.get(document_type_id)
            if doc_id:
                document_ids.append(doc_id)
            else:
                print(f"Skipping job '{self.name}' - missing required document type: {document_type_id}")
                return 4
        
        data = json.dumps(
            {"application": {"applicable_id": self.id, "applicable_type": self.type, "document_ids": document_ids},
             "work_authorization_status": None})
        result = self.session.post(f'https://{HOST}/jobs/{self.id}/applications',
                                   headers=headers, data=data)
        if result.status_code != requests.codes.ok:
            print(f"Failed to apply to '{self.name}': Status {result.status_code}, Response: {result.text[:200]}")
            return 1
        print(f"✅ Applied to '{self.name}' at {self.employer} successfully!")
        return 0

    def wait(self, wait_list):
        """Add to WAIT_LIST"""
        wait_list.append(self.data)

    def write(self, jobs_file):
        """Write job info to JOBS_FILE"""
        jobs_file.write("%d, \"%s\", \"%s\", \"%s\"\n" % (self.id, self.name, self.employer, self.now))


def main():
    configs = read_conf()
    cookie_error = False
    if not configs["valid"]:
        print("RTFM!!!")
        exit(1)

    session = requests.Session()
    session.cookies.update(configs["cookies"])
    Job.set(session, configs)

    waited_list = read_wait_file()
    wait_list = list()
    jobs_file = open(JOBS_FILE, 'a+')
    for job_data in waited_list:
        job = Job(job_data)
        ret = job.apply()
        if ret != 0:
            if ret == 2:
                job.wait(wait_list)
            elif ret == 1:
                cookie_error = True
                break
        else:
            job.write(jobs_file)

    page = 1
    see_old_jobs = False
    date = datetime.datetime.utcnow().isoformat()
    
    jobs_checked = 0
    jobs_skipped_keywords = 0
    jobs_applied = 0
    
    # Clean up old new_jobs.csv before processing fresh data from HTML
    cleanup_new_jobs_file()
    
    # Auto-extract from HTML files if present
    check_and_extract_html()
    
    # Check if we have specific jobs from HTML extraction
    specific_job_ids = read_new_jobs()
    
    if specific_job_ids:
        print("="*70)
        print(f"🎯 Applying to {len(specific_job_ids)} specific jobs from {NEW_JOBS_FILE}")
        print("="*70)
        print()
        
        for job_id in specific_job_ids:
            jobs_checked += 1
            
            # Create minimal job data structure - details will be fetched
            job_data = {
                'job_id': job_id,
                'job_name': f'Job ID {job_id}',
                'employer_name': 'Unknown',
                'created_at': datetime.datetime.utcnow().isoformat(),
                'apply_start': None
            }
            
            job = Job(job_data)
            ret = job.apply()
            
            if ret == 0:
                jobs_applied += 1
                job.write(jobs_file)
                print(f"✅ Applied to '{job.name}' at {job.employer} successfully!")
            elif ret == 1:
                print(f"❌ Cookie error on job {job_id}")
                cookie_error = True
                break
            elif ret == 2:
                print(f"⏭️  Job {job_id} not open yet")
                job.wait(wait_list)
            elif ret == 3:
                print(f"⏭️  Job {job_id} requires external application")
            elif ret == 4:
                print(f"⏭️  Job {job_id} requires unsupported documents")
            elif ret == 5:
                print(f"⏭️  Failed to fetch details for job {job_id}")
        
        print()
        print("="*70)
        print(f"✅ Processed {jobs_checked} jobs from {NEW_JOBS_FILE}")
        print(f"✅ Successfully applied to: {jobs_applied}")
        print("="*70)
        
        # Delete the new_jobs.csv after processing (already archived before processing)
        if os.path.exists(NEW_JOBS_FILE):
            try:
                os.remove(NEW_JOBS_FILE)
                print(f"🧹 Cleaned up {NEW_JOBS_FILE}")
            except Exception as e:
                print(f"⚠️  Could not delete {NEW_JOBS_FILE}: {e}")
    
    else:
        # Original bulk processing with keyword filtering
        print("="*70)
        print(f"📊 No {NEW_JOBS_FILE} found - using bulk processing with keyword filters")
        print("="*70)
        print()
        
        # Get keyword filters for client-side filtering
        job_keywords = [kw.lower() for kw in configs.get("job_keywords", [])]
        skip_keywords = [kw.lower() for kw in configs.get("skip_keywords", [])]
        
        if job_keywords or skip_keywords:
            print(f"✅ Using client-side keyword filtering:")
            if job_keywords:
                print(f"   Include keywords: {', '.join(job_keywords[:5])}{'...' if len(job_keywords) > 5 else ''}")
            if skip_keywords:
                print(f"   Exclude keywords: {', '.join(skip_keywords[:5])}{'...' if len(skip_keywords) > 5 else ''}")
        else:
            print(f"⚠️  No keyword filters - will process ALL jobs")
        print()
    
    while not cookie_error and not see_old_jobs and not specific_job_ids:
        # Use /stu/postings API (the actual REST endpoint that returns JSON)
        # /job-search/ URLs are frontend routes and return HTML, not JSON
        url = f'https://{HOST}/stu/postings'
        params = {
            'page': page,
            'per_page': 25,
            'sort_direction': 'desc',
            'sort_column': 'created_at'
        }
        response = session.get(url, params=params, headers={"Host": HOST, "Accept": ACCEPT_GET})
        
        if response.status_code != 200:
            print(f"Failed to fetch jobs: Status {response.status_code}")
            cookie_error = True
            break
            
        jobs = response.json()
        if "results" not in jobs or len(jobs["results"]) == 0:
            break
        
        if page == 1:
            print(f"📊 Processing jobs page by page...\n")
            
        for job_data in jobs["results"]:
            jobs_checked += 1
            job_name_lower = job_data.get("job_name", "").lower()
            
            # Apply keyword filtering
            if skip_keywords and any(skip in job_name_lower for skip in skip_keywords):
                jobs_skipped_keywords += 1
                continue
            
            if job_keywords and not any(keyword in job_name_lower for keyword in job_keywords):
                jobs_skipped_keywords += 1
                continue
            
            job = Job(job_data)
            if configs["date"] > job.date:
                see_old_jobs = True
                break
            ret = job.apply()
            if ret != 0:
                if ret == 2:
                    job.wait(wait_list)
                elif ret == 1:
                    cookie_error = True
                    break
                # ret == 3, 4, 5: external apply, unsupported docs, or fetch failed - skip silently
            else:
                jobs_applied += 1
                job.write(jobs_file)
        page += 1

    configs["valid"] = not cookie_error
    configs["cookies"] = requests.utils.dict_from_cookiejar(session.cookies)
    if cookie_error:
        print("\n" + "="*60)
        print("❌ Cookies are not valid, please provide new ones!!!")
    else:
        configs["date"] = date
        with open(WAIT_FILE, 'w') as wait_file:
            json.dump(wait_list, wait_file)
        
        # Print summary (only for bulk processing mode)
        if not specific_job_ids:
            print("\n" + "="*60)
            print("✅ Run completed successfully!")
            print(f"📊 Jobs checked: {jobs_checked}")
            if configs.get("job_keywords") or configs.get("skip_keywords"):
                print(f"🔍 Jobs skipped (keyword filter): {jobs_skipped_keywords}")
            print(f"✅ Jobs applied to: {jobs_applied}")
            print(f"📝 Check {JOBS_FILE} for details")
            print("="*60)
    
    with open(CONF_FILE, 'w') as conf_file:
        json.dump(configs, conf_file)
    jobs_file.close()


if __name__ == '__main__':
    main()
