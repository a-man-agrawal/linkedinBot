
from pypdf import PdfReader
from openai import OpenAI
import re

class AIResponseGenerator:
    def __init__(self, api_key, personal_info, experience, resume_path, text_resume_path=None, debug=False):
        self.personal_info = personal_info
        self.experience = experience
        self.pdf_resume_path = resume_path
        self.text_resume_path = text_resume_path
        self._resume_content = None
        self._client = OpenAI(api_key=api_key) if api_key else None
        self.debug = debug
    @property
    def resume_content(self):
        if self._resume_content is None:
            # First try to read from text resume if available
            if self.text_resume_path:
                try:
                    with open(self.text_resume_path, 'r', encoding='utf-8') as f:
                        self._resume_content = f.read()
                        print("Successfully loaded text resume")
                        return self._resume_content
                except Exception as e:
                    print(f"Could not read text resume: {str(e)}")

            # Fall back to PDF resume if text resume fails or isn't available
            try:
                content = []
                reader = PdfReader(self.pdf_resume_path)
                for page in reader.pages:
                    content.append(page.extract_text())
                self._resume_content = "\n".join(content)
                print("Successfully loaded PDF resume")
            except Exception as e:
                print(f"Could not extract text from resume PDF: {str(e)}")
                self._resume_content = ""
        return self._resume_content

    def _build_context(self):
        return f"""
        Personal Information:
        - Name: {self.personal_info['First Name']} {self.personal_info['Last Name']}
        - Current Role: {self.experience.get('currentRole', '')}
        - Skills: {', '.join(self.experience.keys())}
        - Professional Summary: {self.personal_info.get('MessageToManager', '')}

        Resume Content (Give the greatest weight to this information, if specified):
        {self.resume_content}
        """

    def generate_response(self, question_text, response_type="text", options=None, max_tokens=100):
        """
        Generate a response using OpenAI's API
        
        Args:
            question_text: The application question to answer
            response_type: "text", "numeric", or "choice"
            options: For "choice" type, a list of tuples containing (index, text) of possible answers
            max_tokens: Maximum length of response
            
        Returns:
            - For text: Generated text response or None
            - For numeric: Integer value or None
            - For choice: Integer index of selected option or None
        """
        if not self._client:
            return None
            
        try:
            context = self._build_context()
            
            system_prompt = {
                "text": "You are a helpful assistant answering job application questions professionally and concisely. Use the candidate's background information and resume to personalize responses.",
                "numeric": "You are a helpful assistant providing numeric answers to job application questions. Based on the candidate's experience, provide a single number as your response. No explanation needed.",
                "choice": "You are a helpful assistant selecting the most appropriate answer choice for job application questions. Based on the candidate's background, select the best option by returning only its index number. No explanation needed."
            }[response_type]

            user_content = f"Using this candidate's background and resume:\n{context}\n\nPlease answer this job application question: {question_text}"
            if response_type == "choice" and options:
                options_text = "\n".join([f"{idx}: {text}" for idx, text in options])
                user_content += f"\n\nSelect the most appropriate answer by providing its index number from these options:\n{options_text}"

            response = self._client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                max_tokens=max_tokens,
                temperature=0.7
            )
            
            answer = response.choices[0].message.content.strip()
            print(f"AI response: {answer}")  # TODO: Put logging behind a debug flag
            
            if response_type == "numeric":
                # Extract first number from response
                numbers = re.findall(r'\d+', answer)
                if numbers:
                    return int(numbers[0])
                return 0
            elif response_type == "choice":
                # Extract the index number from the response
                numbers = re.findall(r'\d+', answer)
                if numbers and options:
                    index = int(numbers[0])
                    # Ensure index is within valid range
                    if 0 <= index < len(options):
                        return index
                return None  # Return None if the index is not within the valid range
                
            return answer
            
        except Exception as e:
            print(f"Error using AI to generate response: {str(e)}")
            return None

    def evaluate_job_fit(self, job_title, job_description):
        """
        Evaluate whether a job is worth applying to based on the candidate's experience and the job requirements
        
        Args:
            job_title: The title of the job posting
            job_description: The full job description text
            
        Returns:
            bool: True if should apply, False if should skip
        """
        if not self._client:
            return True  # Proceed with application if AI not available
            
        try:
            context = self._build_context()
            
            system_prompt = """You are evaluating job fit for technical roles. 
            Recommend APPLY if:
            - Candidate meets 65 percent of the core requirements
            - Experience gap is 2 years or less
            - Has relevant transferable skills
            
            Return SKIP if:
            - Experience gap is greater than 2 years
            - Missing multiple core requirements
            - Role is clearly more senior
            - The role is focused on an uncommon technology or skill that is required and that the candidate does not have experience with
            - The role is a leadership role or a role that requires managing people and the candidate has no experience leading or managing people

            """
            #Consider the candidate's education level when evaluating whether they meet the core requirements. Having higher education than required should allow for greater flexibility in the required experience.
            
            if self.debug:
                system_prompt += """
                You are in debug mode. Return a detailed explanation of your reasoning for each requirement.

                Return APPLY or SKIP followed by a brief explanation.

                Format response as: APPLY/SKIP: [brief reason]"""
            else:
                system_prompt += """Return only APPLY or SKIP."""

            response = self._client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Job: {job_title}\n{job_description}\n\nCandidate:\n{context}"}
                ],
                max_tokens=250 if self.debug else 1,  # Allow more tokens when debug is enabled
                temperature=0.2  # Lower temperature for more consistent decisions
            )
            
            answer = response.choices[0].message.content.strip()
            print(f"AI evaluation: {answer}")
            return answer.upper().startswith('A')  # True for APPLY, False for SKIP
            
        except Exception as e:
            print(f"Error evaluating job fit: {str(e)}")
            return True  # Proceed with application if evaluation fails
