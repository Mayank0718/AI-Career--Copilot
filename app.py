import os
import json
import fitz
import google.generativeai as genai

from dotenv import load_dotenv
from flask import Flask, render_template, request,send_file
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
# -------------------------------
# Flask App
# -------------------------------

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")

UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# -------------------------------
# Gemini API
# -------------------------------

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
model = None

if API_KEY:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")

# -------------------------------
# Gemini Wrapper
# -------------------------------

def ask_gemini(prompt):
    if model is None:
        print("Gemini API key is missing. Set GEMINI_API_KEY in your environment.")
        return None

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print("Gemini Error:", e)
        return None

# Store latest resume text
latest_resume = ""
latest_resume = ""
# -------------------------------
# Routes
# -------------------------------

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/interview")
def interview():
    return render_template("interview.html")




def extract_text(pdf_path):

    text = ""

    pdf = fitz.open(pdf_path)

    for page in pdf:
        text += page.get_text()

    pdf.close()

    return text



def analyze_resume(resume_text):

    prompt = f"""
You are an expert ATS Resume Analyzer.

I am an Engineering student , currrently searching for a job and my target roles are trainee software engineer.
Also consider resume does not contains the engineering stream, do not proceed for analyze resume 
Analyze the following resume.

Return ONLY valid JSON.

Format:
{{
  "ats_score": 0,
  "summary": "",
  "strengths": [],
  "missing_skills": [],
  "technical_skills": [],
  "career_suggestions": [],
  "job_roles": [],
  "interview_questions": []
}}

Resume:

{resume_text}
"""

    text = ask_gemini(prompt)

    if text is None:
        return {
            "ats_score": 0,
            "summary": "Gemini API is busy. Please try again.",
            "strengths": [],
            "missing_skills": [],
            "technical_skills": [],
            "career_suggestions": [],
            "job_roles": [],
            "interview_questions": []
        }

    text = text.strip()
    text = text.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(text)

    except Exception:
        ...


@app.route("/upload", methods=["POST"])
def upload():

    if "resume" not in request.files:
        return "No File Uploaded"

    file = request.files["resume"]

    if file.filename == "":
        return "No File Selected"

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)

    file.save(filepath)

    

    global latest_resume

    resume_text = extract_text(filepath)

    latest_resume = resume_text

    analysis = analyze_resume(resume_text)

    generate_pdf(file.filename, analysis)

    print(type(analysis))
    print(analysis)
    return render_template(
    "result.html",
    filename=file.filename,
    ats_score=analysis.get("ats_score", 0),
    summary=analysis.get("summary", ""),
    strengths=analysis.get("strengths", []),
    missing_skills=analysis.get("missing_skills", []),
    technical_skills=analysis.get("technical_skills", []),
    career_suggestions=analysis.get("career_suggestions", []),
    job_roles=analysis.get("job_roles", []),
    interview_questions=analysis.get("interview_questions", [])
)

def generate_pdf(filename, analysis):

    os.makedirs("reports", exist_ok=True)

    pdf_path = os.path.join("reports", "report.pdf")

    doc = SimpleDocTemplate(pdf_path, pagesize=A4)

    styles = getSampleStyleSheet()

    story = []

    story.append(Paragraph("<b>AI Career Copilot Report</b>", styles["Title"]))

    story.append(Paragraph(f"<b>Resume:</b> {filename}", styles["Heading2"]))

    story.append(Paragraph("<br/>", styles["Normal"]))

    story.append(Paragraph(f"<b>ATS Score:</b> {analysis.get('ats_score')}", styles["BodyText"]))

    story.append(Paragraph("<br/>", styles["Normal"]))

    story.append(Paragraph("<b>Professional Summary</b>", styles["Heading2"]))
    story.append(Paragraph(analysis.get("summary", ""), styles["BodyText"]))

    story.append(Paragraph("<br/>", styles["Normal"]))

    story.append(Paragraph("<b>Strengths</b>", styles["Heading2"]))
    for item in analysis.get("strengths", []):
        story.append(Paragraph("• " + item, styles["BodyText"]))

    story.append(Paragraph("<br/>", styles["Normal"]))

    story.append(Paragraph("<b>Missing Skills</b>", styles["Heading2"]))
    for item in analysis.get("missing_skills", []):
        story.append(Paragraph("• " + item, styles["BodyText"]))

    story.append(Paragraph("<br/>", styles["Normal"]))

    story.append(Paragraph("<b>Technical Skills</b>", styles["Heading2"]))
    for item in analysis.get("technical_skills", []):
        story.append(Paragraph("• " + item, styles["BodyText"]))

    story.append(Paragraph("<br/>", styles["Normal"]))

    story.append(Paragraph("<b>Career Suggestions</b>", styles["Heading2"]))
    for item in analysis.get("career_suggestions", []):
        story.append(Paragraph("• " + item, styles["BodyText"]))

    story.append(Paragraph("<br/>", styles["Normal"]))

    story.append(Paragraph("<b>Best Job Roles</b>", styles["Heading2"]))
    for item in analysis.get("job_roles", []):
        story.append(Paragraph("• " + item, styles["BodyText"]))

    story.append(Paragraph("<br/>", styles["Normal"]))

    story.append(Paragraph("<b>Interview Questions</b>", styles["Heading2"]))
    for item in analysis.get("interview_questions", []):
        story.append(Paragraph("• " + item, styles["BodyText"]))

    doc.build(story)

    return pdf_path

