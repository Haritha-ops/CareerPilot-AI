import re
import sqlite3
from datetime import date
from pathlib import Path

import streamlit as st
from google import genai
from dotenv import load_dotenv
import os

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    client = None

# -------------------- App configuration --------------------
st.set_page_config(
    page_title="CareerPilot AI",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_PATH = Path(__file__).with_name("careerpilot.db")

# -------------------- Database --------------------
# -------------------- Gemini AI --------------------
def ask_gemini(prompt):
    if client is None:
        return "Gemini API key not found. Please check your .env file."

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text
    except Exception as e:
        return f"AI request failed: {e}"
def get_connection():
    return sqlite3.connect(DB_PATH)

def initialize_database():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                role TEXT NOT NULL,
                status TEXT NOT NULL,
                applied_on TEXT NOT NULL,
                notes TEXT
            )
        """)

def add_application(company, role, status, applied_on, notes):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO applications
               (company, role, status, applied_on, notes)
               VALUES (?, ?, ?, ?, ?)""",
            (company, role, status, str(applied_on), notes),
        )

def get_applications():
    with get_connection() as conn:
        return conn.execute(
            """SELECT id, company, role, status, applied_on, notes
               FROM applications ORDER BY applied_on DESC, id DESC"""
        ).fetchall()

def update_application_status(application_id, status):
    with get_connection() as conn:
        conn.execute(
            "UPDATE applications SET status = ? WHERE id = ?",
            (status, application_id),
        )

def delete_application(application_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM applications WHERE id = ?", (application_id,))

initialize_database()

# -------------------- Resume text extraction --------------------
def extract_resume_text(uploaded_file):
    file_name = uploaded_file.name.lower()
    raw = uploaded_file.getvalue()

    if file_name.endswith(".txt"):
        return raw.decode("utf-8", errors="ignore")

    if file_name.endswith(".pdf"):
        try:
            from pypdf import PdfReader
            import io
            reader = PdfReader(io.BytesIO(raw))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:
            raise ValueError(f"Could not read this PDF: {exc}")

    if file_name.endswith(".docx"):
        try:
            from docx import Document
            import io
            document = Document(io.BytesIO(raw))
            return "\n".join(paragraph.text for paragraph in document.paragraphs)
        except Exception as exc:
            raise ValueError(f"Could not read this DOCX: {exc}")

    raise ValueError("Please upload a PDF, DOCX, or TXT file.")

# -------------------- Text analysis helpers --------------------
STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "in", "is", "it", "of", "on", "or", "that", "the", "to", "with",
    "will", "you", "your", "we", "our", "this", "have", "has", "using",
    "use", "work", "working", "years", "year", "experience", "ability",
    "knowledge", "skills", "skill", "good", "strong", "including",
}

def words(text):
    return set(
        token for token in re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{1,}", text.lower())
        if token not in STOP_WORDS
    )

def keyword_match(resume_text, job_description):
    resume_words = words(resume_text)
    job_words = words(job_description)
    if not job_words:
        return 0, [], []
    matched = sorted(resume_words & job_words)
    missing = sorted(job_words - resume_words)
    score = round((len(matched) / len(job_words)) * 100)
    return score, matched, missing

SKILL_CATALOG = [
    "python", "sql", "excel", "power bi", "tableau", "pandas", "numpy",
    "machine learning", "data analysis", "data visualization", "statistics",
    "java", "javascript", "html", "css", "react", "git", "github",
    "mongodb", "sqlite", "firebase", "testing", "manual testing",
    "software testing", "api", "rest api", "linux", "networking",
    "cloud", "aws", "azure", "communication", "problem solving",
]

def find_skills(text):
    lower_text = text.lower()
    return [skill for skill in SKILL_CATALOG if skill in lower_text]

