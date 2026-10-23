"""Streamlit interface for SlothSort."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from file_tidy import apply_plan, create_plan, scan_folder
from local_ai import DEFAULT_MODEL, suggest_organization

st.set_page_config(page_title="SlothSort", page_icon="🦥", layout="wide")

st.markdown(
    """
    <style>
    .stApp { background: #f7f8f3; }
    .block-container { max-width: 1000px; padding-top: 2.5rem; }
    .hero { padding: 2rem; border-radius: 22px; background: #e8f0df; }
    .hero h1 { color: #203b2e; margin: 0; font-size: 2.7rem; }
    .hero p { color: #435b4b; font-size: 1.08rem; margin-bottom: 0; }
    </style>
    <div class="hero">
      <h1>🦥 SlothSort</h1>
      <p>Let a local AI sort the file pile. You stay in control of every move.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")
st.caption(
    "Only filenames are sent to your local Ollama model. File contents never "
    "leave your computer, and nothing moves until you approve the plan."
)

with st.form("organize"):
    folder = st.text_input(
        "Folder to tidy",
        placeholder=r"C:\Users\you\Downloads",
        help="SlothSort checks files directly inside this folder, not its subfolders.",
    )
    model = st.text_input("Ollama model", value=DEFAULT_MODEL)
    submitted = st.form_submit_button("🪴 Make me a sorting plan", type="primary")

if submitted:
    st.session_state.pop("plan", None)
    if not folder.strip():
        st.error("Enter a folder path to continue.")
    elif not model.strip():
        st.error("Enter the name of an installed Ollama model.")
    else:
        try:
            root, files = scan_folder(folder.strip())
            if not files:
                st.info("That folder has no regular files to organize.")
            else:
                with st.spinner(f"Thinking locally about {len(files)} filenames..."):
                    suggestions = suggest_organization(
                        [file_path.name for file_path in files], model.strip()
                    )
                    plan = create_plan(root, files, suggestions)
                st.session_state["plan"] = (str(root), plan)
        except (OSError, RuntimeError, ValueError) as error:
            st.error(str(error))

stored_plan = st.session_state.get("plan")
if stored_plan:
    root_text, plan = stored_plan
    st.subheader("Your sorting plan")
    st.write(f"**{len(plan)} files** will be organized inside `{root_text}`.")
    st.dataframe(
        [
            {
                "Current name": move.source.name,
                "Category": move.category,
                "New name": move.destination.name,
            }
            for move in plan
        ],
        use_container_width=True,
        hide_index=True,
    )
    st.warning(
        "Review every suggested name and category. Applying the plan moves "
        "files into category folders; it does not delete file contents."
    )
    confirmed = st.checkbox(
        "I reviewed the plan and want to move these files.",
        key="confirm_moves",
    )
    if st.button("Apply sorting plan", type="primary", disabled=not confirmed):
        try:
            apply_plan(plan)
        except OSError as error:
            st.error(str(error))
        else:
            st.session_state.pop("plan", None)
            st.session_state.pop("confirm_moves", None)
            st.success(f"Done. Organized {len(plan)} files in {Path(root_text)}.")
            st.rerun()
