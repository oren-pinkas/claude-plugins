import json
import subprocess
import sys
import tempfile
import os

def make_jsonl(entries):
    tf = tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False)
    for entry in entries:
        tf.write(json.dumps(entry) + '\n')
    tf.close()
    return tf.name

def run_parser(jsonl_path):
    script = os.path.join(os.path.dirname(__file__), '..', 'hooks', 'parse-transcript.py')
    result = subprocess.run(
        [sys.executable, script, jsonl_path],
        capture_output=True, text=True
    )
    return result.stdout, result.returncode

def test_basic_transcript():
    entries = [
        {"type": "permission-mode", "permissionMode": "default", "sessionId": "abc-123"},
        {"type": "user", "message": {"content": "Fix the login bug in auth.py"}},
        {"type": "assistant", "message": {"content": [
            {"type": "text", "text": "I'll investigate the login bug in auth.py."}
        ]}},
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Read", "input": {"file_path": "/src/auth.py"}}
        ]}},
        {"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "t1", "content": "file contents..."}
        ]}},
        {"type": "assistant", "message": {"content": [
            {"type": "text", "text": "Found the issue. The session check was missing."}
        ]}},
    ]
    path = make_jsonl(entries)
    try:
        output, code = run_parser(path)
        assert code == 0, f"Parser failed with code {code}"
        assert "Fix the login bug" in output
        assert "investigate the login bug" in output
        assert "Found the issue" in output
        assert "tool_result" not in output
        assert "file contents..." not in output
        print("test_basic_transcript: PASS")
    finally:
        os.unlink(path)

def test_empty_transcript():
    path = make_jsonl([])
    try:
        output, code = run_parser(path)
        assert code == 0
        assert output.strip() == "" or "empty" in output.lower()
        print("test_empty_transcript: PASS")
    finally:
        os.unlink(path)

def test_tool_summary():
    entries = [
        {"type": "user", "message": {"content": "Refactor the utils"}},
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Read", "input": {"file_path": "/a.py"}}
        ]}},
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Edit", "input": {"file_path": "/a.py"}}
        ]}},
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Read", "input": {"file_path": "/b.py"}}
        ]}},
        {"type": "assistant", "message": {"content": [
            {"type": "text", "text": "Done refactoring."}
        ]}},
    ]
    path = make_jsonl(entries)
    try:
        output, code = run_parser(path)
        assert code == 0
        assert "Read" in output
        assert "Edit" in output
        print("test_tool_summary: PASS")
    finally:
        os.unlink(path)

if __name__ == "__main__":
    test_basic_transcript()
    test_empty_transcript()
    test_tool_summary()
    print("\nAll tests passed.")
