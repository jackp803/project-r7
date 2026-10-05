"""Preserve the original launcher; prepare its failure-recording correction."""
from pathlib import Path
project=Path(__file__).resolve().parent.parent
original=project/'artifacts/s13_recovery_ui_qualify.py'
text=original.read_text(encoding='utf-8')
needle="        for name in ['overview.png','protected-paper.png','approval-preview.png','deployment-pause.png','health.png','supervised-health.png']:shutil.copyfile(source/name,output/name)"
assert needle in text
text=text.replace(needle,"        item['browser_errors']=len(browser.get('errors',[]))\n        item['passed']=item['passed'] and item['browser_errors']==0\n        if item['passed']:\n            for name in ['overview.png','protected-paper.png','approval-preview.png','deployment-pause.png','health.png','supervised-health.png']:shutil.copyfile(source/name,output/name)")
destination=project/'artifacts/s13_recovery_ui_qualify_v2.py'
assert not destination.exists()
compile(text,str(destination),'exec')
destination.write_text(text,encoding='utf-8',newline='\n')
print('Prepared corrected collector; original launcher unchanged; corrected collectorNOT_EXECUTED')
