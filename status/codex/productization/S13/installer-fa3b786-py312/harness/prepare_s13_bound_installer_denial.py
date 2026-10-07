from pathlib import Path
base=Path(__file__).resolve().parent
text=(base/'s13_native_installer_denial.py').read_text(encoding='utf-8')
def change(old,new):
    global text
    assert text.count(old)==1,(old,text.count(old));text=text.replace(old,new)
change('from application.qualification import revision_fact,_sanitize',
    'from application.qualification import revision_fact,_sanitize\nfrom s13_installer_package_binding import require_package_identity')
change("    log=output/(name+'.log');started=stamp()", "    require_package_identity(package,identity)\n    log=output/(name+'.log');started=stamp()")
change("        code=owned.wait()", "        code=owned.wait()\n    require_package_identity(package,identity)")
change("report['passed']=True", "require_package_identity(package,identity)\nreport['package_identity_checks']='BEFORE_AND_AFTER_EACH_COMMAND_AND_AT_COMPLETION'\nreport['passed']=True")
path=base/'s13_native_installer_denial_v2.py';assert not path.exists();path.write_text(text,encoding='utf-8',newline='\n')
print('Prepared bound v2 without altering original unbound native evidence')