@app.route("/download")
def download():
    return send_file(
        "reports/report.pdf",
        as_attachment=True
    )

@app.route("/job-match", methods=["GET", "POST"])
def job_match():

    result = None
    job_description = ""

    if request.method == "POST":

        job_description = request.form.get("job_description", "")

        if not latest_resume:
            return "Please upload a resume first."

        prompt = f"""
You are an expert ATS and career matching system.

Compare the candidate's resume with the given job description.

Return ONLY valid JSON in exactly this format:

{{
    "match_score": 0,
"matching_skills": [],
"missing_skills": [],
"keyword_gaps": [],
"matched_keywords": [],
"important_keywords": [],
"keyword_coverage": 0,
"role_fit": "",
"suggestions": []
}}

For keyword analysis:
- matched_keywords = important job-description keywords already present in the resume.
- important_keywords = important keywords/skills from the job description.
- keyword_coverage = percentage of important keywords covered by the resume.

CANDIDATE RESUME:

{latest_resume}

JOB DESCRIPTION:

{job_description}
"""

        text = ask_gemini(prompt)

        if text is None:
            result = {
                "match_score": 0,
                "matching_skills": [],
                "missing_skills": [],
                "keyword_gaps": [],
                "role_fit": "Gemini API is busy. Please try again.",
                "suggestions": []
            }

        else:

            text = text.strip()

            text = (
                text
                .replace("```json", "")
                .replace("```", "")
                .strip()
            )

            try:
                result = json.loads(text)

            except Exception as e:

                print("Job Match JSON Error:", e)
                print("Gemini Response:", text)

                result = {
                    "match_score": 0,
                    "matching_skills": [],
                    "missing_skills": [],
                    "keyword_gaps": [],
                    "role_fit": "Unable to process AI response.",
                    "suggestions": []
                }

    return render_template(
        "job_match.html",
        result=result,
        job_description=job_description
    )

@app.route("/chat", methods=["GET", "POST"])
def chat():

    answer = ""
    question = ""

    if request.method == "POST":

        question = request.form["question"]

        prompt = f"""
You are an AI Career Coach.

This is the user's resume:

{latest_resume}

User Question:

{question}

Answer professionally.
"""

        answer = ask_gemini(prompt)

        if answer is None:
         answer = "⚠️ Gemini API is busy. Please try again after a minute."

    return render_template(
        "chat.html",
        question=question,
        answer=answer
    )

@app.route("/mock-interview", methods=["GET", "POST"])
def mock_interview():

    global latest_resume

    feedback = ""

    question = "Tell me about yourself."

    if request.method == "POST":

        answer = request.form["answer"]

        prompt = f"""
You are a Senior Technical Interviewer.

Candidate Resume:

{latest_resume}

Interview Question:

{question}

Candidate Answer:

{answer}

Evaluate the answer.

Give output in this format:

⭐ Overall Score : /10

👍 Strengths

❌ Weaknesses

💡 Better Answer

➡ Next Interview Question
"""

        feedback = ask_gemini(prompt)

        if feedback is None:
           
           feedback = "⚠️ Gemini API is busy. Please try again after a minute."
    return render_template(
        "mock_interview.html",
        question=question,
        feedback=feedback
    )

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug_mode = os.getenv("FLASK_DEBUG", "true").lower() in ("1", "true", "yes")
    app.run(host="0.0.0.0", port=port, debug=debug_mode)