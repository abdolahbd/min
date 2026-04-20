import os
import tempfile
import requests
import runpod
import subprocess

def handler(job):
    job_input = job.get("input", {})
    file_url = job_input.get("file_url")

    if not file_url:
        return {"success": False, "error": "file_url required"}

    work_dir = tempfile.mkdtemp()
    input_path = os.path.join(work_dir, "input.pdf")

    try:
        with requests.get(file_url, stream=True, timeout=300) as r:
            r.raise_for_status()
            with open(input_path, "wb") as f:
                for chunk in r.iter_content(1024 * 1024):
                    if chunk:
                        f.write(chunk)

        cmd = [
            "mineru",
            "-p",
            input_path,
            "-o",
            work_dir,
            "--backend",
            "pipeline"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)

        if result.returncode != 0:
            return {
                "success": False,
                "error": "MinerU failed",
                "stdout": result.stdout[-4000:],
                "stderr": result.stderr[-4000:]
            }

        md_file = None
        for root, dirs, files in os.walk(work_dir):
            for name in files:
                if name.endswith(".md"):
                    md_file = os.path.join(root, name)
                    break
            if md_file:
                break

        if not md_file:
            return {"success": False, "error": "no markdown found"}

        with open(md_file, "r", encoding="utf-8", errors="ignore") as f:
            markdown = f.read()

        return {
            "success": True,
            "markdown": markdown[:5000]
        }

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "MinerU timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}

runpod.serverless.start({"handler": handler})