from fastapi import FastAPI, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import pdfplumber
import tempfile
from agents import Runner, Agent, set_default_openai_api, set_tracing_disabled, SQLiteSession, AsyncOpenAI, set_default_openai_client

# --- Setup ---
api_key = "AIzaSyCRhMEV0dpTxSVWhy9TDz5843zpcgS2bAA"
MODEL = "gemini-2.0-flash"
client = AsyncOpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=api_key
)

set_default_openai_api("chat_completions")
set_default_openai_client(client=client)
set_tracing_disabled(True)
session = SQLiteSession("conversation_123")

app = FastAPI()

# Allow frontend calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # later restrict to your Next.js domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- PDF Extractor ---
def extract_pdf_text(file_path: str) -> str:
    try:
        with pdfplumber.open(file_path) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text(x_tolerance=1, y_tolerance=1)
                if page_text:
                    text += page_text + "\n"
        return text.strip() if text else "[No extractable text]"
    except Exception as e:
        return f"❌ Error: {e}"

# --- Agent ---
agent = Agent(
    name="Resume Roaster",
    instructions="You are a funny but insightful resume roaster. Roast based on the given text. Be witty but also give serious suggestions.",
    model=MODEL,
    tools=[],
)
@app.post("/roast")
async def roast_resume(
    file: UploadFile = None,
    roast_level: str = Form("Light"),
    roast_status: str = Form("Success"),
    role_type: str = Form("Friend"),
    language: str = Form("English"),
):
    resume_text = "[No resume uploaded]"
    file_name = "Not selected"

    if file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            contents = await file.read()
            tmp.write(contents)
            tmp_path = tmp.name
        resume_text = extract_pdf_text(tmp_path)
        file_name = file.filename

    user_context = f"""
📄 File: {file_name}

🔥 Roast Level: {roast_level}
⚡ Status: {roast_status}
🎭 Role: {role_type}
🌍 Language: {language}
"""

    result = await Runner.run(
        agent,
        input=f"""
Here are the user’s roast preferences:

{user_context}

Here is the resume text extracted from the PDF:

{resume_text}

Now roast this resume according to the user’s settings.
""",
        session=session,
    )

    return {
        "file": file_name,
        "roast_level": roast_level,
        "roast_status": roast_status,
        "role_type": role_type,
        "language": language,
        "resume_text": resume_text[:1000] + ("..." if len(resume_text) > 1000 else ""),
        "roast": result.final_output,
    }

    file: UploadFile,
    roast_level: str = Form(...),
    roast_status: str = Form(...),
    role_type: str = Form(...),
    language: str = Form(...),
):
    # Save uploaded PDF temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        contents = await file.read()
        tmp.write(contents)
        tmp_path = tmp.name

    # Extract text ✅
    resume_text = extract_pdf_text(tmp_path)

    # User context
    user_context = f"""
📄 File: {file.filename}

🔥 Roast Level: {roast_level}
⚡ Status: {roast_status}
🎭 Role: {role_type}
🌍 Language: {language}
"""

    # Run agent with actual text ✅
    result = await Runner.run(
        agent,
        input=f"""
Here are the user’s roast preferences:

{user_context}

Here is the resume text extracted from the PDF:

{resume_text}

Now roast this resume according to the user’s settings.
""",
        session=session,
    )

    return {
        "file": file.filename,
        "roast_level": roast_level,
        "roast_status": roast_status,
        "role_type": role_type,
        "language": language,
        "resume_text": resume_text[:1000] + ("..." if len(resume_text) > 1000 else ""),  # send preview
        "roast": result.final_output,
    }
