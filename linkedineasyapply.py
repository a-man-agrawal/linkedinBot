import time, random, csv, pyautogui, traceback
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from datetime import date


class LinkedinEasyApply:
    def __init__(self, parameters, driver):
        self.browser = driver
        self.email = parameters['email']
        self.password = parameters['password']
        self.disable_lock = parameters['disableAntiLock']
        self.positions = parameters.get('positions', [])
        self.base_search_url = self.get_base_search_url(parameters)
        self.seen_jobs = []
        self.file_name = "output"
        self.unprepared_questions_file_name = "unprepared_questions"
        self.output_file_directory = parameters['outputFileDirectory']
        self.resume_dir = parameters['uploads']['resume']
        if 'coverLetter' in parameters['uploads']:
            self.cover_letter_dir = parameters['uploads']['coverLetter']
        else:
            self.cover_letter_dir = ''
        self.checkboxes = parameters.get('checkboxes', [])
        self.university_gpa = parameters['universityGpa']
        self.salary_minimum = parameters['salaryMinimum']
        self.languages = parameters.get('languages', [])
        self.experience = parameters.get('experience', [])
        self.personal_info = parameters.get('personalInfo', [])
        self.eeo = parameters.get('eeo', [])
        self.experience_default = self.experience['default']


    def login(self):
        try:
            self.browser.get("https://www.linkedin.com/login")
            time.sleep(random.uniform(3, 5))
            self.browser.find_element(By.ID, "username").send_keys(self.email)
            self.browser.find_element(By.ID, "password").send_keys(self.password)
            self.browser.find_element(By.CSS_SELECTOR, ".btn__primary--large").click()
            time.sleep(random.uniform(5, 10))
        except TimeoutException:
            raise Exception("Could not login!")

    def security_check(self):
        current_url = self.browser.current_url
        page_source = self.browser.page_source

        if '/checkpoint/challenge/' in current_url or 'security check' in page_source:
            input("Please complete the security check and press enter in this console when it is done.")
            time.sleep(random.uniform(5.5, 10.5))
    
    def start_applying(self):

        page_sleep = 0
        minimum_time = 60*15
        minimum_page_time = time.time() + minimum_time

        for position in self.positions:
            job_page_number = -1

            print("Starting the search for " + position + ".")

            try:
                while True:
                    page_sleep += 1
                    job_page_number += 1
                    print("Going to job page " + str(job_page_number))
                    self.next_job_page(position,job_page_number)
                    time.sleep(random.uniform(1.5, 3.5))
                    print("Starting the application process for this page...")
                    self.apply_jobs()
                    print("Applying to jobs on this page has been completed!")

                    time_left = minimum_page_time - time.time()
                    if time_left > 0:
                        print("Sleeping for " + str(time_left) + " seconds.")
                        time.sleep(time_left)
                        minimum_page_time = time.time() + minimum_time
                    if page_sleep % 5 == 0:
                        sleep_time = random.randint(500, 900)
                        print("Sleeping for " + str(sleep_time/60) + " minutes.")
                        time.sleep(sleep_time)
                        page_sleep += 1
            except:
                traceback.print_exc()
                pass

            time_left = minimum_page_time - time.time()
            if time_left > 0:
                print("Sleeping for " + str(time_left) + " seconds.")
                time.sleep(time_left)
                minimum_page_time = time.time() + minimum_time
            if page_sleep % 5 == 0:
                sleep_time = random.randint(500, 900)
                print("Sleeping for " + str(sleep_time/60) + " minutes.")
                time.sleep(sleep_time)
                page_sleep += 1
    
    # heading Check
    def check_contains_blacklisted_keywords(self,text):
        text = text.lower()
        exclusions = ["python engineer","python developer","data engineer","network","marketing","incident","planning","performance","ops","flutter","bi","admin","fraud","system","virtual","application","lake","quant","migration","legal","database","build","operations",
        "finance","Maintenance","consumer","capability","configuration","hardware",
        "infra","infrastructure","mobile","design","physical","qa","servicenow","project","quality","embedded",
        "c#","quality","integration","sales","solution","risk","snowflake","angular","ios","cyber","security",
        "business","android","tableau","process","power bi","powerbi","azure","site","support",
        "sas","test","imaging","iot","dot","computer vision","scala","data visualization","spring",
        "java","big","c++","front","react","dotnet","frontend","devops","teaching"
        ,"itpa",".net","ui","pl/sql","plsql","r&d","pyspark","matlab","php","spark","j2ee","visual basic"]
        
        if any(ele in text for ele in exclusions):
            return True
        return False
    
    # Experience check
    def exp_check(self,text):
        exclusions = [" 6+","6 to","6-","7+","8+","8 to","8-"]
        if any(ele in text for ele in exclusions):
            return True
        return False
    
    #employee count check
    def emp_check(self,text):
        if "1-10 e" in text or "11-" in text or "101-" in text or "51-" in text or "201-" in text or "501-" in text:
            return True
        return False
    
    def apply_jobs(self):
        no_jobs_text = ""
        try:
            no_jobs_element = self.browser.find_element(By.CLASS_NAME, 'jobs-search-two-pane__no-results-banner--expand')
            no_jobs_text = no_jobs_element.text
        except:
            pass
        if 'No matching jobs found' in no_jobs_text:
            raise Exception("No more jobs on this page")

        if 'unfortunately, things aren' in self.browser.page_source.lower():
            raise Exception("No more jobs on this page")

        try:
            job_results = self.browser.find_element(By.CLASS_NAME, "jobs-search-results-list")
            self.scroll_slow(job_results)
            self.scroll_slow(job_results, step=500, reverse=True)

            job_list = self.browser.find_elements(By.CLASS_NAME, 'scaffold-layout__list-container')[0].find_elements(By.CLASS_NAME, 'jobs-search-results__list-item')
            if len(job_list) == 0:
                raise Exception("No job class elements found in page")
        except:
            raise Exception("No more jobs on this page")

        if len(job_list) == 0:
            raise Exception("No more jobs on this page")

        for job_tile in job_list:
            job_title, company, poster, job_location, link, job_employee_count = "", "", "", "", "",""

            try:
                job_title = job_tile.find_element(By.CLASS_NAME, 'job-card-list__title').text
                job_description = self.browser.find_element(By.ID,"job-details").text
                link = job_tile.find_element(By.CLASS_NAME, 'job-card-list__title').get_attribute('href').split('?')[0]
            except:
                pass
            
            try:
                company = job_tile.find_element(By.CLASS_NAME, 'job-card-container__primary-description').text
            except:
                pass
            
            try:
                job_location = job_tile.find_element(By.CLASS_NAME, 'job-card-container__metadata-item').text
            except:
                pass
            
            
            try:
                job_employee_count = self.browser.find_elements(By.CSS_SELECTOR,".job-details-jobs-unified-top-card__job-insight")[1].text
            except:
                pass
            
            try:
                poster = self.browser.find_elements(By.CLASS_NAME,"hirer-card__container")[0].find_elements(By.CLASS_NAME,"app-aware-link ")[1].get_attribute('href')
            except:
                pass
            
            contains_blacklisted_keywords = False
            employee_count_not_match = False
            already_applied = "Applied" in job_tile.text
            experience_check = False
            
            try:
                contains_blacklisted_keywords = self.check_contains_blacklisted_keywords(job_title)
                employee_count_not_match = self.emp_check(job_employee_count)
                experience_check = self.exp_check(job_description)
            except:
                pass
            
            if contains_blacklisted_keywords is False and already_applied is False and experience_check is False :
                if employee_count_not_match is False:
                    try:
                        job_el = job_tile.find_element(By.CLASS_NAME, 'job-card-list__title')
                        job_el.click()

                        time.sleep(random.uniform(3, 5))

                        try:
                            done_applying = self.apply_to_job()
                            done_applying = True
                            if done_applying:
                                print("Done applying to the job!")
                            else:
                                print('Already applied to the job!')
                        except:
                            temp = self.file_name
                            self.file_name = "failed"
                            print("Failed to apply to job! Please submit a bug report with this link: " + link)
                            print("Writing to the failed csv file...")
                            try:
                                self.browser.find_elements(By.CLASS_NAME,'jobs-save-button')[0].click()
                                self.write_to_file(company, job_title, link, job_location,poster,job_employee_count)
                            except:
                                pass
                            self.file_name = temp


                        try:
                            self.write_to_file(company, job_title, link, job_location,poster,job_employee_count)
                        except Exception:
                            print("Could not write the job to the file! No special characters in the job title/company is allowed!")
                            traceback.print_exc()
                    except:
                        traceback.print_exc()
                        print("Could not apply to the job!")
                        pass
                else:
                    temp = self.file_name
                    self.file_name = "large_employee_count"
                    print("greater employee match found. Saving!")
                    try:
                        self.browser.find_elements(By.CLASS_NAME,'jobs-save-button')[0].click()
                        self.write_to_file(company, job_title, link, job_location,poster,job_employee_count)
                    except:
                        pass
                    self.file_name = temp
            else:
                print("Job contains blacklisted keyword or experience does not match!")

    def apply_to_job(self):
        easy_apply_button = None

        try:
            easy_apply_button = self.browser.find_element(By.CLASS_NAME, 'jobs-apply-button')
        except:
            return False

        print("Applying to the job....")
        easy_apply_button.click()

        button_text = ""
        submit_application_text = 'submit application'
        while submit_application_text not in button_text.lower():
            try:
                self.fill_up()
                next_button = self.browser.find_element(By.CLASS_NAME, "artdeco-button--primary")
                button_text = next_button.text.lower()
                if submit_application_text in button_text:
                    try:
                        self.unfollow()
                    except:
                        print("Failed to unfollow company!")
                time.sleep(1)
                next_button.click()
                time.sleep(2)

                if 'please enter a valid answer' in self.browser.page_source.lower() or 'file is required' in self.browser.page_source.lower():
                    raise Exception("Failed answering required questions or uploading required files.")
            except:
                traceback.print_exc()
                self.browser.find_element(By.CLASS_NAME, 'artdeco-modal__dismiss').click()
                time.sleep(random.uniform(3, 5))
                self.browser.find_elements(By.CLASS_NAME, 'artdeco-modal__confirm-dialog-btn')[1].click()
                time.sleep(random.uniform(3, 5))
                raise Exception("Failed to apply to job!")

        closed_notification = False
        try:
            self.browser.find_element(By.CLASS_NAME, 'artdeco-modal__dismiss').click()
            closed_notification = True
        except:
            pass
        try:
            self.browser.find_element(By.CLASS_NAME, 'artdeco-toast-item__dismiss').click()
            closed_notification = True
        except:
            pass
        time.sleep(random.uniform(3, 5))

        if closed_notification is False:
            raise Exception("Could not close the applied confirmation window!")

        return True
    
    def home_address(self, element):
        try:
            groups = element.find_elements(By.CLASS_NAME, 'jobs-easy-apply-form-section__grouping')
            if len(groups) > 0:
                for group in groups:
                    lb = group.find_element(By.TAG_NAME, 'label').text.lower()
                    input_field = group.find_element(By.TAG_NAME, 'input')
                    if 'street' in lb:
                        self.enter_text(input_field, self.personal_info['Street address'])
                    elif 'city' in lb:
                        self.enter_text(input_field, self.personal_info['City'])
                        time.sleep(3)
                        input_field.send_keys(Keys.DOWN)
                        input_field.send_keys(Keys.RETURN)
                    elif 'zip' in lb or 'postal' in lb:
                        self.enter_text(input_field, self.personal_info['Zip'])
                    elif 'state' in lb or 'province' in lb:
                        self.enter_text(input_field, self.personal_info['State'])
                    else:
                        pass
        except:
            pass

    def get_answer(self, question):
        if self.checkboxes[question]:
            return 'yes'
        else:
            return 'no'

    def additional_questions(self):
        #pdb.set_trace()
        frm_el = self.browser.find_elements(By.CLASS_NAME, 'jobs-easy-apply-form-section__grouping')
        if len(frm_el) > 0:
            for el in frm_el:
                # Radio check
                try:
                    question = el.find_element(By.CLASS_NAME, 'jobs-easy-apply-form-element')
                    radios = question.find_elements(By.CLASS_NAME, 'fb-text-selectable__option')
                    if len(radios) == 0:
                        raise Exception("No radio found in element")

                    radio_text = el.text.lower()
                    radio_options = [text.text.lower() for text in radios]
                    answer = "yes"

                    if 'driver\'s licence' in radio_text or 'driver\'s license' in radio_text:
                        answer = self.get_answer('driversLicence')
                    elif 'gender' in radio_text or 'veteran' in radio_text or 'race' in radio_text or 'disability' in radio_text or 'latino' in radio_text:
                        answer = ""
                        for option in radio_options:
                            if 'prefer' in option.lower() or 'decline' in option.lower() or 'don\'t' in option.lower() or 'specified' in option.lower() or 'none' in option.lower():
                                answer = option

                        if answer == "":
                            answer = radio_options[len(radio_options) - 1]
                    elif 'assessment' in radio_text:
                        answer = self.get_answer("assessment")
                    elif 'north korea' in radio_text:
                        answer = 'no'
                    elif 'previously employ' in radio_text or 'previous employ' in radio_text:
                        answer = 'no'
                    elif 'authorized' in radio_text or 'authorised' in radio_text or 'legally' in radio_text:
                        answer = self.get_answer('legallyAuthorized')
                    elif 'urgent' in radio_text:
                        answer = self.get_answer('urgentFill')
                    elif 'commut' in radio_text:
                        answer = self.get_answer('commute')
                    elif 'remote' in radio_text:
                        answer = self.get_answer('remote')
                    elif 'background check' in radio_text:
                        answer = self.get_answer('backgroundCheck')
                    elif 'drug test' in radio_text:
                        answer = self.get_answer('drugTest')
                    elif 'level of education' in radio_text:
                        for degree in self.checkboxes['degreeCompleted']:
                            if degree.lower() in radio_text:
                                answer = "yes"
                                break
                    elif 'experience' in radio_text:
                        for experience in self.experience:
                            if experience.lower() in radio_text:
                                answer = "yes"
                                break
                    elif 'data retention' in radio_text:
                        answer = 'no'
                    elif 'sponsor' in radio_text:
                        answer = self.get_answer('requireVisa')
                    else:
                        answer = radio_options[len(radio_options) - 1]
                        self.record_unprepared_question("radio", radio_text)

                    i = 0
                    to_select = None
                    for radio in radios:
                        if answer in radio.text.lower():
                            to_select = radios[i]
                        i += 1

                    if to_select is None:
                        to_select = radios[len(radios)-1]

                    self.radio_select(to_select, answer, len(radios) > 2)

                    if radios != []:
                        continue
                except:
                    pass
                # Questions check
                try:
                    question = el.find_element(By.CLASS_NAME, 'jobs-easy-apply-form-element')
                    question_text = question.find_element(By.TAG_NAME, 'label').text.lower()

                    txt_field_visible = False
                    try:
                        txt_field = question.find_element(By.TAG_NAME, 'input')
                        txt_field_visible = True
                    except:
                        try:
                            txt_field = question.find_element(By.TAG_NAME, 'textarea')  # TODO: Test textarea
                            txt_field_visible = True
                        except:
                            raise Exception("Could not find textarea or input tag for question")

                    text_field_type = txt_field.get_attribute('type').lower()
                    if 'numeric' in text_field_type:  # TODO: test numeric type
                        text_field_type = 'numeric'
                    elif 'text' in text_field_type:
                        text_field_type = 'text'
                    else:
                        raise Exception("Could not determine input type of input field!")

                    to_enter = ''
                    if 'experience' in question_text:
                        no_of_years = None
                        for experience in self.experience:
                            if experience.lower() in question_text:
                                no_of_years = self.experience[experience]
                                break
                        if no_of_years is None:
                            self.record_unprepared_question(text_field_type, question_text)
                            no_of_years = self.experience_default
                        to_enter = no_of_years
                    elif 'grade point average' in question_text:
                        to_enter = self.university_gpa
                    elif 'first name' in question_text:
                        to_enter = self.personal_info['First Name']
                    elif 'last name' in question_text:
                        to_enter = self.personal_info['Last Name']
                    elif 'name' in question_text:
                        to_enter = self.personal_info['First Name'] + " " + self.personal_info['Last Name']
                    elif 'pronouns' in question_text:
                        to_enter = self.personal_info['Pronouns']
                    elif 'phone' in question_text:
                        to_enter = self.personal_info['Mobile Phone Number']
                    elif 'linkedin' in question_text:
                        to_enter = self.personal_info['Linkedin']
                    elif 'website' in question_text or 'github' in question_text or 'portfolio' in question_text:
                        to_enter = self.personal_info['Website']
                    elif 'salary' in question_text:
                        if text_field_type == 'numeric':
                            to_enter = self.salary_minimum
                        else:
                            to_enter = "$" + self.salary_minimum + "+"
                    else:
                        if text_field_type == 'numeric':
                            to_enter = 0
                        else:
                            to_enter = " ‏‏‎ "
                        self.record_unprepared_question(text_field_type, question_text)

                    if text_field_type == 'numeric':
                        if not isinstance(to_enter, (int, float)):
                            to_enter = 0
                    elif to_enter == '':
                        to_enter = " ‏‏‎ "

                    self.enter_text(txt_field, to_enter)
                    continue
                except:
                    pass
                # Date Check
                try:
                    date_picker = el.find_element(By.CLASS_NAME, 'artdeco-datepicker__input ')
                    date_picker.clear()
                    date_picker.send_keys(date.today().strftime("%m/%d/%y"))
                    time.sleep(3)
                    date_picker.send_keys(Keys.RETURN)
                    time.sleep(2)
                    continue
                except:
                    pass
                # Dropdown check
                try:
                    question = el.find_element(By.CLASS_NAME, 'jobs-easy-apply-form-element')
                    question_text = question.find_element(By.TAG_NAME, 'label').text.lower()
                    dropdown_field = question.find_element(By.TAG_NAME, 'select')

                    select = Select(dropdown_field)
                    options = [options.text for options in select.options]

                    if 'proficiency' in question_text:
                        proficiency = "Conversational"

                        for language in self.languages:
                            if language.lower() in question_text:
                                proficiency = self.languages[language]
                                break

                        self.select_dropdown(dropdown_field, proficiency)
                    elif 'assessment' in question_text:
                        answer = self.get_answer('assessment')

                        choice = ""
                        for option in options:
                            if answer == 'yes':
                                choice = option
                            else:
                                if 'no' in option.lower():
                                    choice = option

                        if choice == "":
                            choice = options[len(options) - 1]

                        self.select_dropdown(dropdown_field, choice)
                    elif 'commut' in question_text:
                        answer = self.get_answer('commute')

                        choice = ""
                        for option in options:
                            if answer == 'yes':
                                choice = option
                            else:
                                if 'no' in option.lower():
                                    choice = option

                        if choice == "":
                            choice = options[len(options) - 1]

                        self.select_dropdown(dropdown_field, choice)
                    elif 'country code' in question_text:
                        self.select_dropdown(dropdown_field, self.personal_info['Phone Country Code'])
                    elif 'north korea' in question_text:

                        choice = ""

                        for option in options:
                            if 'no' in option.lower():
                                choice = option

                        if choice == "":
                            choice = options[len(options) - 1]

                        self.select_dropdown(dropdown_field, choice)
                    elif 'previously employed' in question_text or 'previous employment' in question_text:

                        choice = ""

                        for option in options:
                            if 'no' in option.lower():
                                choice = option

                        if choice == "":
                            choice = options[len(options) - 1]

                        self.select_dropdown(dropdown_field, choice)
                    elif 'sponsor' in question_text:
                        answer = self.get_answer('requireVisa')

                        choice = ""

                        for option in options:
                            if answer == 'yes':
                                choice = option
                            else:
                                if 'no' in option.lower():
                                    choice = option

                        if choice == "":
                            choice = options[len(options) - 1]

                        self.select_dropdown(dropdown_field, choice)
                    elif 'authorized' in question_text or 'authorised' in question_text:
                        answer = self.get_answer('legallyAuthorized')

                        choice = ""

                        for option in options:
                            if answer == 'yes':
                                # find some common words
                                choice = option
                            else:
                                if 'no' in option.lower():
                                    choice = option

                        if choice == "":
                            choice = options[len(options) - 1]

                        self.select_dropdown(dropdown_field, choice)
                    elif 'citizenship' in question_text:
                        answer = self.get_answer('legallyAuthorized')

                        choice = ""

                        for option in options:
                            if answer == 'yes':
                                if 'no' in option.lower():
                                    choice = option

                        if choice == "":
                            choice = options[len(options) - 1]

                        self.select_dropdown(dropdown_field, choice)
                    elif 'clearance' in question_text:
                        answer = self.get_answer('clearance')

                        choice = ""

                        for option in options:
                            if answer == 'yes':
                                # find some common words
                                choice = option
                            else:
                                if 'no' in option.lower():
                                    choice = option

                        if choice == "":
                            choice = options[len(options) - 1]

                        self.select_dropdown(dropdown_field, choice)
                    elif 'gender' in question_text or 'veteran' in question_text or 'race' in question_text or 'disability' in question_text or 'latino' in question_text:

                        choice = ""

                        for option in options:
                            if 'prefer' in option.lower() or 'decline' in option.lower() or 'don\'t' in option.lower() or 'specified' in option.lower() or 'none' in option.lower():
                                choice = option

                        if choice == "":
                            choice = options[len(options) - 1]

                        self.select_dropdown(dropdown_field, choice)
                    elif 'email' in question_text:
                        continue  # assume email address is filled in properly by default
                    elif 'experience' in question_text or 'understanding' in question_text or 'familiar' in question_text or 'comfortable' in question_text or 'able to' in question_text:
                        answer = 'no'
                        for experience in self.experience:
                            if experience.lower() in question_text and self.experience[experience] > 0:
                                answer = 'yes'
                                break
                        if answer == 'no':
                            # record unlisted experience as unprepared questions
                            self.record_unprepared_question("dropdown", question_text)

                        choice = ""
                        for option in options:
                            if answer in option.lower():
                                choice = option
                        if choice == "":
                            choice = options[len(options) - 1]

                        self.select_dropdown(dropdown_field, choice)
                    else:
                        choice = ""

                        for option in options:
                            if 'yes' in option.lower():
                                choice = option

                        if choice == "":
                            choice = options[len(options) - 1]

                        self.select_dropdown(dropdown_field, choice)
                        self.record_unprepared_question("dropdown", question_text)
                    continue
                except:
                    pass

                # Checkbox check for agreeing to terms and service
                try:
                    question = el.find_element(By.CLASS_NAME, 'jobs-easy-apply-form-element')

                    clickable_checkbox = question.find_element(By.TAG_NAME, 'label')

                    clickable_checkbox.click()
                except:
                    pass

    def unfollow(self):
        try:
            follow_checkbox = self.browser.find_element(By.XPATH, "//label[contains(.,\'to stay up to date with their page.\')]").click()
            follow_checkbox.click()
        except:
            pass

    def enter_text(self, element, text):
        element.clear()
        element.send_keys(text)

    def select_dropdown(self, element, text):
        select = Select(element)
        select.select_by_visible_text(text)

    # Radio Select
    def radio_select(self, element, label_text, clickLast=False):
        label = element.find_element(By.TAG_NAME, 'label')
        if label_text in label.text.lower() or clickLast == True:
            label.click()
        else:
            pass

    def fill_up(self):
        try:
            easy_apply_content = self.browser.find_element(By.CLASS_NAME, 'jobs-easy-apply-content')
            pb4 = easy_apply_content.find_elements(By.CLASS_NAME, 'pb4')
            if len(pb4) == 0:
                raise Exception("No pb4 class elements found in element")
            if len(pb4) > 0:
                for pb in pb4:
                    try:
                        label = pb.find_element(By.TAG_NAME, 'h3').text.lower()
                        try:
                            self.additional_questions()
                        except:
                            pass

                        if 'home address' in label:
                            self.home_address(pb)
                    except:
                        pass
        except:
            pass

    def write_to_file(self, company, job_title, link, location,poster,employee_count):
        to_write = [company, job_title, link, location,poster,employee_count]
        file_path = self.output_file_directory + self.file_name + ".csv"

        with open(file_path, 'a') as f:
            writer = csv.writer(f)
            writer.writerow(to_write)

    def record_unprepared_question(self, answer_type, question_text):
        to_write = [answer_type, question_text]
        file_path = self.unprepared_questions_file_name + ".csv"

        try:
            with open(file_path, 'a') as f:
                writer = csv.writer(f)
                writer.writerow(to_write)
        except:
            print("Could not write the unprepared question to the file! No special characters in the question is allowed: ")
            print(question_text)

    def scroll_slow(self, scrollable_element, start=0, end=3600, step=600, reverse=False):
        if reverse:
            start, end = end, start
            step = -step

        for i in range(start, end, step):
            self.browser.execute_script("arguments[0].scrollTo(0, {})".format(i), scrollable_element)
            time.sleep(random.uniform(1.0, 2.6))

    def avoid_lock(self):
        if self.disable_lock:
            return

        pyautogui.keyDown('ctrl')
        pyautogui.press('esc')
        pyautogui.keyUp('ctrl')
        time.sleep(1.0)
        pyautogui.press('esc')

    def get_base_search_url(self, parameters):
        remote_url = ""

        job_types_url = "f_JT="
        job_types = parameters.get('jobTypes', [])
        for key in job_types:
            if job_types[key]:
                job_types_url += "%2C" + key[0].upper()

        date_url = ""
        dates = {"all time": "", "month": "&f_TPR=r2592000", "week": "&f_TPR=r604800", "24 hours": "&f_TPR=r86400"}
        date_table = parameters.get('date', [])
        for key in date_table.keys():
            if date_table[key]:
                date_url = dates[key]
                break

        easy_apply_url = "&f_AL=true"

        extra_search_terms = [remote_url, job_types_url]
        extra_search_terms_str = '&'.join(term for term in extra_search_terms if len(term) > 0) + easy_apply_url + date_url

        return extra_search_terms_str

    def next_job_page(self, position,job_page):
        self.browser.get("https://www.linkedin.com/jobs/search/?" + self.base_search_url +
                         "&keywords=" + position + "&start=" + str(job_page*25))

        self.avoid_lock()