JOB_PROFILES = [
    {
        "role": "Junior Python Developer",
        "skills": ["python", "sql", "git", "api", "problem solving"],
        "description": "Build and maintain Python applications, work with APIs and databases.",
    },
    {
        "role": "Junior Data Analyst",
        "skills": ["sql", "excel", "power bi", "pandas", "data analysis", "statistics"],
        "description": "Analyze data, prepare reports, and create dashboards for business teams.",
    },
    {
        "role": "QA / Software Testing Trainee",
        "skills": ["testing", "manual testing", "software testing", "sql", "problem solving"],
        "description": "Test software, document defects, and support quality assurance activities.",
    },
    {
        "role": "IT Support / Cloud Support Trainee",
        "skills": ["networking", "linux", "cloud", "aws", "azure", "communication"],
        "description": "Troubleshoot user and system issues and support cloud infrastructure.",
    },
    {
        "role": "Junior SQL / Database Associate",
        "skills": ["sql", "sqlite", "mongodb", "python", "excel"],
        "description": "Query, maintain, and validate data in relational and NoSQL databases.",
    },
]

# -------------------- Session state --------------------
if "resume_text" not in st.session_state:
    st.session_state.resume_text = ""
if "resume_name" not in st.session_state:
    st.session_state.resume_name = ""
if "quiz_index" not in st.session_state:
    st.session_state.quiz_index = 0

# -------------------- Sidebar navigation --------------------
st.sidebar.title("🚀 CareerPilot AI")
st.sidebar.caption("Your career toolkit")
page = st.sidebar.radio(
    "Navigate",
    [
        "Dashboard",
        "Resume Analyzer",
        "ATS Checker",
        "Job Matcher",
        "Interview Preparation",
        "Application Tracker",
    ],
)
st.sidebar.divider()
st.sidebar.caption("MVP • Built with Python + Streamlit")

# -------------------- Dashboard --------------------
if page == "Dashboard":
    applications = get_applications()
    total = len(applications)
    interviews = sum(1 for row in applications if row[3] == "Interview")
    offers = sum(1 for row in applications if row[3] == "Offer")

    st.title("Your career command centre")
    st.write("Organise your job search, understand your resume, and prepare for interviews.")
    st.caption("A practical career toolkit. AI-powered features will be connected in a later release.")

    c1, c2, c3 = st.columns(3)
    c1.metric("Applications tracked", total)
    c2.metric("Interviews", interviews)
    c3.metric("Offers", offers)

    st.subheader("Explore your tools")
    cards = [
        ("📄 Resume Analyzer", "Upload a resume and extract its text."),
        ("🎯 ATS Checker", "Compare your resume with a job description."),
        ("💼 Job Matcher", "See which sample job profiles match your skills."),
        ("🎤 Interview Preparation", "Practise role-related questions."),
        ("📌 Application Tracker", "Save applications and update their status."),
    ]
    cols = st.columns(2)
    for i, (heading, description) in enumerate(cards):
        with cols[i % 2]:
            st.markdown(f"**{heading}**")
            st.write(description)
            st.divider()

    st.info("Choose a tool from the left navigation menu to get started.")

# -------------------- Resume Analyzer --------------------
elif page == "Resume Analyzer":
    st.title("📄 Resume Analyzer")
    st.write("Upload your resume to extract its text and identify skills.")
    uploaded = st.file_uploader("Choose your resume", type=["pdf", "docx", "txt"])

    if uploaded is not None:
        try:
            extracted = extract_resume_text(uploaded)
            if not extracted.strip():
                st.warning("No selectable text was found. If this is a scanned PDF, it may need OCR.")
            else:
                st.session_state.resume_text = extracted
                st.session_state.resume_name = uploaded.name
                st.success(f"Read resume: {uploaded.name}")
        except ValueError as exc:
            st.error(str(exc))

    if st.session_state.resume_text:
        resume_text = st.session_state.resume_text
        detected = find_skills(resume_text)
        a, b, c = st.columns(3)
        a.metric("Words extracted", len(resume_text.split()))
        b.metric("Skills detected", len(detected))
        c.metric("Resume file", "Loaded")
        st.subheader("Detected skills")
        if detected:
            st.write(" · ".join(detected))
        else:
            st.write("No skills from the current starter list were detected.")
        with st.expander("Preview extracted resume text"):
            st.text_area("Extracted text", resume_text, height=280)
        if st.button("Clear uploaded resume"):
            st.session_state.resume_text = ""
            st.session_state.resume_name = ""
            st.rerun()
    else:
        st.caption("Supported formats: PDF, DOCX, TXT. Scanned image-only PDFs are not supported in this MVP.")

