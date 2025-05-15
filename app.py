
import streamlit as st
import pdfplumber
import docx
import openai
from langdetect import detect
import openpyxl
import io
import pytesseract
from pdf2image import convert_from_bytes
import os

openai.api_key = st.secrets["openai_api_key"] if "openai_api_key" in st.secrets else "your-api-key"

def extract_text(file):
    if file.name.endswith(".pdf"):
        try:
            with pdfplumber.open(file) as pdf:
                text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
            if not text.strip():
                images = convert_from_bytes(file.read())
                text = "\n".join([pytesseract.image_to_string(img, lang='ara+eng') for img in images])
            return text
        except:
            images = convert_from_bytes(file.read())
            return "\n".join([pytesseract.image_to_string(img, lang='ara+eng') for img in images])
    elif file.name.endswith(".docx"):
        doc = docx.Document(file)
        return "\n".join([para.text for para in doc.paragraphs])
    return ""

def detect_language(text):
    try:
        return detect(text)
    except:
        return "unknown"

def load_saved_constraints():
    if not os.path.exists("constraints.txt"):
        return ""
    with open("constraints.txt", "r", encoding="utf-8") as f:
        return f.read()

def save_constraints(new_rules):
    with open("constraints.txt", "a", encoding="utf-8") as f:
        f.write("\n" + new_rules.strip())

def build_constraint_prompt(static_rules, user_rules):
    all_rules = (static_rules + "\n" + user_rules).strip()
    return f"""
You are a smart bilingual AI assistant for construction cost projects.
Apply the following constraints when analyzing the uploaded document:

{all_rules}

Then extract:
- Project location
- Project type
- Required materials and services
- Warnings or violations
"""

def query_gpt(text, combined_prompt):
    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": combined_prompt},
            {"role": "user", "content": text}
        ]
    )
    return response['choices'][0]['message']['content']

def generate_excel(summary_text):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Project Summary"
    for i, line in enumerate(summary_text.split("\n")):
        ws.cell(row=i + 1, column=1, value=line)
    return wb

st.title("📄 Project Cost Agent (Arabic + English)")
uploaded_file = st.file_uploader("Upload your project document (.pdf or .docx)", type=["pdf", "docx"])
lang_option = st.selectbox("Output Language", ["Auto Detect", "Arabic", "English"])
saved_rules = load_saved_constraints()
st.subheader("📜 Standard Constraints (saved)")
st.code(saved_rules or "No saved constraints yet.")

st.subheader("➕ Add New Permanent Rule")
new_rule = st.text_area("Write a new constraint to save permanently")
if st.button("💾 Save New Rule"):
    save_constraints(new_rule)
    st.success("Rule saved. Reload the page to see it in effect.")

st.subheader("📝 Temporary Rules for This Project")
user_constraints = st.text_area("Write constraints that apply only to this project")

if uploaded_file and st.button("Run Analysis"):
    with st.spinner("Reading document..."):
        text = extract_text(uploaded_file)

    if not text.strip():
        st.error("No readable text found in file.")
    else:
        with st.spinner("Analyzing with GPT..."):
            final_prompt = build_constraint_prompt(saved_rules, user_constraints)
            summary = query_gpt(text, final_prompt)

        st.subheader("📋 Extracted Project Summary")
        st.text(summary)

        if st.button("✅ Approve and Generate Excel"):
            wb = generate_excel(summary)
            buffer = io.BytesIO()
            wb.save(buffer)
            buffer.seek(0)
            st.download_button("Download Excel Report", buffer, file_name="project_summary.xlsx")
