
import streamlit as st
import pdfplumber
import docx
import openai
from langdetect import detect
import io
import pytesseract
from pdf2image import convert_from_bytes
import os

# 🔐 Set API key
openai.api_key = st.secrets["openai_api_key"] if "openai_api_key" in st.secrets else "your-api-key"

# 📁 Phase 1: Book Upload & Analysis
st.title("📘 Phase 1 – Project Book Analysis")

uploaded_book = st.file_uploader("Upload the Project Book (.pdf or .docx)", type=["pdf", "docx"])

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

def analyze_book(text):
    prompt = f"""
You are a bilingual assistant. Analyze the following project book text and extract the following:
- Project Location (mention region, neighborhood or any address details)
- Project Title (inferred from heading or keywords)
- CD Availability (Does it mention a CD or drawing?)

Explain how you found each item.

Text:
{text}
"""
    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[{"role": "system", "content": "You are a construction project assistant."},
                  {"role": "user", "content": prompt}]
    )
    return response['choices'][0]['message']['content']

if uploaded_book:
    with st.spinner("Reading and analyzing project book..."):
        text = extract_text(uploaded_book)
        if not text:
            st.error("No readable text found in the file.")
        else:
            result = analyze_book(text)
            st.subheader("📄 Book Analysis Summary")
            st.text(result)
            if st.button("✅ Approve & Proceed to Phase 1.5"):
                st.session_state.phase1_approved = True
