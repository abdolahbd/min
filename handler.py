import os
import glob
import shutil
import tempfile
import subprocess
import requests
import runpod

def download_file(file_url: str, dest_path: str):
    with requests.get(file_url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

def find_markdown_file(output_dir: str):
    patterns = [
        os.path.join(output_dir, "**", "*.md"),
        os.path.join(output_dir, "**", "*.markdown"),
    ]
    matches = []
    for pattern in patterns:
        matches.extend(glob.glob(pattern, recursive=True))
    return matches[0] if matches else None

def handler(job):
    job_input = job.get("input", {})
    file_url = job_input.get("file_url")

    if not file_url:
        return {"success": False, "error": "file_url is required"}

    work_dir = tempfile.mkdtemp(prefix="mineru_job_")
    input_path = os.path.join(work_dir, "input.pdf")
    output_dir = os.path.join(work_dir, "output")

    try:
        os.makedirs(output_dir, exist_ok=True)

        download_file(file_url, input_path)

        cmd = [
            "mineru",
            "-p",
            input_path,
            "-o",
            output_dir
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1800
        )

        if result.returncode != 0:
            return {
                "success": False,
                "error": "MinerU command failed",
                "stdout": result.stdout[-4000:],
                "stderr": result.stderr[-4000:]
            }

        md_file = find_markdown_file(output_dir)
        if not md_file:
            return {
                "success": False,
                "error": "No markdown file found in MinerU output",
                "stdout": result.stdout[-4000:],
                "stderr": result.stderr[-4000:]
            }

        with open(md_file, "r", encoding="utf-8", errors="ignore") as f:
            markdown = f.read()

        return {
            "success": True,
            "markdown": markdown,
            "markdown_file": os.path.basename(md_file)
        }

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "MinerU timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

runpod.serverless.start({"handler": handler})