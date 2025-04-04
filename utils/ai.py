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
        - Skill 1  
        - Skill 2  
        - Skill 3  
        - Skill 4  
        - Skill 5  

        ### **Cover Letter Guidelines:**
        - Write a **concise and compelling 5-line cover letter**.
        - Express enthusiasm for the role.
        - Highlight **1-2 key strengths** relevant to the job.
        - Mention **matching skills or experience**.
        - End with a **request for further discussion**.

        ###     If the match is **NO**, do not generate missing skills or a cover letter. Only return "NO".

        ### **Example Response Format:**
        YES  
        - Cloud Computing  
        - Python Automation  
        - Database Optimization  
        - CI/CD Pipelines  
        - Microservices Architecture  

        **Cover Letter:**  
        Dear Hiring Manager,  
        I am excited to apply for the [Job Title] at [Company Name]. With my expertise in [Key Skill], I am confident in my ability to contribute to your team. My experience in [Another Relevant Skill] aligns well with your needs. I am eager to bring my expertise to [Company Name] and would welcome the opportunity to discuss further. Looking forward to your response.
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
        # Extract match status (first Yes/No occurrence)
        match_status_line = next((line for line in lines if "Match Status:" in line), "Match Status: NO")
        match_status = "YES" if "YES" in match_status_line else "NO"
        if match_status == "NO":
            return "No", [], "" 
        
        # Extract missing skills
        skill_lines = [line.strip() for line in lines if re.match(r'^\s*[-*]\s+', line)]
        missing_skills = [re.sub(r'^\s*[-*]\s+', '', skill) for skill in skill_lines if skill]

        # Extract cover letter (everything after "Cover Letter:")
        cover_letter_index = next((i for i, line in enumerate(lines) if "Cover Letter:" in line), None)
        cover_letter = "\n".join(lines[cover_letter_index + 1:]).strip() if cover_letter_index else ""

        return match_status, missing_skills, cover_letter

