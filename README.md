# CareerPilot AI — MVP

A beginner-friendly career toolkit built with Python and Streamlit.

## Features
- Dashboard
- PDF, DOCX and TXT resume text extraction
- Resume keyword overlap checker (not a real ATS score)
- Skill-based matching against sample entry-level role profiles
- Interview practice questions and answer outlines
- SQLite job application tracker

## Setup (Windows PowerShell)

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

If the virtual environment is already created and active, skip the first three commands.

## Notes
- The job profiles are sample profiles, not live vacancies.
- The ATS checker measures keyword overlap only. It does not predict an employer's ATS result.
- Scanned image-only PDFs need OCR and are not supported in this starter version.
- AI API integration and live job search are planned future features.
