from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
from google import genai
from flask_cors import CORS
from PyPDF2 import PdfReader
import json
import re

load_dotenv()

app = Flask(__name__)
CORS(app)

# Initialize Gemini client
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# Temporary storage
resume_text = ""


# =========================
# 🔹 ANALYZE ANSWER
# =========================
@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON received"}), 400

        question = data.get("question")
        answer = data.get("answer")

        if not question or not answer:
            return jsonify({"error": "Missing question or answer"}), 400

        prompt = f"""
You are an interview coach.

Question: {question}
Answer: {answer}

Give:
1. Score out of 10
2. Strengths
3. Mistakes
4. Improved Answer
5. Communication Tips
6. Pronunciation Feedback
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        return jsonify({"result": response.text})

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"error": str(e)})


# =========================
# 🔹 UPLOAD RESUME
# =========================
@app.route("/upload_resume", methods=["POST"])
def upload_resume():
    global resume_text

    try:
        if "resume" not in request.files:
            return jsonify({"error": "No file part"}), 400

        file = request.files["resume"]

        if file.filename == "":
            return jsonify({"error": "No selected file"}), 400

        reader = PdfReader(file)
        text = ""

        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted

        if not text.strip():
            return jsonify({"error": "Could not read resume content"}), 400

        resume_text = text

        print("Resume loaded successfully")
        return jsonify({"message": "Resume uploaded successfully"})

    except Exception as e:
        print("UPLOAD ERROR:", e)
        return jsonify({"error": str(e)})


# =========================
# 🔹 GENERATE QUESTIONS FROM RESUME
# =========================
@app.route("/generate_questions", methods=["GET"])
def generate_questions():
    global resume_text

    try:
        if not resume_text:
            return jsonify({"error": "Upload resume first"}), 400

        prompt = f"""
You are an interview coach.

From the resume below, generate EXACTLY 10 interview questions.

RULES:
- Each question must be SHORT
- One question per line
- No explanations
- No numbering
- No markdown

Resume:
{resume_text}
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        raw = response.text.strip()

        # 🔥 Robust parsing (works even if Gemini misbehaves)
        questions = re.split(r'\?\s*', raw)
        questions = [q.strip() + '?' for q in questions if q.strip()]

        # Remove garbage
        questions = [q for q in questions if len(q) > 15]

        return jsonify({"questions": questions})

    except Exception as e:
        print("QUESTION ERROR:", e)
        return jsonify({"error": str(e)})


# =========================
# 🔹 RUN APP
# =========================
if __name__ == "__main__":
    print("API KEY:", os.getenv("GOOGLE_API_KEY"))
    app.run(debug=True)