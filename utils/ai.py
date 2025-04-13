import google.genai as genai
from google.genai import types
import fitz
import re
import os

class JobMatchEvaluator:
    def __init__(self,resume_path= None):
        self.gemini_client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
        self.resume_path = resume_path
        self.resume_content = None
    
    def extract_resume_content(self):
        try:
            if self.resume_content :
                return self.resume_content
            
            document = fitz.open(self.resume_path)
            content = [page.get_text() for page in document]
            self.resume_content = "\n".join(content)
        except Exception as e:
            print(f"Could not extract text from resume PDF: {str(e)}")
            self.resume_content = ""
        return self.resume_content
    
    def get_gemini_insights(self, prompt, system_prompt):
        models = ["gemini-2.5-pro-exp-03-25","gemini-2.0-flash","gemini-1.5-flash"]
        for model in models:
            try:
                print(f"Using model: {model}")
                response = self.gemini_client.models.generate_content(
                    model=model,
                    config=types.GenerateContentConfig(system_instruction=system_prompt),
                    contents=prompt)
                return response.text
            except Exception as e:
                error_message = str(e).lower()
                if "rate limit" in error_message or "exceeded" in error_message:
                    print(f"Rate limit reached for {model}, switching to next model...")
                    continue 
                else:
                    raise e 

        return "Error: All Gemini models reached rate limit. Try again later."

    def check_job_match(self, job_description):

        system_prompt = f"""You are an AI evaluating a candidate’s fit for a technical job based on their resume and the job description.

        ### **Decision Criteria:**
        Recommend **YES** if:
        -- The candidate meets **at least 65 percent of the core requirements** listed in the job description.
        - The experience gap is **3 years or less**.
        - The candidate has **relevant transferable skills or industry exposure**.

        Recommend **NO** if:
        - The experience gap is **more than 3 years**.
        - The candidate is **missing multiple core requirements or responsibilities**.
        - The role is **significantly more senior** than the candidate’s past experience.
        - The job requires **niche skills or technologies** that the candidate does not mention.


        ### **Response Format:**
        **Match Status:** YES / NO

        #### If **YES**, also return: 
        **Missing or Recommended Skills (Top 7):**  
        - List **7 key skills, tools, or responsibilities** that are:
        - **Not present in the resume**, or  
        - **Present in an alternate form** but should be **reworded to match the job description terminology** (e.g., use “Regulatory Compliance” instead of “Compliance” or “AML Investigations” instead of “Case Review”).
        - Include **at least 3 technical skills or tools** related to the job (e.g., “Actimize”, “SQL Reporting”, “Power BI”, “Tableau”).
        - The remaining **4 can include soft skills, responsibilities, or industry-specific keywords** (e.g., “Risk Assessment”, “Client Due Diligence”, “Transaction Monitoring”).
        - Each item should be **short and specific (2–4 words)**.
        - Avoid redundant or overly broad terms like “Finance” or “Analysis”.
        - Ensure all items are **relevant, realistic, and aligned** with the candidate’s background.

        ### **Referral Message:**
        Generate a clear, professional, and friendly referral request using the format below:

        Hi (Name),  
        Thanks for connecting!  

        I’m interested in the **(job_title)** role at **(company_name)** and noticed you’re currently working there.  
        I’d really appreciate it if you could refer me for the position.  

        **Job link:** (job_id or job link if ID not available)  

        For context, I’m currently an Associate at SBI with over 4 years of experience in banking operations, client onboarding, KYC/AML compliance, and regulatory risk reviews — including due diligence and transaction monitoring.  

        Thanks so much for your support!  
        **Name** :(Extract from resume)
        ""Email**: (Extract from resume)

        **Referral Message Notes:**
        - Mention the **job title** and **company name** naturally.
        - Message should be **polite and confident**, without sounding too casual or vague.
        - The **About section** should align with common phrasing used in job descriptions.
        - Use the **job link** if a specific **Job ID** is unavailable.
        - End with the candidate’s **name and email**, extracted from the resume or environment variable.
                       
        ###If the match is **NO**, do not generate missing skills or a referral messsage. Only return "NO".

        ### **Example Response Format:**
        YES  
        - SQL Reporting  
        - Regulatory Compliance  
        - Transaction Monitoring  
        - Data Visualization Tools  
        - Client Due Diligence  
        - Risk Assessment  
        - Actimize

        Referral Message:  
        Hi Priya,
        Thanks for connecting!

        I’m interested in the Senior Associate Analyst role at CommBank and noticed you’re currently working there.
        I’d really appreciate it if you could refer me for the position.

        Job link: https://www.commbank.com.au/careers/job/12345678

        For context, I’m currently an Associate at SBI with over 4 years of experience in banking operations, client onboarding, KYC/AML compliance, and regulatory risk reviews — including due diligence and transaction monitoring.

        Thanks so much for your support!
        Name: Anuradha Gangnani
        Email: anuradha.g@example.com
        """

        prompt = (
            f"Resume:\n{self.extract_resume_content()}\n\n"
            f"Job Description:\n{job_description}\n\n"
            f"Evaluate the job fit based on the criteria and format specified above."
        )
        
        response = self.get_gemini_insights(prompt, system_prompt)

        if not response:
            return "No", [], "" 
        
        lines = response.split('\n')

        # Extract match status
        match_status_line = next((line for line in lines if "Match Status:" in line), "Match Status: NO")
        match_status = "YES" if "YES" in match_status_line else "NO"
        if match_status == "NO":
            return "No", [], ""

        # Extract missing skills (up to 5)
        skill_lines = [line.strip() for line in lines if re.match(r'^\s*[-*]\s+', line)]
        missing_skills = [re.sub(r'^\s*[-*]\s+', '', skill) for skill in skill_lines if skill]

        # Extract referral message
        referral_index = next((i for i, line in enumerate(lines) if "Referral Message:" in line), None)
        referral_message = "\n".join(lines[referral_index + 1:]).strip() if referral_index is not None else ""

        return match_status, missing_skills, referral_message

