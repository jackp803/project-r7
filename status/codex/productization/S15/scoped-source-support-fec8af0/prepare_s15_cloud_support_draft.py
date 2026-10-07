"""Adapt the read-only supporting-case draft to the ten explicit cloud rows."""
from pathlib import Path
base=Path(__file__).resolve().parent
text=(base/'build_s15_strategy_support_draft.py').read_text(encoding='utf-8')
for before,after in (
 ('S15-strategy-support-selection-fec8af0.json','S15-cloud-support-selection-fec8af0.json'),
 ("[f'STR-{number:02d}' for number in range(1,9)]","[f'CLOUD-{number:02d}' for number in range(1,11)]"),
 ('selected_requirement_drafts=8','selected_requirement_drafts=10'),('unselected_v02_requirements=58','unselected_v02_requirements=56'),
 ('S15-strategy-support-draft-fec8af0.json','S15-cloud-support-draft-fec8af0.json')):
    assert before in text,before;text=text.replace(before,after)
target=base/'build_s15_cloud_support_draft.py';assert not target.exists()
target.write_text(text,encoding='utf-8',newline='\n')
print('Prepared explicit ten-row cloud support draft builder')
