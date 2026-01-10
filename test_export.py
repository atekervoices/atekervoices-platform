#!/usr/bin/env python3

import tempfile
import zipfile
import shutil
from pathlib import Path
import os
import subprocess
import json
from datetime import datetime

# Simulate the export process
output_dir = Path("/app/output")
export_dir = output_dir.parent / "exports"
export_dir.mkdir(exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
export_path = export_dir / f"temp_test_{timestamp}"
export_path.mkdir(exist_ok=True)

# Run export
cmd = ["python", "-m", "export_dataset", str(output_dir), str(export_path), "--threshold", "0.5"]
result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(output_dir.parent))

print(f"Export result: {result.returncode}")
print(f"Export stderr: {result.stderr}")

# Create ZIP
zip_path = export_dir / f"test_export_{timestamp}.zip"
print(f"Creating ZIP at: {zip_path}")

with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
    file_count = 0
    for file_path in export_path.rglob("*"):
        if file_path.is_file():
            arcname = file_path.relative_to(export_path)
            print(f"Adding {arcname} to ZIP")
            zipf.write(file_path, arcname)
            file_count += 1
    print(f"Added {file_count} files to ZIP")

# Check ZIP size
zip_size = zip_path.stat().st_size
print(f"ZIP file size: {zip_size} bytes")

# Clean up
shutil.rmtree(export_path, ignore_errors=True)
print("Cleaned up temp directory")
