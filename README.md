# SlothSort

SlothSort is a local-first file organizer for the Downloads folder you have
been meaning to sort. It asks an open-weight model running on your computer to
suggest a category and a clearer name for each file, then shows you a preview.
Nothing moves until you review the plan and confirm it.

## Run locally

1. Install [Ollama](https://ollama.com/) and download a small open-weight model:

   ```powershell
   ollama pull qwen2.5:3b
   ```

2. In this folder, install the app and run it:

   ```powershell
   python -m pip install -r requirements.txt
   streamlit run app.py
   ```

3. Open the local Streamlit URL, enter the folder path, and select **Make me a
   sorting plan**. Review the proposed changes and explicitly confirm before
   files are moved.

Ollama must be running locally. The first model download needs internet access;
after that, inference runs on your computer.

## Privacy and safety

- SlothSort sends filenames only to Ollama on `localhost`; it never reads or
  uploads file contents.
- It scans only regular files directly inside the chosen folder (not
  subfolders), with a maximum of 100 files per plan.
- It only proposes destinations in a fixed set of category folders.
- It previews all moves, requires confirmation, and refuses to overwrite an
  existing destination.
- The model output is treated as untrusted: categories are allowlisted and
  suggested names are sanitized before use.

Always review the preview before applying it. Start with a test folder if this
is your first time using the app.

## Tests

Run the standard-library test suite:

```powershell
python -m unittest -v
```

## Why open innovation matters

Personal filenames can reveal projects, clients, and habits. A local
open-weight model means those names stay on the user's own computer instead
of being sent to a hosted AI API. Once downloaded, the model works without a
per-file API charge, and users can inspect the prompt, change the categories,
or swap to another Ollama-compatible model.
