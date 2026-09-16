ContextCapsule is a portable AI project memory tool that helps you save and carry project context between AI conversations and tools.

## ✨ Features

* 🧠 Extracts project context from conversations and files
* 🎯 Captures goals, progress, decisions, tasks, and errors
* 📁 Supports project file uploads
* 💾 Saves capsules using SQLite
* ⬇️ Export capsules as JSON
* 📥 Import capsules and continue working
* 📚 Manage saved capsules

## 🛠️ Tech Stack

* Python
* Streamlit
* FastAPI
* SQLite
* JSON

🚀 Run Locally

## Backend

```bash
uvicorn backend:app --reload
```

## Frontend

```bash
streamlit run frontend/app.py
```

The frontend connects to the FastAPI backend running on `localhost:8000` by default.

 💡 Concept

> **Capture your project context once. Continue anywhere.**

ContextCapsule currently uses a rule-based extraction system to organize project information into a portable capsule.
