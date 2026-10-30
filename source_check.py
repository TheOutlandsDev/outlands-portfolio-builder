"""Exact reviewed source-only SHA-256 inventory. Original MIT code; stdlib only."""
import ast
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parent
NAMES=sorted([
    '.gitattributes','.gitignore','.github/ISSUE_TEMPLATE/bug_report.yml',
    '.github/ISSUE_TEMPLATE/feature_request.yml','.github/workflows/checks.yml',
    'LICENSE','README.md','CHANGELOG.md','CONTRIBUTING.md','SECURITY.md','THIRD-PARTY-NOTICES.txt',
    'portfolio.py','portfolio_gui.py','requirements.txt','requirements-dev.txt',
    'check_advisories.py','source_check.py','tests/test_portfolio.py','tests/windows_visual_capture.py',
    'examples/workshop.json','examples/receipt.txt','examples/WALKTHROUGH.md',
    'docs/PROVENANCE.md','docs/VALIDATION.md','docs/DEPENDENCIES.json'])
EXCLUDED={'.git','.venv','__pycache__','output','private-inputs','coverage'}
def inventory():
    found=[]
    def visit(folder):
        for path in folder.iterdir():
            if path.name in EXCLUDED or path.name=='.env' or path.name.startswith('.env.'): continue
            if path.is_symlink() or getattr(path,'is_junction',lambda:False)(): raise ValueError('Linked source is unsupported')
            if path.is_dir(): visit(path)
            elif path.name!='SOURCE-MANIFEST.json': found.append(path.relative_to(ROOT).as_posix())
    visit(ROOT)
    if sorted(found)!=NAMES: raise ValueError('Source paths differ from the explicit reviewed allowlist')
    rows=[]
    for name in NAMES:
        data=(ROOT/name).read_bytes()
        if len(data)>1024*1024 or b'\0' in data: raise ValueError('Unsupported source payload: '+name)
        text=data.decode('utf-8')
        if re.search(r'(gh[pousr]_[A-Za-z0-9_]{30,}|github_pat_[A-Za-z0-9_]{40,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|[A-Za-z]:[\\/]Users[\\/])',text):
            raise ValueError('Private-source indicator: '+name)
        if name.endswith('.py'): ast.parse(text,filename=name)
        if name.endswith('.json'): json.loads(text)
        if name.endswith('.md'):
            for link in re.findall(r'\]\(([^)]+)\)',text):
                if link.startswith(('https://','http://','#')): continue
                target=((ROOT/name).parent/link.split('#')[0]).resolve()
                if not target.is_relative_to(ROOT) or not target.exists(): raise ValueError('Broken local document link: '+name)
        rows.append({'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    return rows
def main():
    if sys.argv[1:] not in ([],['--write-manifest']): raise ValueError('Unknown source gate option')
    rows=inventory(); target=ROOT/'SOURCE-MANIFEST.json'
    manifest={'schema':1,'original_source_license':'MIT','files':rows}
    if sys.argv[1:]: target.write_bytes((json.dumps(manifest,indent=2)+'\n').encode())
    if json.loads(target.read_text(encoding='utf-8'))!=manifest: raise ValueError('Reviewed source manifest differs')
    print(json.dumps({'status':'PASS','source_files':len(rows),'bytes':sum(x['bytes'] for x in rows),'runtime_payloads':0}))
if __name__=='__main__':
    try:main()
    except Exception as error: print(str(error),file=sys.stderr);raise SystemExit(1)