# -------------------- ATS Checker --------------------
elif page == "ATS Checker":
    st.title("🎯 ATS Keyword Match Checker")
    st.write("This starter checker measures keyword overlap. It is not a real employer ATS score.")
    resume_source = st.radio(
        "Resume text source",
        ["Use uploaded resume", "Paste resume text"],
        horizontal=True,
    )
    if resume_source == "Use uploaded resume":
        resume_text = st.session_state.resume_text
        if not resume_text:
            st.warning("Upload a resume first in the Resume Analyzer, or choose 'Paste resume text'.")
    else:
        resume_text = st.text_area("Paste your resume text", height=220)

    job_description = st.text_area("Paste the job description", height=240)

    if st.button("Calculate keyword match", type="primary"):
        if not resume_text.strip():
            st.error("Please provide resume text.")
        elif not job_description.strip():
            st.error("Please paste the job description.")
        else:
            score, matched, missing = keyword_match(resume_text, job_description)
            st.subheader("Keyword match result")
            st.metric("Keyword overlap", f"{score}%")
            st.progress(score / 100)
            left, right = st.columns(2)
            with left:
                st.markdown("**Keywords found**")
                st.write(", ".join(matched) if matched else "No matching keywords found.")
            with right:
                st.markdown("**Keywords not found**")
                st.write(", ".join(missing[:60]) if missing else "No missing keywords in this comparison.")
            st.caption("Score = matched distinct words ÷ distinct job-description words. It does not predict an actual ATS outcome.")

# -------------------- Job Matcher --------------------
elif page == "Job Matcher":
    st.title("💼 Job Matcher")
    st.write("Compare your resume skills with sample entry-level job profiles.")
    skills_text = ""
    if st.session_state.resume_text:
        skills_text = st.session_state.resume_text
        st.success(f"Using uploaded resume: {st.session_state.resume_name}")
    else:
        skills_text = st.text_area(
            "Paste your skills or resume text",
            placeholder="Example: Python, SQL, Excel, Power BI, Git...",
            height=160,
        )

    if st.button("Find matching roles", type="primary"):
        if not skills_text.strip():
            st.error("Upload a resume or enter your skills first.")
        else:
            user_skills = set(find_skills(skills_text))
            if not user_skills:
                st.warning("No recognised skills found. Try adding skills such as Python, SQL, Excel, or Power BI.")
            else:
                st.write("**Skills detected:** " + ", ".join(sorted(user_skills)))
                ranked = []
                for profile in JOB_PROFILES:
                    required = set(profile["skills"])
                    matches = sorted(user_skills & required)
                    match_score = round(len(matches) / len(required) * 100)
                    ranked.append((match_score, profile, matches, sorted(required - user_skills)))
                ranked.sort(key=lambda item: item[0], reverse=True)

                for score, profile, matches, missing in ranked:
                    with st.container(border=True):
                        st.subheader(profile["role"])
                        st.metric("Skills match", f"{score}%")
                        st.progress(score / 100)
                        st.write(profile["description"])
                        st.write("**Matching skills:** " + (", ".join(matches) if matches else "None yet"))
                        st.write("**Skills to develop:** " + (", ".join(missing) if missing else "No gaps in this sample list"))
                st.caption("These are illustrative role profiles, not live vacancies or hiring recommendations.")

