from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Optional
from datetime import datetime
import sqlite3
import json
import uuid
import re
import os

app = FastAPI(
    title="ContextCapsule API",
    description="Portable AI Project Memory Backend",
    version="1.0.0"
)

DATABASE = "contextcapsule.db"


def init_db():
    conn = sqlite3.connect(DATABASE)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS capsules (
            capsule_id TEXT PRIMARY KEY,
            project_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            source_platform TEXT,
            capsule_json TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


init_db()



def read_uploaded_file(filename: str, content: bytes) -> str:
    """
    Convert uploaded project files into readable text.
    """

    extension = os.path.splitext(filename)[1].lower()

    # Text-based files
    text_extensions = {
        ".py", ".txt", ".md", ".json", ".js", ".jsx",
        ".ts", ".tsx", ".html", ".css", ".java",
        ".c", ".cpp", ".h", ".sql", ".xml", ".yaml",
        ".yml", ".csv"
    }

    if extension in text_extensions:
        try:
            return content.decode("utf-8", errors="ignore")
        except Exception:
            return ""

    return f"[Binary file: {filename}]"


def find_matching_lines(text: str, keywords: list) -> list:
    """
    Find useful lines based on keywords.
    """

    results = []

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        lower = line.lower()

        if any(keyword in lower for keyword in keywords):
            if line not in results:
                results.append(line)

    return results[:15]


def detect_technologies(text: str) -> list:
    technologies = [
        "Python",
        "FastAPI",
        "Streamlit",
        "SQLite",
        "JSON",
        "Git",
        "GitHub",
        "Java",
        "JavaScript",
        "React",
        "Node.js",
        "Flask",
        "Django",
        "OpenAI",
        "LLM",
        "MCP"
    ]

    found = []

    for tech in technologies:
        if re.search(
            r"\b" + re.escape(tech) + r"\b",
            text,
            re.IGNORECASE
        ):
            found.append(tech)

    return found


def detect_errors(text: str) -> list:
    lines = find_matching_lines(
        text,
        [
            "error",
            "exception",
            "failed",
            "failure",
            "bug",
            "issue",
            "warning"
        ]
    )

    errors = []

    for line in lines:
        errors.append({
            "description": line,
            "status": "open"
        })

    return errors


def detect_code_context(
    conversation: str,
    file_contents: list
) -> list:

    code_context = []

    # Uploaded files
    for filename, content in file_contents:

        if not content:
            continue

        summary = content[:300].replace("\n", " ")

        snippet = content[:1000]

        code_context.append({
            "filename": filename,
            "summary": summary,
            "snippet": snippet
        })

    # Try to find filenames mentioned in conversation
    filenames = re.findall(
        r"\b[\w.-]+\.(?:py|js|jsx|ts|tsx|java|json|sql|html|css)\b",
        conversation,
        re.IGNORECASE
    )

    for filename in filenames:

        if not any(
            x["filename"] == filename
            for x in code_context
        ):
            code_context.append({
                "filename": filename,
                "summary": "File mentioned in conversation.",
                "snippet": ""
            })

    return code_context[:30]


def generate_summary(conversation: str) -> str:

    sentences = re.split(
        r"(?<=[.!?])\s+",
        conversation.strip()
    )

    sentences = [
        s.strip()
        for s in sentences
        if s.strip()
    ]

    if not sentences:
        return "No conversation summary available."

    return " ".join(sentences[:5])[:1500]


def extract_capsule(
    project_name: str,
    conversation_text: str,
    source_platform: str,
    file_contents: list
):

    combined_text = conversation_text

    for filename, content in file_contents:
        combined_text += f"\n\nFILE: {filename}\n{content}"

    
    goals = find_matching_lines(
        combined_text,
        [
            "goal",
            "objective",
            "aim",
            "purpose",
            "requirement"
        ]
    )

   
    decisions = find_matching_lines(
        combined_text,
        [
            "decided",
            "decision",
            "chosen",
            "choose",
            "using",
            "will use",
            "selected"
        ]
    )

   
    progress_lines = find_matching_lines(
        combined_text,
        [
            "completed",
            "implemented",
            "finished",
            "working",
            "built",
            "created",
            "done"
        ]
    )

    progress = (
        " ".join(progress_lines)
        if progress_lines
        else "No progress information detected."
    )

  
    pending_tasks = find_matching_lines(
        combined_text,
        [
            "todo",
            "pending",
            "remaining",
            "next",
            "need to",
            "should",
            "to do"
        ]
    )

  
    errors = detect_errors(combined_text)

   
    code_context = detect_code_context(
        conversation_text,
        file_contents
    )

   
    technologies = detect_technologies(combined_text)

   
    capsule_id = str(uuid.uuid4())

    now = datetime.now().isoformat()

    capsule = {
        "capsule_id": capsule_id,

        "project_name": project_name,

        "created_at": now,

        "metadata": {
            "source_platform": source_platform,
            "extraction_method": "rule-based prototype",
            "file_count": len(file_contents),
            "source_char_count": len(conversation_text)
        },

        "summary": {
            "overview": generate_summary(conversation_text),

            "goals": goals,

            "progress": progress,

            "decisions": decisions,

            "pending_tasks": pending_tasks,

            "errors": errors,

            "code_context": code_context,

            "technologies": technologies
        }
    }

    return capsule



@app.get("/")
def root():

    return {
        "status": "running",
        "application": "ContextCapsule",
        "message": "Backend is working!"
    }



@app.get("/health")
def health():

    return {
        "status": "healthy"
    }



@app.post("/extract")
async def extract(
    project_name: str = Form(...),
    conversation_text: str = Form(""),
    source_platform: str = Form("Unknown"),
    files: Optional[List[UploadFile]] = File(None)
):

    file_contents = []

    if files:

        for uploaded_file in files:

            try:

                data = await uploaded_file.read()

                text = read_uploaded_file(
                    uploaded_file.filename,
                    data
                )

                file_contents.append(
                    (
                        uploaded_file.filename,
                        text
                    )
                )

            except Exception as e:

                print(
                    f"Could not read {uploaded_file.filename}: {e}"
                )

    if not conversation_text.strip() and not file_contents:

        raise HTTPException(
            status_code=400,
            detail="Conversation text or files are required."
        )

    capsule = extract_capsule(
        project_name=project_name,
        conversation_text=conversation_text,
        source_platform=source_platform,
        file_contents=file_contents
    )

    return capsule



@app.post("/capsules")
def save_capsule(capsule: dict):

    required = [
        "capsule_id",
        "project_name",
        "created_at",
        "metadata",
        "summary"
    ]

    for field in required:

        if field not in capsule:

            raise HTTPException(
                status_code=400,
                detail=f"Missing field: {field}"
            )

    capsule_id = capsule["capsule_id"]

    project_name = capsule["project_name"]

    created_at = capsule["created_at"]

    source_platform = capsule.get(
        "metadata",
        {}
    ).get(
        "source_platform",
        "Unknown"
    )

    now = datetime.now().isoformat()

    conn = sqlite3.connect(DATABASE)

    conn.execute(
        """
        INSERT OR REPLACE INTO capsules
        (
            capsule_id,
            project_name,
            created_at,
            updated_at,
            source_platform,
            capsule_json
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            capsule_id,
            project_name,
            created_at,
            now,
            source_platform,
            json.dumps(capsule)
        )
    )

    conn.commit()
    conn.close()

    return {
        "success": True,
        "capsule_id": capsule_id,
        "message": "Capsule saved successfully."
    }



@app.get("/capsules")
def get_capsules():

    conn = sqlite3.connect(DATABASE)

    cursor = conn.execute(
        """
        SELECT
            capsule_id,
            project_name,
            created_at,
            source_platform
        FROM capsules
        ORDER BY created_at DESC
        """
    )

    rows = cursor.fetchall()

    conn.close()

    result = []

    for row in rows:

        result.append({
            "capsule_id": row[0],
            "project_name": row[1],
            "created_at": row[2],
            "source_platform": row[3]
        })

    # IMPORTANT:
    # App.py expects a LIST directly.
    return result



@app.get("/capsules/{capsule_id}")
def get_capsule(capsule_id: str):

    conn = sqlite3.connect(DATABASE)

    cursor = conn.execute(
        """
        SELECT capsule_json
        FROM capsules
        WHERE capsule_id = ?
        """,
        (capsule_id,)
    )

    row = cursor.fetchone()

    conn.close()

    if not row:

        raise HTTPException(
            status_code=404,
            detail="Capsule not found."
        )

    return json.loads(row[0])



@app.post("/capsules/import")
async def import_capsule(
    file: UploadFile = File(...)
):

    try:

        data = await file.read()

        capsule = json.loads(
            data.decode("utf-8")
        )

    except Exception:

        raise HTTPException(
            status_code=400,
            detail="Invalid JSON capsule file."
        )

    required = [
        "capsule_id",
        "project_name",
        "created_at",
        "metadata",
        "summary"
    ]

    missing = [
        field
        for field in required
        if field not in capsule
    ]

    if missing:

        raise HTTPException(
            status_code=400,
            detail={
                "message": "Invalid Context Capsule.",
                "missing_fields": missing
            }
        )

    capsule_id = capsule["capsule_id"]

    project_name = capsule["project_name"]

    created_at = capsule["created_at"]

    source_platform = capsule.get(
        "metadata",
        {}
    ).get(
        "source_platform",
        "Imported"
    )

    now = datetime.now().isoformat()

    conn = sqlite3.connect(DATABASE)

    conn.execute(
        """
        INSERT OR REPLACE INTO capsules
        (
            capsule_id,
            project_name,
            created_at,
            updated_at,
            source_platform,
            capsule_json
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            capsule_id,
            project_name,
            created_at,
            now,
            source_platform,
            json.dumps(capsule)
        )
    )

    conn.commit()
    conn.close()

    return capsule



@app.delete("/capsules/{capsule_id}")
def delete_capsule(capsule_id: str):

    conn = sqlite3.connect(DATABASE)

    cursor = conn.execute(
        """
        DELETE FROM capsules
        WHERE capsule_id = ?
        """,
        (capsule_id,)
    )

    conn.commit()

    deleted = cursor.rowcount

    conn.close()

    if deleted == 0:

        raise HTTPException(
            status_code=404,
            detail="Capsule not found."
        )

    return {
        "success": True,
        "message": "Capsule deleted successfully."
    }

