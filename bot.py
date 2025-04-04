import os
import sys
current_file_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_file_path)


from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import yaml
import time
import random
from webdriver_manager.chrome import ChromeDriverManager
import pyautogui
import pandas as pd
from tqdm import tqdm
from linkedinBot.utils.ai import JobMatchEvaluator
import os

class LinkedInBot:
    def __init__(self, headless = False,resume_path = None):
        self.headless = headless
        self.config = self.load_config()
        self.driver = self.init_browser()
        self.job_match_evaluator  = JobMatchEvaluator(resume_path=resume_path) 
        self.file_path = r"linkedinBot\output\jobs.csv"
        if os.path.exists(self.file_path):
            self.df_jobs = pd.read_csv(self.file_path)
            print(f"Loaded {self.df_jobs.shape[0]} jobs from file.")
        else:
            self.df_jobs = pd.DataFrame(columns=["job_title", "job_description", "job_location","company_name","company_link", "job_link", "employee_count", "hirer_link","job_skills","cover_letter"])

        self.applied_jobs = [(row['job_title'], row['company_name']) for _, row in self.df_jobs.iterrows()] if self.df_jobs.shape[0] else []
    
    def load_config(self):
        """Load bot configurations from a YAML file."""
        try:
            with open("linkedinBot\configs\config.yaml", "r") as file:
                config = yaml.safe_load(file)
        except FileNotFoundError:
            print("Config file not found! Using default settings.")
            return {}

        return {
            "email": os.environ.get("LINKEDIN_EMAIL"),
            "password": os.environ.get("LINKEDIN_PASSWORD"),
            "disableAntiLock": config.get("settings", {}).get("disableAntiLock", False),
            "maxJobPage": config.get("settings", {}).get("maxJobPage", 5),
            "maxPeoplePerProfile": config.get("settings", {}).get("maxPeoplePerProfile", 2),
            "jobTypes": config.get("jobPreferences", {}).get("jobTypes", {}),
            "datePosted": config.get("jobPreferences", {}).get("datePosted", {}),
            "positions": config.get("jobPreferences", {}).get("positions", []),
            "people_profiles": config.get("jobPreferences", {}).get("people_profiles", []),
            "blacklistedtitles": config.get("jobPreferences", {}).get("blacklistedTitles", []),
            "blacklistedEmployeeCounts": config.get("jobPreferences", {}).get("blacklistedEmployeeCounts", []),
        }

    def init_browser(self):
        browser_options = Options()
        if self.headless:
            browser_options.add_argument("--headless")

        optionss = ['--disable-blink-features', '--no-sandbox', '--start-maximized', '--disable-extensions',
                    '--ignore-certificate-errors', '--disable-blink-features=AutomationControlled', '--remote-debugging-port=9222']

        for option in optionss:
            browser_options.add_argument(option)
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=browser_options)
        driver.set_window_position(0, 0)
        driver.maximize_window()
        return driver

    def security_check(self):
        current_url = self.driver.current_url
        page_source = self.driver.page_source

        if '/checkpoint/challenge/' in current_url or 'security check' in page_source or 'quick verification' in page_source:
            input("Please complete the security check and press enter on this console when it is done.")
            time.sleep(random.uniform(5.5, 10.5))

    def login(self):
        """Log in to LinkedIn using credentials from the config file."""
        try:
            print("Logging in to LinkedIn...")
            self.driver.get("https://www.linkedin.com/login")
            time.sleep(random.uniform(3, 5))
            
            email, password = self.config.get("email"), self.config.get("password")
            if not email or not password:
                raise ValueError("Email or password missing in the configuration file.")
            
            self.driver.find_element(By.ID, "username").send_keys(email)
            self.driver.find_element(By.ID, "password").send_keys(password)
            self.driver.find_element(By.CSS_SELECTOR, ".btn__primary--large").click()
            time.sleep(random.uniform(5, 10))

        except TimeoutException:
            print("Timeout occurred while trying to log in.")
            self.security_check()
        except Exception as e:
            print(f"An error occurred during login: {e}")

    def get_base_search_url(self, parameters):
        """Generate base search URL parameters based on filters."""
        job_types_url = "f_JT="
        job_types = parameters.get('jobTypes', {})
        job_types_url += "%2C".join([key[0].upper() for key in job_types if job_types[key]])
        
        date_url = ""
        dates = {"all time": "", "month": "&f_TPR=r2592000", "week": "&f_TPR=r604800", "24 hours": "&f_TPR=r86400"}
        date_table = parameters.get('datePosted', {})
        for key, value in date_table.items():
            if value:
                date_url = dates[key]
                break
        
        extra_search_terms = [job_types_url, date_url]
        extra_search_terms_str = '&'.join(term for term in extra_search_terms if term)
        
        return extra_search_terms_str

    def avoid_lock(self):
        if self.config.get("disableAntiLock", False):
            return

        try:
            pyautogui.keyDown('ctrl')
            pyautogui.press('esc')
            pyautogui.keyUp('ctrl')
            time.sleep(1.0)
            pyautogui.press('esc')
        except ImportError:
            print("pyautogui module is not installed. Skipping avoid_lock functionality.")
    
    def scroll_down_page(self, percentage=20):
        scroll_height = self.driver.execute_script("return document.body.scrollHeight")  # Get total height
        scroll_by = scroll_height * (percentage / 100)  # Calculate pixels to scroll
        self.driver.execute_script(f"window.scrollBy(0, {scroll_by});")  # Scroll down
        time.sleep(random.uniform(1, 2))

    def job_page(self, position,job_page):
        self.driver.get("https://www.linkedin.com/jobs/search/?" + self.get_base_search_url(self.config) +
                         "&keywords=" + position + "&start=" + str(job_page*25))

        self.avoid_lock()

    def close(self):
        """Close the browser."""
        self.driver.quit()

    def scroll_slow(self, scrollable_element, reverse=False):
        """Smooth scrolling to load more content dynamically, with optional reverse scroll."""
        try:
            last_height = self.driver.execute_script("return arguments[0].scrollHeight;", scrollable_element)
            
            # Scroll down
            while True:
                self.driver.execute_script("arguments[0].scrollTo(0, arguments[0].scrollHeight);", scrollable_element)
                time.sleep(random.uniform(0.3, 1.0))
                
                new_height = self.driver.execute_script("return arguments[0].scrollHeight;", scrollable_element)
                if new_height == last_height:
                    break  # Stop if no more content loads
                last_height = new_height
            
            # Scroll back up if reverse is True
            if reverse:
                while last_height > 0:
                    self.driver.execute_script("arguments[0].scrollBy(0, -200);", scrollable_element)
                    time.sleep(random.uniform(0.3, 1.0))
                    last_height -= 200
        
        except Exception as e:
            print(f"An error occurred during scrolling: {e}")

    def start_applying(self):
        for position in self.config["positions"]:
            try:
                print(f"Starting the search for {position}")

                self.job_page(position, 0)
                time.sleep(random.uniform(2, 4))

                # Finding the job count
                try:
                    job_count_element = self.driver.find_element(By.CSS_SELECTOR, ".jobs-search-results-list__title-heading")
                    job_count = int(job_count_element.text.split("\n")[1].split()[0].replace(",", ""))
                except Exception as e:
                    print(f"Could not retrieve job count for '{position}': {e}")
                    continue

                print(f"Total jobs available for '{position}': {job_count}")

                if job_count == 0:
                    print(f"No jobs available for the position: {position}.")
                    continue
                
                total_applied = 0

                for page in range(0, min(job_count // 25 + 1, self.config["maxJobPage"])):  # Limit to 5 pages to avoid excessive requests
                    print(f"Processing page {page + 1} for position '{position}'")
                    self.job_page(position, page)
                    time.sleep(random.uniform(3, 5))

                    try:
                        jobs_detals = self.apply_jobs()
                        if jobs_detals:
                            total_applied += len(jobs_detals)
                            if jobs_detals:
                                self.df_jobs = pd.concat([self.df_jobs, pd.DataFrame(jobs_detals)], ignore_index=True)
                    except Exception as e:
                        print(f"Error applying for jobs on page {page}: {e}")
                        continue

                print(f"Applied for {total_applied} jobs for the position: {position}.")

                #saving the data to a CSV file
                if not self.df_jobs.empty:
                    self.df_jobs.to_csv(self.file_path , index=False)
                    print(f"Job details saved to {self.file_path}")

            except Exception as e:
                print(f"Error while processing position '{position}': {e}")

    def head_check(self, text):
        text = text.lower()
        exclusions = self.config.get("blacklistedtitles", [])
        return not any(keyword.lower() in text for keyword in exclusions)

    def emp_check(self, text):
        blacklisted_employee_counts = self.config.get("blacklistedEmployeeCounts", ["1-10 e", "11-", "101-", "51-"])
        return not any(count in text for count in blacklisted_employee_counts)

    def apply_jobs(self):
        try:
            # Locate the job results header and check for relevant text
            job_results_header = self.driver.find_element(By.CLASS_NAME, "jobs-search-results-list__text")
            maybe_jobs_crap = job_results_header.text

            if 'Jobs you may be interested in' in maybe_jobs_crap:
                raise Exception("Nothing to do here, moving forward...")

            # Attempt to locate the job results element
            try:
                # Attempt to find the job results element using the provided CSS selector
                job_results = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.scaffold-layout__list > div"))
                )
                # Perform smooth scrolling to load all job results
                self.scroll_slow(job_results)
                self.scroll_slow(job_results, reverse=True)

            except Exception as e:
                print(f"An unexpected error occurred: {e}")
                raise e

            # Find job list elements
            ul_element = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.scaffold-layout__list ul")))
            job_list = ul_element.find_elements(By.CSS_SELECTOR, "li.scaffold-layout__list-item")
            print(f"Found {len(job_list)} jobs on this page")

            if len(job_list) == 0:
                raise Exception("No jobs found on this page.")

            # Iterate through each job tile to extract details
            jobs_details = []
            for job_tile in tqdm(job_list):
                try:
                    job_details = self.get_job_details(job_tile)
                    if job_details:
                        jobs_details.append(job_details)
                except Exception as e:
                    print(f"Error while getting job details: {e}")
                    continue
            print(f"Total jobs processed: {len(jobs_details) if jobs_details else 0}")
            return jobs_details
        
        except NoSuchElementException as e:
            print(f"Element not found: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")

    def get_job_details(self,job_tile, save=True):
        try:
            # Extract job title
            job_title_element = job_tile.find_element(By.CLASS_NAME, 'job-card-list__title--link')
            job_title = job_title_element.find_element(By.TAG_NAME, 'strong').text
            
            company_name_element = job_tile.find_element(By.CLASS_NAME, 'artdeco-entity-lockup__subtitle')
            company_name = company_name_element.find_element(By.TAG_NAME, 'span').text
            
            # check in already applied jobs
            if (job_title,company_name) in self.applied_jobs:
                return None
            
            if not self.head_check(job_title):
                return None

            max_retries = 3
            retries = 0
            while retries < max_retries:
                try:
                    job_el = job_tile.find_element(By.CLASS_NAME, 'job-card-list__title--link')
                    job_el.click()
                    break
                except Exception:
                    if retries == max_retries - 1:
                        print("Max retries reached. Skipping this job.")
                        return None
                    retries += 1
                    continue

            time.sleep(random.uniform(3, 5))          
            # Extract employee count
            try:
                employee_count = self.driver.find_elements(By.CSS_SELECTOR, ".jobs-company__inline-information")[0].text
                if not self.emp_check(employee_count):
                    print(f"Employee count '{employee_count}' is not acceptable.")
                    return None
            except Exception:
                employee_count = None
                print("Employee count not found.")

            # Extract job description
            try:
                job_description = self.driver.find_element(By.ID, 'job-details').text
            except Exception:
                job_description = None
                print("Job description not found.")

            # job ai evaluation
            try:
                if self.job_match_evaluator:
                    is_matching,skills,cover_letter = self.job_match_evaluator.check_job_match(job_description)
                    if is_matching == "No":
                        print("Job description does not match resume.")
                        return None
            except:
                skills,cover_letter = None,None

            # Extract job location
            try:
                job_location = self.driver.find_element(By.CSS_SELECTOR, 
                    ".job-details-jobs-unified-top-card__tertiary-description-container").text.split("·")[0].strip()
            except Exception:
                job_location = None
                print("Job location not found.")

            # Extract hirer link
            try:
                hirer_link = self.driver.find_element(By.CSS_SELECTOR, ".hirer-card__hirer-information a").get_attribute("href")
            except Exception:
                hirer_link = None

            # Extract company link
            try:
                company_element = self.driver.find_element(By.CSS_SELECTOR, 
                    "div.job-details-jobs-unified-top-card__company-name a")
                company_link = company_element.get_attribute("href")
            except Exception:
                company_link = None
                print("Company link not found.")

            # Extract job link
            try:
                job_element = self.driver.find_element(By.CLASS_NAME, "job-details-jobs-unified-top-card__job-title")
                job_link = job_element.find_element(By.TAG_NAME, "a").get_attribute("href")
            except Exception:
                job_link = None
                print("Job link not found.")

            # Save the job if applicable
            if save:
                # check if it is linkedin easy apply
                try:
                    easy_apply_button = self.driver.find_elements("xpath", "//button[@id='jobs-apply-button-id' and .//span[text()='Easy Apply']]")
                except Exception:
                    easy_apply_button = None
                
                if len(easy_apply_button) > 0:
                    try:
                        save_button = self.driver.find_element(By.CSS_SELECTOR, ".jobs-save-button")
                        if "Save" in save_button.text.split():
                            save_button.click()
                            try:
                                time.sleep(random.uniform(0.5, 1.5))
                                close_button = self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Dismiss')]")
                                close_button.click()
                            except Exception:
                                print("Close button not found after saving the job.")
                    except Exception:
                        print("Save button not found.")

            applied_job = (job_title, company_name)
            self.applied_jobs.append(applied_job)
            
            # Return job details
            return {
                "job_title": job_title,
                "job_description": job_description,
                "job_location": job_location,
                "company_name":company_name,
                "company_link": company_link,
                "job_link": job_link,
                "employee_count": employee_count,
                "hirer_link": hirer_link,
                "job_skills":skills,
                "cover_letter":cover_letter
            }

        except Exception as e:
            print(f"An error occurred while processing job details: {e}")
            return None
    
    def get_connect_people(self, company_link, connect=True):
        company_id = company_link.split("/company/")[1].split("/")[0]
        self.driver.get(f"https://www.linkedin.com/company/{company_id}/people")
        time.sleep(random.uniform(3, 5))

        people_searches = self.config.get('people_profiles',['Hiring'])
        connection_failed = False
        all_profiles = []
        selected_profiles = []

        for search in people_searches:
            selected_profiles, not_connected_profiles = set(), []
            if len(selected_profiles) >= self.config.get('maxPeoplePerProfile',2) or connection_failed:
                break
            try:
                try:
                    self.driver.execute_script("window.scrollTo(0, 0);")
                    self.scroll_down_page(10)
                    clear_btn = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Clear all']"))
                    )
                    clear_btn.click()
                    WebDriverWait(self.driver, 3).until_not(
                        EC.presence_of_element_located((By.XPATH, "//button[normalize-space()='Clear all']"))
                    )
                    time.sleep(random.uniform(2, 4))
                    
                except:
                    pass

                search_box = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, "people-search-keywords")))
                search_box.send_keys(search, Keys.RETURN)
                time.sleep(random.uniform(2, 4))
                self.scroll_down_page(30)
                profiles = self.driver.find_elements(By.CSS_SELECTOR, "div.scaffold-finite-scroll__content ul li")
                for profile in profiles:
                    if len(selected_profiles) >= self.config.get('maxPeoplePerProfile',2) or connection_failed:
                        break
                    try:
                        profile_link = profile.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
                        profile.find_element(By.XPATH, ".//button[span[text()='Message']]")
                        selected_profiles.add(profile_link)
                    except Exception as e:
                        try:
                            connect_button = profile.find_element(By.XPATH, ".//button[span[text()='Connect']]")
                            not_connected_profiles.append((profile_link, connect_button))
                        except Exception as e:
                            pass
            except Exception as e:
                print(f"Error while searching for '{search}': {e}")

            if connect:
                for profile_link, connect_button in not_connected_profiles:
                    if len(selected_profiles) >= self.config.get('maxPeoplePerProfile',2) or connection_failed:
                        break
                    try:
                        connect_button.click()
                        time.sleep(random.uniform(1, 2))
                        WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[span[text()='Send without a note']]"))
                        ).click()
                        time.sleep(2)
                        selected_profiles.add(profile_link)
                    except Exception as e:
                        print(f"Connection failed for {profile_link} : {str(e)[:100]}")
                        if "invitation limit" in str(e).lower() or "restricted" in str(e).lower():
                            connection_failed = True 

            else:
                for profile_link, _ in not_connected_profiles:
                    if len(selected_profiles) >= self.config.get('maxPeoplePerProfile',2):
                        break
                    selected_profiles.add(profile_link)
            
            all_profiles+=selected_profiles
        return list(all_profiles),connection_failed

    def populate_connections(self,contiue_after_limit = False):
        print("Gathering and connecting people!")
        # Read the jobs data
        df_jobs = pd.read_csv(self.file_path)
        
        # Check if 'connections' column exists, if not, create it
        if 'connections' not in df_jobs.columns:
            df_jobs['connections'] = None
        
        # Get unique company links where connections are empty
        unique_company_links = df_jobs[df_jobs['connections'].isnull() | (df_jobs['connections'] == '[]')]['company_link'].drop_duplicates().tolist()
        
        # Create a dictionary to store connections for unique companies
        connections_dict = {}
        
        for company_link in tqdm(unique_company_links, desc="Processing Companies"):
            try:
                if company_link:  # Ensure the company link is not empty
                    connections,is_failed = self.get_connect_people(company_link)
                    connections_dict[company_link] = connections
                    
                    # Update the DataFrame for the current company link
                    df_jobs.loc[df_jobs['company_link'] == company_link, 'connections'] = str(connections)
                    
                    # Save the updated DataFrame back to the file after each company is processed
                    df_jobs.to_csv(self.file_path, index=False)
                    print(f"Updated file saved after processing company: {company_link}")

                    if not contiue_after_limit and is_failed:
                        print("connection limit reached!")
                        break
            except Exception as e:
                print(f"Error processing company link {company_link}: {e}")


if __file__ == "__main___":
    bot = LinkedInBot(headless=False)
    bot.login()
    bot.start_applying()
    bot.populate_connections()
    bot.close()