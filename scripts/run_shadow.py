"""Run research-only pipeline from repository root."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def main():
    for script in ("test_shadow_performance.py", "shadow_coupon.py", "shadow_performance.py", "shadow_results.py", "shadow_performance.py"):
        subprocess.run([sys.executable, str(ROOT / "scripts" / script)], cwd=ROOT, check=True)

if __name__ == "__main__":
    main()