# -------------------- Interview Preparation --------------------
elif page == "Interview Preparation":
    st.title("🎤 Interview Preparation")
    st.write("Choose a practice category and reveal a sample answer outline.")
    category = st.selectbox(
        "Choose a category",
        ["Python", "SQL", "Data Analysis", "Software Testing", "HR / Behavioural"],
    )

    question_bank = {
        "Python": [
            ("What is the difference between a list and a tuple?",
             "A list is mutable, so its elements can be changed. A tuple is immutable after creation. Lists use square brackets; tuples commonly use parentheses."),
            ("What is a Python dictionary?",
             "A dictionary stores key-value pairs. Keys are unique and are used to retrieve their associated values."),
            ("What is the purpose of a function?",
             "A function is a reusable block of code that performs a task. It helps organise code and avoid repetition."),
        ],
        "SQL": [
            ("What is the difference between WHERE and HAVING?",
             "WHERE filters rows before grouping. HAVING filters groups after GROUP BY has been applied."),
            ("What is a primary key?",
             "A primary key uniquely identifies each row in a table and cannot contain NULL values."),
            ("What is an INNER JOIN?",
             "INNER JOIN returns rows where the join condition matches in both tables."),
        ],
        "Data Analysis": [
            ("What is data cleaning?",
             "Data cleaning identifies and handles missing, duplicate, inconsistent, or incorrect data before analysis."),
            ("What is the difference between mean and median?",
             "Mean is the arithmetic average. Median is the middle value after sorting and is less affected by extreme values."),
            ("Why use a dashboard?",
             "A dashboard summarises important metrics visually so users can monitor performance and make decisions."),
        ],
        "Software Testing": [
            ("What is the difference between verification and validation?",
             "Verification checks whether the product is being built according to specifications. Validation checks whether it meets user needs."),
            ("What is a test case?",
             "A test case describes preconditions, steps, test data, and expected results used to verify a feature."),
            ("What is regression testing?",
             "Regression testing checks that recent code changes have not broken previously working functionality."),
        ],
        "HR / Behavioural": [
            ("Tell me about yourself.",
             "Use a short structure: education, relevant skills, one project or internship, and the type of role you are seeking."),
            ("Describe a challenge you faced.",
             "Explain the situation, your responsibility, the actions you took, and the result. Be specific and honest."),
            ("Why should we hire you as a fresher?",
             "Connect your foundational skills, project experience, learning ability, and willingness to contribute to the role."),
        ],
    }

    questions = question_bank[category]
    if st.session_state.quiz_index >= len(questions):
        st.session_state.quiz_index = 0
    q, answer = questions[st.session_state.quiz_index]
    st.markdown(f"**Question {st.session_state.quiz_index + 1} of {len(questions)}**")
    st.subheader(q)
    with st.expander("Show answer outline"):
        st.write(answer)

    prev_col, next_col = st.columns(2)
    with prev_col:
        if st.button("← Previous", disabled=st.session_state.quiz_index == 0):
            st.session_state.quiz_index -= 1
            st.rerun()
    with next_col:
        if st.button("Next question →", disabled=st.session_state.quiz_index == len(questions) - 1):
            st.session_state.quiz_index += 1
            st.rerun()
    if st.button("Restart category"):
        st.session_state.quiz_index = 0
        st.rerun()

# -------------------- Application Tracker --------------------
elif page == "Application Tracker":
    st.title("📌 Job Application Tracker")
    st.write("Record applications and keep their status up to date.")

    with st.form("add_application_form", clear_on_submit=True):
        company = st.text_input("Company name")
        role = st.text_input("Job role")
        status = st.selectbox(
            "Application status",
            ["Applied", "Assessment", "Interview", "Offer", "Rejected", "Withdrawn"],
        )
        applied_on = st.date_input("Date applied", value=date.today())
        notes = st.text_area("Notes (optional)")
        submitted = st.form_submit_button("Add application", type="primary")

        if submitted:
            if not company.strip() or not role.strip():
                st.error("Please enter both company name and job role.")
            else:
                add_application(company.strip(), role.strip(), status, applied_on, notes.strip())
                st.success("Application saved.")
                st.rerun()

    st.divider()
    st.subheader("Your applications")
    applications = get_applications()
    if not applications:
        st.info("No applications saved yet. Add your first application above.")
    else:
        for app_id, company, role, current_status, applied_on, notes in applications:
            with st.container(border=True):
                top_left, top_right = st.columns([3, 1])
                with top_left:
                    st.markdown(f"**{role} — {company}**")
                    st.caption(f"Applied: {applied_on}")
                    if notes:
                        st.write(notes)
                with top_right:
                    st.write(current_status)
                edit_col, delete_col = st.columns([3, 1])
                with edit_col:
                    new_status = st.selectbox(
                        "Update status",
                        ["Applied", "Assessment", "Interview", "Offer", "Rejected", "Withdrawn"],
                        index=["Applied", "Assessment", "Interview", "Offer", "Rejected", "Withdrawn"].index(current_status),
                        key=f"status_{app_id}",
                    )
                    if new_status != current_status:
                        if st.button("Save status", key=f"save_{app_id}"):
                            update_application_status(app_id, new_status)
                            st.rerun()
                with delete_col:
                    if st.button("Delete", key=f"delete_{app_id}"):
                        delete_application(app_id)
                        st.rerun()

# -------------------- Footer --------------------
st.sidebar.divider()
st.sidebar.caption("CareerPilot AI • Learning MVP")
