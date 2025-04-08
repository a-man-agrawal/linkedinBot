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

        system_prompt = """You are an AI evaluating a candidate’s fit for a technical job based on their resume and the job description.

        ### **Decision Criteria:**
        Recommend **YES** if:
        - The candidate meets **at least 65%** of the core requirements.
        - The experience gap is **3 years or less**.
        - The candidate has **relevant transferable skills**.

        Recommend **NO** if:
        - The experience gap is **greater than 3 years**.
        - The candidate is **missing multiple core requirements**.
        - The role is **significantly more senior**.
        - The job requires **specific niche skills or technologies** that the candidate lacks.

        ### **Response Format:**
        **Match Status:** YES / NO

        If YES, also provide:  

        **Missing or Recommended Skills (up to 5):**  
        - List **5 key skills or responsibilities** that are **not in the resume** but are **frequently mentioned or strongly implied** in the job description.
        - Keep each skill **short (2–4 words)** like “Cloud Infrastructure” or “API Design”.
        - Do not include duplicate or overly broad terms like "Software Engineering".
        - Make sure they are **not already present in the resume**.
        - These skills should be **relevant and not entirely misaligned** — they should make the candidate stronger without being unrealistic.


        ### **Referral Message:**
            Generate a short 4–5 line message for requesting a referral. Use the following structure and tone:

            Hi (Name),
            Thanks for connecting with me.
            I'm interested in applying for the (job_title) role at (company_name) and saw you’re currently working there.  
            I believe strengthening my background in areas like (skill_1), (skill_2), and (skill_3) would align well with the role.  
            Would it be possible for you to refer me or point me to the right person?  
            Job link/ID: (job_id)

            Thanks in advance — really appreciate your time! 

            - Mention the job title and company naturally
            - Include 3 recommended/missing skills from the earlier list
            - Keep the tone friendly, concise, and low-pressure
            - Job link/ID:  Use job link attached with description if the actual job ID is not found                         

        ###     If the match is **NO**, do not generate missing skills or a referral messsage. Only return "NO".

        ### **Example Response Format:**
        YES  
        - Cloud Computing  
        - Python Automation  
        - Database Optimization  
        - CI/CD Pipelines  
        - Microservices Architecture  

        Referral Message:  
        Hi John,
        Thanks for connecting with me.  
        I'm interested in applying for the Senior Backend Engineer role at Acme Corp and saw you’re currently working there.  
        I believe strengthening my background in areas like Python Automation, CI/CD Pipelines, and Microservices Architecture would align well with the role.  
        Would it be possible for you to refer me or point me to the right person?  
        Job link/ID: 12345678
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

