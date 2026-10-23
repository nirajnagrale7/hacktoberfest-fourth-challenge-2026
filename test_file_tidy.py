from __future__ import annotations

import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from file_tidy import (
    apply_plan,
    create_plan,
    parse_suggestions,
    scan_folder,
)
from local_ai import suggest_organization


class FileTidyTests(unittest.TestCase):
    def test_scan_returns_only_immediate_regular_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "b.txt").write_text("b", encoding="utf-8")
            (root / "a.txt").write_text("a", encoding="utf-8")
            (root / "folder").mkdir()

            scanned_root, files = scan_folder(root)

            self.assertEqual(scanned_root, root.resolve())
            self.assertEqual([item.name for item in files], ["a.txt", "b.txt"])

    def test_model_suggestions_must_match_scanned_files(self) -> None:
        response = {
            "files": [
                {
                    "original_name": "budget draft.txt",
                    "category": "Documents",
                    "new_stem": "Budget Draft",
                }
            ]
        }

        result = parse_suggestions(response, ["budget draft.txt"])

        self.assertEqual(result["budget draft.txt"]["new_stem"], "Budget Draft")
        with self.assertRaisesRegex(ValueError, "did not categorize"):
            parse_suggestions(response, ["budget draft.txt", "photo.png"])

    def test_plan_sanitizes_names_and_preserves_extensions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "odd.txt"
            source.write_text("private", encoding="utf-8")

            plan = create_plan(
                root,
                [source],
                {"odd.txt": {"category": "Documents", "new_stem": "../Budget: Q4"}},
            )

            self.assertEqual(plan[0].destination, root / "Documents" / "Budget-Q4.txt")

    def test_apply_moves_file_without_overwriting(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "notes.txt"
            source.write_text("keep me", encoding="utf-8")
            plan = create_plan(
                root,
                [source],
                {"notes.txt": {"category": "Documents", "new_stem": "Notes"}},
            )

            apply_plan(plan)

            destination = root / "Documents" / "Notes.txt"
            self.assertFalse(source.exists())
            self.assertEqual(destination.read_text(encoding="utf-8"), "keep me")

    def test_plan_refuses_existing_destination(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "notes.txt"
            source.write_text("keep me", encoding="utf-8")
            destination_folder = root / "Documents"
            destination_folder.mkdir()
            (destination_folder / "Notes.txt").write_text("existing", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                create_plan(
                    root,
                    [source],
                    {"notes.txt": {"category": "Documents", "new_stem": "Notes"}},
                )
            self.assertTrue(source.exists())

    def test_apply_refuses_destination_created_after_planning(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "notes.txt"
            source.write_text("keep me", encoding="utf-8")
            plan = create_plan(
                root,
                [source],
                {"notes.txt": {"category": "Documents", "new_stem": "Notes"}},
            )
            destination = root / "Documents" / "Notes.txt"
            destination.parent.mkdir()
            destination.write_text("existing", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                apply_plan(plan)

            self.assertEqual(source.read_text(encoding="utf-8"), "keep me")
            self.assertEqual(destination.read_text(encoding="utf-8"), "existing")

    @patch("local_ai.urllib.request.urlopen")
    def test_ollama_receives_filenames_and_returns_validated_suggestions(
        self, urlopen: MagicMock
    ) -> None:
        generated = {
            "files": [
                {
                    "original_name": "draft.txt",
                    "category": "Documents",
                    "new_stem": "Draft",
                }
            ]
        }
        response = MagicMock()
        response.__enter__.return_value = BytesIO(
            json.dumps({"response": json.dumps(generated)}).encode("utf-8")
        )
        urlopen.return_value = response

        result = suggest_organization(["draft.txt"])

        self.assertEqual(result["draft.txt"]["category"], "Documents")
        request = urlopen.call_args.args[0]
        request_payload = json.loads(request.data.decode("utf-8"))
        self.assertIn('"draft.txt"', request_payload["prompt"])
        self.assertNotIn("file contents", request_payload["prompt"].lower())
        self.assertEqual(request_payload["model"], "qwen2.5:3b")


if __name__ == "__main__":
    unittest.main()
