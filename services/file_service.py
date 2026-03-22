import os
from datetime import datetime
import difflib

def save_backup(folder, hostname_label, content_type, content):
    os.makedirs(folder, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    safe_hostname = hostname_label if hostname_label else "unknown_switch"

    filename = f"{safe_hostname}_{timestamp}_{content_type}.txt"
    filepath = os.path.join(folder, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return filepath

def save_text_file(folder, hostname_label, suffix, content, extension="txt"):
        os.makedirs(folder, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        safe_hostname = hostname_label if hostname_label else "unknown_switch"

        filename = f"{safe_hostname}_{timestamp}_{suffix}.{extension}"
        filepath = os.path.join(folder, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return filepath

def generate_diff(before_text, after_text, from_name="pre-change", to_name="post-change"):
    before_lines = before_text.splitlines()
    after_lines = after_text.splitlines()

    diff = difflib.unified_diff(
        before_lines,
        after_lines,
        fromfile=from_name,
        tofile=to_name,
        lineterm=""
    )

    return "\n".join(diff)