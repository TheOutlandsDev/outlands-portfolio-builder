"""Explicit maintainer/CI network check of pinned runtime PyPI advisories. MIT."""
import importlib.metadata
import json
import sys
import urllib.request

PINS = {'reportlab': '5.1.0', 'pillow': '13.0.0', 'charset-normalizer': '3.5.2'}
def check():
    results = []
    for name, version in PINS.items():
        if importlib.metadata.version(name) != version: raise ValueError('Installed runtime pin differs: '+name)
        with urllib.request.urlopen(f'https://pypi.org/pypi/{name}/{version}/json', timeout=30) as response:
            data = response.read(2*1024*1024+1)
        if len(data)>2*1024*1024: raise ValueError('Advisory response too large')
        record=json.loads(data)
        if record['info']['version']!=version or not isinstance(record.get('vulnerabilities'),list):
            raise ValueError('Invalid advisory response')
        results.append({'name':name,'version':version,'advisories':[x['id'] for x in record['vulnerabilities']]})
    if any(row['advisories'] for row in results): raise ValueError('PyPI reports a runtime advisory; review before release')
    return {'status':'PASS','packages':len(results),'known_advisories':0}
if __name__=='__main__':
    try:
        if len(sys.argv)!=1: raise ValueError('This check accepts no arguments or custom endpoints')
        print(json.dumps(check()))
    except Exception:
        print(json.dumps({'status':'FAIL','code':'Runtime pins/advisories could not be cleared; inspect installed pins and current PyPI advisories.'}),file=sys.stderr)
        raise SystemExit(1)
