from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
import re
import google.generativeai as genai
import json
import uvicorn

from dotenv import load_dotenv
load_dotenv()   

app = FastAPI()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash')

SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SENDER_EMAIL = "nishantdeswal02@gmail.com"
RESUME_PATH = "nishant-resume.pdf"

RESUME_INFO = """
Nishant Deswal
Email: nishantdeswal02@gmail.com | Phone: 7015654300
Linkedin | Portfolio
Location: Bengaluru, Karnataka, India

EDUCATION:
- Masters in AI & ML, IIIT Lucknow (Aug 2023 - Jun 2025) - CGPA: 8.45
- BSc (hons) Maths, MDU Rohtak (Aug 2020 - Jun 2023) - 75.7%

EXPERIENCE:
Data Engineer at Ambitio, Bengaluru (Oct 2024 - Present)
- Finetuned embedding model (nomic-embed-text) improving similarity search by 56%
- Trained neural network with RLHF for application prediction and shortlisting
- Built scalable ETL pipelines processing 40,000+ records quarterly
- Developed AI sales audit system automating call analysis
- Created AI document evaluation tool for SOPs and LORs
- Tech: Python, Playwright, OpenAI, EC2, LLMs, AWS

Data Engineer at Propques, Lucknow (Apr 2024 - Oct 2024)
- Engineered 30+ extraction scripts with Selenium and Playwright
- Managed noSQL database with 10,000+ records
- Migrated from GCP to DigitalOcean achieving 90% cost reduction
- Tech: Python, Selenium, Flask, MongoDB, GCP, Dialogflow

PROJECTS:
- CVE Data Analysis Platform: NLP-driven platform with LLaMA 3.1 8B, RAG, Flask, MongoDB, Pinecone
- Interview Hub: AI-powered interview platform using Groq, Flask, MongoDB

SKILLS:
- Languages & Frameworks: Django, Langchain, Langgraph, Git, TensorFlow, FastAPI
- Data & Databases: MongoDB, MySQL, PostgreSQL, Data Modeling, Analytics
- Cloud: GCP, AWS, DigitalOcean
- ML & AI: Machine Learning, Deep Learning, NLP, RLHF, Generative AI, RAG, Agentic AI
"""


class JobApplication(BaseModel):
    jd: str


def generate_application_content(jd):
    prompt = f"""Given this job description and my resume, perform these tasks:
1. Extract the email address where applications should be sent
2. Generate a compelling email subject line (max 60 characters)
3. Generate a concise email body highlighting relevant experience

Job Description:
{jd}

My Resume:
{RESUME_INFO}

Email Body Requirements:
- Start with "Hey {{name}}," or "Hey team," (extract hiring manager/recruiter name from JD if available, otherwise use "team")
- Break into 2-3 short paragraphs
- First paragraph: Brief introduction and interest in the role
- Middle paragraph(s): Highlight 2-3 most relevant skills/experiences matching the JD
- Keep total under 150 words
- Professional but conversational tone
- No email addresses, no LinkedIn URLs
- End with: "Thanks,\\nNishant\\n7015654300"

Return response in this exact JSON format:
{{
  "email": "extracted_email@example.com",
  "subject": "subject line here",
  "body": "email body here with proper line breaks"
}}"""

    response = model.generate_content(prompt)
    content = response.text.strip()
    
    content = re.sub(r'^```json\s*', '', content)
    content = re.sub(r'\s*```$', '', content)
    
    data = json.loads(content)
    
    return data['email'], data['subject'], data['body']


def send_email(recipient_email, subject, body):
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = recipient_email
    msg['Subject'] = subject
    
    msg.attach(MIMEText(body, 'plain'))
    
    with open(RESUME_PATH, 'rb') as attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename=Nishant_Deswal_Resume.pdf')
        msg.attach(part)
    
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(SENDER_EMAIL, SMTP_PASSWORD)
        server.send_message(msg)


@app.post("/apply")
async def apply_job(application: JobApplication):
    try:
        recipient_email, subject, body = generate_application_content(application.jd)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate content: {str(e)}")
    
    if not recipient_email or '@' not in recipient_email:
        raise HTTPException(status_code=400, detail="No valid email found in JD")
    
    if not os.path.exists(RESUME_PATH):
        raise HTTPException(status_code=500, detail="Resume file not found")
    
    send_email(recipient_email, subject, body)
    
    return {
        "status": "success",
        "recipient": recipient_email,
        "subject": subject,
        "body": body
    }


@app.get("/")
async def root():
    return {"message": "Job Application API"}

if __name__ == "__main__":
    
    uvicorn.run(app, host="0.0.0.0", port=8000)