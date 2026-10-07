"""Keep all accepted validation assertions; select the new frontend launcher."""
from pathlib import Path
base=Path(__file__).resolve().parent;target=base/'s14_feedback_acceptance_core.py';assert not target.exists()
raw=(base/'s13_acceptance_integrity.py').read_bytes()
old=b"browser_launcher.parent/'s13_service_ui_frontend.py'";new=b"browser_launcher.parent/'s14_feedback_ui_frontend.py'"
assert raw.count(old)==1
target.write_bytes(raw.replace(old,new))
print('Copied accepted core with only the exact frontend launcher basename changed')
