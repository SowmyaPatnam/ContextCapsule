"""
ContextCapsule frontend.

Run from the project root (with the backend already running) via:
    streamlit run frontend/app.py
"""

import json
import os

import requests
import streamlit as st

BACKEND_URL = os.environ.get("CONTEXTCAPSULE_BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="ContextCapsule", page_icon="💊", layout="wide")

st.title("💊 ContextCapsule")
st.caption("Portable AI project memory — carry your project context between AI tools.")

tab_create, tab_import, tab_library = st.tabs(["Create Capsule", "Import & Continue", "My Capsules"])


def render_capsule(capsule: dict):
    summary = capsule.get("summary", {})
    meta = capsule.get("metadata", {})

    st.subheader(capsule.get("project_name", "Untitled Project"))
    st.caption(
        f"Extracted via **{meta.get('extraction_method', 'unknown')}** · "
        f"{meta.get('file_count', 0)} file(s) · {meta.get('source_char_count', 0)} chars of conversation"
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**🎯 Goals**")
        goals = summary.get("goals", [])
        if goals:
            for g in goals:
                st.markdown(f"- {g}")
        else:
            st.caption("None detected")

        st.markdown("**✅ Decisions**")
        decisions = summary.get("decisions", [])
        if decisions:
            for d in decisions:
                st.markdown(f"- {d}")
        else:
            st.caption("None detected")

        st.markdown("**📌 Pending Tasks**")
        tasks = summary.get("pending_tasks", [])
        if tasks:
            for t in tasks:
                st.markdown(f"- {t}")
        else:
            st.caption("None detected")

    with col2:
        st.markdown("**📈 Progress**")
        st.write(summary.get("progress", ""))

        st.markdown("**🐞 Errors / Issues**")
        errors = summary.get("errors", [])
        if errors:
            for e in errors:
                st.markdown(f"- {e.get('description')} _(status: {e.get('status')})_")
        else:
            st.caption("None detected")

    code_context = summary.get("code_context", [])
    if code_context:
        st.markdown("**📁 Code Context**")
        for c in code_context:
            with st.expander(f"{c.get('filename')} — {c.get('summary')}"):
                if c.get("snippet"):
                    st.code(c["snippet"])


def build_continuation_prompt(capsule: dict) -> str:
    summary = capsule.get("summary", {})
    lines = [f'I\'m continuing a project called "{capsule.get("project_name")}". Here is my project context:', ""]

    if summary.get("goals"):
        lines.append("Goals:")
        lines.extend(f"- {g}" for g in summary["goals"])
        lines.append("")
    if summary.get("progress"):
        lines.append("Progress so far:")
        lines.append(summary["progress"])
        lines.append("")
    if summary.get("decisions"):
        lines.append("Decisions already made:")
        lines.extend(f"- {d}" for d in summary["decisions"])
        lines.append("")
    if summary.get("errors"):
        lines.append("Known errors/issues:")
        lines.extend(f"- {e.get('description')} (status: {e.get('status')})" for e in summary["errors"])
        lines.append("")
    if summary.get("pending_tasks"):
        lines.append("Pending tasks:")
        lines.extend(f"- {t}" for t in summary["pending_tasks"])
        lines.append("")
    if summary.get("code_context"):
        lines.append("Relevant files:")
        for c in summary["code_context"]:
            lines.append(f"- {c.get('filename')}: {c.get('summary')}")
        lines.append("")

    lines.append("Please pick up from here without asking me to re-explain the above.")
    return "\n".join(lines)


with tab_create:
    st.subheader("Create a new capsule")
    project_name = st.text_input("Project name", key="create_project_name")
    source_platform = st.text_input("Which AI tool is this from? (optional)", key="create_source_platform")
    conversation_text = st.text_area("Paste conversation / notes", height=220, key="create_conversation_text")
    uploaded_files = st.file_uploader("Upload project files (optional)", accept_multiple_files=True, key="create_files")

    if st.button("Extract Capsule", type="primary"):
        if not project_name.strip():
            st.warning("Please enter a project name.")
        elif not conversation_text.strip() and not uploaded_files:
            st.warning("Provide conversation text or upload at least one file.")
        else:
            files_payload = []
            if uploaded_files:
                for f in uploaded_files:
                    files_payload.append(("files", (f.name, f.getvalue())))
            data = {
                "project_name": project_name,
                "conversation_text": conversation_text,
                "source_platform": source_platform or "Unknown",
            }
            try:
                resp = requests.post(
                    f"{BACKEND_URL}/extract",
                    data=data,
                    files=files_payload if files_payload else None,
                    timeout=60,
                )
                resp.raise_for_status()
                st.session_state["draft_capsule"] = resp.json()
            except Exception as e:
                st.error(f"Extraction failed: {e}")

    if "draft_capsule" in st.session_state:
        st.divider()
        render_capsule(st.session_state["draft_capsule"])
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("💾 Save Capsule"):
                try:
                    resp = requests.post(f"{BACKEND_URL}/capsules", json=st.session_state["draft_capsule"], timeout=30)
                    resp.raise_for_status()
                    st.success(f"Saved with ID: {resp.json().get('capsule_id')}")
                except Exception as e:
                    st.error(f"Save failed: {e}")
        with col_b:
            st.download_button(
                "⬇️ Download Capsule JSON",
                data=json.dumps(st.session_state["draft_capsule"], indent=2),
                file_name=f"{(project_name or 'capsule').replace(' ', '_')}.json",
                mime="application/json",
            )

with tab_import:
    st.subheader("Import a capsule and continue")
    imported_file = st.file_uploader("Upload a .json capsule file", type=["json"], key="import_file")
    if imported_file is not None:
        try:
            resp = requests.post(
                f"{BACKEND_URL}/capsules/import",
                files={"file": (imported_file.name, imported_file.getvalue(), "application/json")},
                timeout=30,
            )
            resp.raise_for_status()
            st.session_state["imported_capsule"] = resp.json()
        except Exception as e:
            st.error(f"Import failed: {e}")

    if "imported_capsule" in st.session_state:
        st.divider()
        render_capsule(st.session_state["imported_capsule"])
        st.markdown("**📋 Continuation prompt** — paste this into your next AI chat:")
        st.code(build_continuation_prompt(st.session_state["imported_capsule"]), language="text")

with tab_library:
    st.subheader("My Capsules")
    try:
        resp = requests.get(f"{BACKEND_URL}/capsules", timeout=30)
        resp.raise_for_status()
        capsules = resp.json()
    except Exception as e:
        capsules = []
        st.error(f"Could not load capsules: {e}")

    if not capsules:
        st.caption("No saved capsules yet.")
    else:
        for c in capsules:
            with st.expander(f"{c['project_name']} — {c['created_at']}"):
                st.caption(f"ID: {c['capsule_id']} · Source: {c.get('source_platform')}")
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("View / Load", key=f"view_{c['capsule_id']}"):
                        full = requests.get(f"{BACKEND_URL}/capsules/{c['capsule_id']}", timeout=30).json()
                        st.session_state["imported_capsule"] = full
                        st.info("Loaded into the Import & Continue tab.")
                with col_b:
                    if st.button("🗑️ Delete", key=f"delete_{c['capsule_id']}"):
                        requests.delete(f"{BACKEND_URL}/capsules/{c['capsule_id']}", timeout=30)
                        st.rerun()