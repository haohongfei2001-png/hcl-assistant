"""Build-time acquisition of exactly the existing reviewed three-file slice."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.fetch_development_runtime import acquire

if __name__=='__main__':
    # Not user data, not a research checkout, and no provider call.
    acquire(Path('.hcla-runtime'))
