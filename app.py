from flask import Flask, render_template, request
import re
import spacy
import docx
from PyPDF2 import PdfReader
import os

app = Flask(__name__)
nlp = spacy.load("en_core_web_sm")

# Load skills
with open("skills.txt") as f:
    SKILLS_DB = [line.strip().lower() for line in f]

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------- TEXT EXTRACTION ----------------
def extract_text(path):
    text = ""
    if path.endswith(".pdf"):
        reader = PdfReader(path)
        for page in reader.pages:
            if page.extract_text():
                text += page.extract_text()

    elif path.endswith(".docx"):
        doc = docx.Document(path)
        for p in doc.paragraphs:
            text += p.text + "\n"

    elif path.endswith(".txt"):
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()

    return text


# ---------------- NLP FUNCTIONS ----------------
def extract_email(text):
    match = re.findall(r"[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+", text)
    return match[0] if match else "Not Found"


def extract_phone(text):
    patterns = [r"\+92\d{10}", r"92\d{10}", r"03\d{9}"]
    for p in patterns:
        m = re.search(p, text.replace(" ", ""))
        if m:
            return m.group()
    return "Not Found"


def extract_name(text):
    lines = text.strip().split("\n")
    blacklist = ["i am", "developer", "engineer", "resume", "cv"]

    for line in lines[:5]:
        l = line.strip()
        if not l or len(l.split()) > 4:
            continue
        if any(b in l.lower() for b in blacklist):
            continue
        if re.search(r"\d", l):
            continue

        # direct return (best industry trick)
        if 1 <= len(l.split()) <= 3:
            return l

        doc = nlp(l)
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                return ent.text

    return "Not Found"


def extract_skills(text):
    text = text.lower()
    return list(set([s for s in SKILLS_DB if s in text]))


def extract_education(text):
    text = text.lower()

    # 🎯 Degree patterns (STRICT matching)
    patterns = {
        "PhD": [
            r"\bphd\b", r"doctor of philosophy"
        ],
        "Master": [
    r"\bm\.s\b", 
    r"\bmsc\b", 
    r"\bmba\b",
    r"\bmaster of\b",
    r"\bmasters in\b"
        ],
        "Bachelor": [
            r"\bbs\b", r"\bb\.s\b", r"\bbsc\b", r"\bbscs\b",
            r"bachelor of", r"bachelors in"
        ],
        "Intermediate": [
            r"\bintermediate\b", r"\bfsc\b", r"\bf\.sc\b",
            r"\bhssc\b"
        ],
        "Matric": [
            r"\bmatric\b", r"\bssc\b"
        ]
    }

    # 🎯 Ranking (highest first)
    hierarchy = ["PhD", "Master", "Bachelor", "Intermediate", "Matric"]

    found_levels = []

    for level, regex_list in patterns.items():
        for pattern in regex_list:
            if re.search(pattern, text):
                found_levels.append(level)
                break

    # 🎯 Return highest only
    for level in hierarchy:
        if level in found_levels:
            return level

    return "Not Found"


def extract_experience(text):
    text = text.lower()

    years = re.findall(r'(\d+)\+?\s*(years|year|yrs)', text)
    months = re.findall(r'(\d+)\+?\s*(months|month)', text)

    result = []

    if years:
        result.append(f"{max([int(y[0]) for y in years])} years")
    if months:
        result.append(f"{max([int(m[0]) for m in months])} months")
    if "intern" in text:
        result.append("Internship")

    return ", ".join(result) if result else "Not Found"


# ---------------- ROUTES ----------------
@app.route("/", methods=["GET", "POST"])
def index():
    data = None

    if request.method == "POST":
        file = request.files["resume"]
        path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(path)

        text = extract_text(path)

        data = {
            "name": extract_name(text),
            "email": extract_email(text),
            "phone": extract_phone(text),
            "skills": extract_skills(text),
            "education": extract_education(text),
            "experience": extract_experience(text)
        }

    return render_template("index.html", data=data)


if __name__ == "__main__":
    app.run(debug=True)