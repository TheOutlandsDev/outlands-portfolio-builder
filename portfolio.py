"""Original MIT portfolio/case-study builder. Explicit inputs; no network calls."""
from __future__ import annotations
import argparse
import copy
import csv
import hashlib
import html
import io
import ipaddress
import json
import os
from pathlib import Path
import re
import stat
import sys
import threading
from typing import Callable, NamedTuple
from urllib.parse import urlsplit
import zipfile

VERSION = '1.0.0'
MAX_INPUT = 256 * 1024
MAX_FILE = 16 * 1024 * 1024
MAX_EVIDENCE_BYTES = 64 * 1024 * 1024
MAX_OUTPUT = 32 * 1024 * 1024
MAX_PDF_PAGES = 100
STATES = {'observed': 'Observed (author-stated)', 'reported': 'Reported',
          'planned': 'Planned', 'unverified': 'Unverified'}
ID = re.compile(r'[a-z][a-z0-9-]{0,39}\Z')
FONT_NOTE = 'PDF supports printable Windows-1252 text; HTML and PDF share this validated input.'
CLAIM_NOTE = ('Outcome labels are supplied by the author. File checksums identify selected bytes; '
              'they do not prove that a claim, test or project succeeded.')
CHECK_LABELS = {'sha256_recorded': 'SHA-256 recorded', 'not_checked': 'File not checked', 'reference_only': 'Reference only'}

class BuildError(ValueError):
    """Bounded public error: field identifiers and codes, never input values."""

def check_cancel(cancel: threading.Event | None):
    if cancel is not None and cancel.is_set():
        raise BuildError('cancelled')

def text(value, field, maximum, required=False):
    if not isinstance(value, str) or len(value) > maximum:
        raise BuildError(field + ': invalid text length/type')
    value = value.strip()
    if required and not value:
        raise BuildError(field + ': required')
    if any((ord(c) < 32 and c not in '\n\t') or ord(c) == 127 for c in value):
        raise BuildError(field + ': unsupported control character')
    try:
        value.encode('cp1252')
    except UnicodeEncodeError:
        raise BuildError(field + ': unsupported PDF character; use printable Windows-1252 text') from None
    return value

def keys(value, allowed, required, field):
    if not isinstance(value, dict) or set(value) - set(allowed) or not set(required) <= set(value):
        raise BuildError(field + ': unexpected or missing fields')

def strings(value, field, count, length):
    if not isinstance(value, list) or len(value) > count:
        raise BuildError(field + ': invalid list')
    return [text(x, field, length, True) for x in value]

def identifier(value, field):
    if not isinstance(value, str) or not ID.fullmatch(value) or re.fullmatch(r'(con|prn|aux|nul|com[1-9]|lpt[1-9])', value):
        raise BuildError(field + ': use a lowercase letter followed by letters, digits or hyphens')
    return value

def public_url(value):
    value = text(value, 'evidence.url', 300, True)
    if any(c.isspace() for c in value) or '\\' in value:
        raise BuildError('evidence.url: invalid URL')
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        port = parsed.port
    except ValueError:
        raise BuildError('evidence.url: invalid URL') from None
    if (parsed.scheme != 'https' or not host or parsed.username or parsed.password or
            parsed.query or parsed.fragment or port not in (None, 443) or
            host in {'localhost'} or '.' not in host or host.endswith(('.local', '.localhost', '.internal'))):
        raise BuildError('evidence.url: use a public-style HTTPS URL without credentials, query or fragment')
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        if not re.fullmatch(r'[A-Za-z0-9.-]+', host):
            raise BuildError('evidence.url: unsupported hostname') from None
    else:
        if not address.is_global:
            raise BuildError('evidence.url: private/local addresses are not supported')
    return value

def validate(raw):
    keys(raw, ['schema_version', 'profile', 'projects', 'evidence'],
         ['schema_version', 'profile', 'projects'], 'document')
    if type(raw['schema_version']) is not int or raw['schema_version'] != 1:
        raise BuildError('document: unsupported schema version')
    p = raw['profile']
    keys(p, ['name', 'title', 'summary', 'skills', 'contact'], ['name', 'title', 'summary'], 'profile')
    profile = {'name': text(p['name'], 'profile.name', 120, True),
               'title': text(p['title'], 'profile.title', 160, True),
               'summary': text(p['summary'], 'profile.summary', 3000, True),
               'skills': strings(p.get('skills', []), 'profile.skills', 20, 100),
               'contact': strings(p.get('contact', []), 'profile.contact', 8, 180)}
    if not isinstance(raw['projects'], list) or not 1 <= len(raw['projects']) <= 10:
        raise BuildError('projects: provide 1 to 10 projects')
    evidence = []
    entries = raw.get('evidence', [])
    if not isinstance(entries, list) or len(entries) > 20:
        raise BuildError('evidence: at most 20 entries')
    for item in entries:
        keys(item, ['id', 'label', 'kind', 'source', 'note'], ['id', 'label', 'kind'], 'evidence')
        entry = {'id': identifier(item['id'], 'evidence.id'),
                 'label': text(item['label'], 'evidence.label', 180, True), 'kind': item['kind'],
                 'note': text(item.get('note', ''), 'evidence.note', 600)}
        if not isinstance(entry['kind'], str) or entry['kind'] not in {'file', 'link', 'note'}:
            raise BuildError('evidence.kind: choose file, link or note')
        source = item.get('source', '')
        if entry['kind'] == 'file':
            # A private input path is not portfolio text and can use the filesystem's Unicode.
            if not isinstance(source, str) or not source or len(source) > 2048 or any(ord(c) < 32 for c in source):
                raise BuildError('evidence.source: invalid file path')
            entry['source'] = source
        elif entry['kind'] == 'link':
            entry['source'] = public_url(source)
        elif source:
            raise BuildError('evidence.source: note entries have no source')
        evidence.append(entry)
    eids = {e['id'] for e in evidence}
    if len(eids) != len(evidence):
        raise BuildError('evidence.id: duplicate')
    projects = []
    for p in raw['projects']:
        keys(p, ['id', 'title', 'role', 'summary', 'problem', 'approach', 'limitations', 'outcomes'],
             ['id', 'title', 'role', 'summary', 'outcomes'], 'project')
        result = {'id': identifier(p['id'], 'project.id'),
                  'title': text(p['title'], 'project.title', 180, True),
                  'role': text(p['role'], 'project.role', 180, True),
                  'summary': text(p['summary'], 'project.summary', 3000, True),
                  'problem': text(p.get('problem', ''), 'project.problem', 3000),
                  'approach': text(p.get('approach', ''), 'project.approach', 3000),
                  'limitations': text(p.get('limitations', ''), 'project.limitations', 3000), 'outcomes': []}
        if not isinstance(p['outcomes'], list) or not 1 <= len(p['outcomes']) <= 20:
            raise BuildError('project.outcomes: provide 1 to 20 outcomes')
        for outcome in p['outcomes']:
            keys(outcome, ['statement', 'status', 'evidence'], ['statement', 'status'], 'outcome')
            if not isinstance(outcome['status'], str) or outcome['status'] not in STATES:
                raise BuildError('outcome.status: observed, reported, planned or unverified required')
            refs = strings(outcome.get('evidence', []), 'outcome.evidence', 20, 40)
            if set(refs) - eids or len(set(refs)) != len(refs):
                raise BuildError('outcome.evidence: unknown or duplicate evidence ID')
            result['outcomes'].append({'statement': text(outcome['statement'], 'outcome.statement', 1200, True),
                                       'status': outcome['status'], 'evidence': refs})
        projects.append(result)
    if len({p['id'] for p in projects}) != len(projects):
        raise BuildError('project.id: duplicate')
    normalized = {'schema_version': 1, 'profile': profile, 'projects': projects, 'evidence': evidence}
    if len(json.dumps(normalized, ensure_ascii=True)) > MAX_INPUT:
        raise BuildError('document: normalized input exceeds 256 KiB')
    return normalized

def plain_path(value, existing=True):
    path = Path(os.path.abspath(value))
    if str(path).startswith('\\\\'):
        raise BuildError('path: use trusted local storage')
    for part in list(path.parents)[::-1] + [path]:
        try:
            info = part.lstat()
        except FileNotFoundError:
            if existing:
                raise BuildError('path: input or parent is missing') from None
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(part, 'is_junction', lambda: False)():
            raise BuildError('path: links/junctions are unsupported')
    return path

def read_input(path):
    path = plain_path(path)
    try:
        if not path.is_file() or path.stat().st_size > MAX_INPUT:
            raise BuildError('input: expected a JSON file no larger than 256 KiB')
        data = path.read_bytes()
        if len(data) > MAX_INPUT:
            raise BuildError('input: file grew beyond limit')
        # Bound nesting before parsing; braces inside strings are counted only as text.
        in_string = escaped = False
        depth = 0
        for char in data.decode('utf-8-sig'):
            if in_string:
                if escaped: escaped = False
                elif char == '\\': escaped = True
                elif char == '"': in_string = False
            elif char == '"': in_string = True
            elif char in '[{':
                depth += 1
                if depth > 12: raise BuildError('input: excessive nesting')
            elif char in ']}': depth -= 1
        def pairs(items):
            result = {}
            for key, value in items:
                if key in result: raise BuildError('input: duplicate JSON key')
                result[key] = value
            return result
        def integer(value):
            if len(value) > 16: raise BuildError('input: integer too large')
            return int(value)
        raw = json.loads(data.decode('utf-8-sig'), object_pairs_hook=pairs, parse_int=integer,
                         parse_float=lambda _: (_ for _ in ()).throw(BuildError('input: floating-point values unsupported')),
                         parse_constant=lambda _: (_ for _ in ()).throw(BuildError('input: nonfinite number')))
        return validate(raw), path.parent
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError):
        raise BuildError('input: unreadable or invalid UTF-8 JSON') from None

def hash_evidence(path, cancel, remaining):
    path = plain_path(path)
    try:
        before = path.stat()
        if not stat.S_ISREG(before.st_mode) or before.st_size > min(MAX_FILE, remaining):
            raise BuildError('evidence: regular file must fit the 16 MiB/file and 64 MiB total budgets')
        digest = hashlib.sha256()
        count = 0
        with path.open('rb') as stream:
            opened = os.fstat(stream.fileno())
            if (opened.st_size, opened.st_mtime_ns, opened.st_ino) != (before.st_size, before.st_mtime_ns, before.st_ino):
                raise BuildError('evidence: file changed before reading')
            while True:
                check_cancel(cancel)
                block = stream.read(min(65536, before.st_size - count + 1))
                if not block: break
                count += len(block)
                if count > before.st_size: raise BuildError('evidence: file grew while reading')
                digest.update(block)
        after = path.stat()
        if count != before.st_size or (after.st_size, after.st_mtime_ns, after.st_ino) != (before.st_size, before.st_mtime_ns, before.st_ino):
            raise BuildError('evidence: file changed while reading')
        return digest.hexdigest(), count
    except OSError:
        raise BuildError('evidence: file could not be read') from None

def public_data(document, base, check_files=False, cancel=None):
    document = validate(document)
    result = copy.deepcopy(document)
    total = 0
    for entry in result['evidence']:
        check_cancel(cancel)
        source = entry.pop('source', '')
        entry['check'] = 'reference_only' if entry['kind'] != 'file' else 'not_checked'
        if entry['kind'] == 'link': entry['url'] = source
        if entry['kind'] == 'file' and check_files:
            sha, size = hash_evidence(Path(base) / source, cancel, MAX_EVIDENCE_BYTES - total)
            total += size
            entry.update(check='sha256_recorded', sha256=sha, bytes=size)
    result['app_version'] = VERSION
    result['interpretation'] = CLAIM_NOTE
    return result

CSS = '''body{margin:0;background:#f1f5f8;color:#172a43;font:16px/1.65 system-ui,sans-serif}
main{max-width:980px;margin:36px auto;padding:36px 44px;background:white;border-top:7px solid #08776e}
h1{font-size:2.7rem;line-height:1.15;margin:12px 0}h2{color:#08776e;margin-top:32px}h3{margin-bottom:4px}
.eyebrow{letter-spacing:.12em;text-transform:uppercase;color:#08776e;font-size:.8rem}.muted{color:#526373}
.card{border:1px solid #d8e2e9;padding:20px;margin:18px 0;border-radius:10px}.tag{display:inline-block;padding:2px 9px;background:#e7f2ef;border-radius:4px;font-size:.85rem}
a{color:#075f80;overflow-wrap:anywhere}p,li,code{overflow-wrap:anywhere;white-space:pre-wrap}code{font-size:.85rem}footer{border-top:1px solid #d8e2e9;margin-top:32px;padding-top:18px;font-size:.85rem}
@media(max-width:650px){main{margin:0;padding:22px}h1{font-size:2rem}}@media print{body{background:white}main{margin:0;max-width:none}}
'''
def esc(value): return html.escape(str(value), quote=True)
def page(title, body):
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">'
            f'<title>{esc(title)}</title><style>{CSS}</style></head><body><main>{body}'
            f'<footer>{esc(CLAIM_NOTE)}</footer></main></body></html>')
def case_body(project, evidence):
    content = f'<p class="eyebrow">Project case study</p><h1>{esc(project["title"])}</h1><p class="muted">{esc(project["role"])}</p><p>{esc(project["summary"])}</p>'
    for label, key in [('Problem', 'problem'), ('Approach', 'approach')]:
        if project[key]: content += f'<h2>{label}</h2><p>{esc(project[key])}</p>'
    content += '<h2>Outcomes and evidence</h2>'
    for outcome in project['outcomes']:
        content += f'<section class="card"><span class="tag">{STATES[outcome["status"]]}</span><p>{esc(outcome["statement"])}</p>'
        if outcome['evidence']: content += '<p class="muted">Evidence IDs: ' + esc(', '.join(outcome['evidence'])) + '</p>'
        content += '</section>'
    if project['limitations']: content += f'<h2>Limitations and next steps</h2><p>{esc(project["limitations"])}</p>'
    used = {ref for out in project['outcomes'] for ref in out['evidence']}
    if used:
        content += '<h2>Evidence references</h2>'
        for item in evidence:
            if item['id'] not in used: continue
            content += f'<p><strong>{esc(item["id"])}: {esc(item["label"])}</strong><br>{esc(CHECK_LABELS[item["check"]])}'
            if 'sha256' in item: content += f'<br><code>SHA-256 {item["sha256"]}</code> ({item["bytes"]} bytes)'
            if 'url' in item: content += f'<br><a rel="noreferrer noopener" href="{esc(item["url"])}">{esc(item["url"])}</a>'
            if item['note']: content += '<br>' + esc(item['note'])
            content += '</p>'
    return content

def render_pdf(data, cancel=None):
    try:
        from reportlab.lib import colors
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
        from reportlab.pdfgen.canvas import Canvas
    except ImportError:
        raise BuildError('PDF dependency missing: install the pinned requirements') from None
    styles = {
        'name': ParagraphStyle('Name', fontName='Helvetica-Bold', fontSize=30, leading=35, spaceAfter=12),
        'title': ParagraphStyle('Title', fontName='Helvetica', fontSize=14, leading=19, textColor=colors.HexColor('#526373'), spaceAfter=18),
        'h': ParagraphStyle('Heading', fontName='Helvetica-Bold', fontSize=14, leading=18, spaceBefore=16, spaceAfter=8, textColor=colors.HexColor('#08776e'), keepWithNext=True),
        'body': ParagraphStyle('Body', fontName='Helvetica', fontSize=10.5, leading=15, spaceAfter=10),
        'small': ParagraphStyle('Small', fontName='Helvetica', fontSize=8.5, leading=12, textColor=colors.HexColor('#526373'), spaceAfter=8),
        'badge': ParagraphStyle('Badge', fontName='Helvetica-Bold', fontSize=9, leading=13, textColor=colors.HexColor('#08776e'), spaceBefore=8, spaceAfter=4, keepWithNext=True),
    }
    flow = []
    def add(value, style='body'):
        check_cancel(cancel)
        # All data is text, never ReportLab markup or external-resource instructions.
        flow.append(Paragraph(esc(value).replace('\n', '<br/>').replace('\t', '    '), styles[style]))
    def heading(label): add(label, 'h')
    p = data['profile']
    add('PROJECT PORTFOLIO', 'badge'); add(p['name'], 'name'); add(p['title'], 'title'); add(p['summary'])
    if p['skills']: heading('Skills'); add(' | '.join(p['skills']))
    if p['contact']: heading('Contact'); [add(x, 'small') for x in p['contact']]
    heading('Project index')
    for project in data['projects']:
        add(project['title'], 'badge'); add(project['role'], 'small'); add(project['summary'])
    heading('How to read this portfolio'); add(CLAIM_NOTE, 'small')
    for project in data['projects']:
        flow.append(PageBreak()); add('PROJECT CASE STUDY', 'badge'); add(project['title'], 'name'); add(project['role'], 'title'); add(project['summary'])
        for label, key in [('Problem', 'problem'), ('Approach', 'approach')]:
            if project[key]: heading(label); add(project[key])
        heading('Outcomes and evidence')
        for item in project['outcomes']:
            add(STATES[item['status']], 'badge'); add(item['statement'])
            if item['evidence']: add('Evidence IDs: ' + ', '.join(item['evidence']), 'small')
        if project['limitations']: heading('Limitations and next steps'); add(project['limitations'])
        used = {ref for out in project['outcomes'] for ref in out['evidence']}
        if used:
            heading('Evidence references')
            for e in data['evidence']:
                if e['id'] not in used: continue
                add(e['id'] + ': ' + e['label'], 'badge'); add(CHECK_LABELS[e['check']], 'small')
                if 'sha256' in e: add('SHA-256 ' + e['sha256'] + f' ({e["bytes"]} bytes)', 'small')
                if 'url' in e: add(e['url'], 'small')
                if e['note']: add(e['note'], 'small')
    buffer = io.BytesIO()
    def decorate(canvas, doc):
        check_cancel(cancel)
        if doc.page > MAX_PDF_PAGES: raise BuildError('PDF exceeds the 100-page limit')
        canvas.saveState(); canvas.setStrokeColor(colors.HexColor('#08776e')); canvas.setLineWidth(2)
        canvas.line(48, 752, 564, 752); canvas.setFont('Helvetica', 8); canvas.setFillColor(colors.HexColor('#526373'))
        canvas.drawString(48, 763, 'OUTLANDS PORTFOLIO BUILDER'); canvas.drawRightString(564, 28, str(doc.page)); canvas.restoreState()
    doc = SimpleDocTemplate(buffer, pagesize=(612, 792), leftMargin=48, rightMargin=48,
                            topMargin=60, bottomMargin=48, title=p['name'] + ' - Portfolio',
                            author=p['name'], subject='Author-supplied projects and evidence references', creator='Outlands Portfolio Builder ' + VERSION)
    doc.build(flow, onFirstPage=decorate, onLaterPages=decorate,
              canvasmaker=lambda *a, **kw: Canvas(*a, **{**kw, 'invariant': 1}))
    result = buffer.getvalue()
    if len(result) > 8 * 1024 * 1024: raise BuildError('PDF exceeds 8 MiB')
    return result

def json_bytes(data): return (json.dumps(data, ensure_ascii=True, indent=2, sort_keys=True) + '\n').encode('utf-8')
def sha(data): return hashlib.sha256(data).hexdigest()
def build_members(document, base, check_files=False, cancel=None):
    data = public_data(document, base, check_files, cancel)
    p = data['profile']
    body = f'<p class="eyebrow">Project portfolio</p><h1>{esc(p["name"])}</h1><h2>{esc(p["title"])}</h2><p>{esc(p["summary"])}</p>'
    if p['skills']: body += '<h2>Skills</h2><p>' + esc(' | '.join(p['skills'])) + '</p>'
    if p['contact']: body += '<h2>Contact</h2>' + ''.join('<p>' + esc(x) + '</p>' for x in p['contact'])
    members = {}
    for project in data['projects']:
        check_cancel(cancel)
        name = 'case-studies/' + project['id'] + '.html'
        members[name] = page(project['title'], '<a href="../index.html">Portfolio index</a>' + case_body(project, data['evidence'])).encode('utf-8')
        body += f'<article class="card"><h3><a href="{name}">{esc(project["title"])}</a></h3><p class="muted">{esc(project["role"])}</p><p>{esc(project["summary"])}</p></article>'
    members['index.html'] = page(p['name'], body).encode('utf-8')
    members['portfolio.pdf'] = render_pdf(data, cancel)
    members['portfolio.json'] = json_bytes(data)
    csv_stream = io.StringIO(newline='')
    writer = csv.writer(csv_stream, lineterminator='\n')
    writer.writerow(['id', 'label', 'kind', 'check', 'sha256', 'bytes', 'url', 'note'])
    def csv_cell(value):
        value = str(value)
        # Prevent spreadsheet formula execution when a textual user field is opened.
        return "'" + value if value.startswith(('=', '+', '-', '@', '\t', '\r', '\n')) else value
    for e in data['evidence']:
        writer.writerow([csv_cell(e.get(k, '')) for k in ['id', 'label', 'kind', 'check', 'sha256', 'bytes', 'url', 'note']])
    members['evidence.csv'] = csv_stream.getvalue().encode('utf-8')
    members['README.txt'] = ('Open index.html or portfolio.pdf. Case studies use relative links and no scripts or external assets.\n'
        + CLAIM_NOTE + '\nSelected evidence file contents and their source paths are not bundled.\n'
        'Public text, labels, URLs and hashes still require your privacy and rights review.\n'
        'MANIFEST.json records content-file SHA-256 values; SHA256SUMS also covers that manifest.\n'
        'Checksums detect byte changes, not authenticity or the truth of portfolio claims.\n').encode('utf-8')
    records = [{'path': k, 'bytes': len(v), 'sha256': sha(v)} for k, v in sorted(members.items())]
    members['MANIFEST.json'] = json_bytes({'schema': 'outlands-portfolio-bundle/1', 'files': records})
    members['SHA256SUMS'] = ''.join(sha(v) + '  ' + k + '\n' for k, v in sorted(members.items())).encode('ascii')
    if sum(map(len, members.values())) > MAX_OUTPUT: raise BuildError('Bundle exceeds 32 MiB')
    return members

def zip_members(members):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(members.items()):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0)); info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    result = buffer.getvalue()
    with zipfile.ZipFile(io.BytesIO(result)) as archive:
        if set(archive.namelist()) != set(members) or archive.testzip() is not None:
            raise BuildError('ZIP verification failed')
        for name, data in members.items():
            if archive.read(name) != data: raise BuildError('ZIP bytes differ')
    return result

def verify_bundle(folder):
    """Read-only exact inventory, checksum and ZIP comparison; not authentication."""
    folder = plain_path(folder)
    if not folder.is_dir(): raise BuildError('verify: select a bundle directory')
    def read(name, limit=MAX_OUTPUT):
        target = plain_path(folder / name)
        if not target.is_file() or target.stat().st_size > limit: raise BuildError('verify: member exceeds limits or is not a file')
        data = target.read_bytes()
        if len(data) > limit: raise BuildError('verify: member grew beyond limit')
        return data
    raw_manifest = read('MANIFEST.json', 65536)
    try:
        manifest = json.loads(raw_manifest)
        if manifest.get('schema') != 'outlands-portfolio-bundle/1' or not isinstance(manifest.get('files'), list) or not 6 <= len(manifest['files']) <= 15:
            raise BuildError('verify: invalid manifest')
        members = {}; total = 0
        fixed = {'index.html', 'portfolio.pdf', 'portfolio.json', 'evidence.csv', 'README.txt'}
        for record in manifest['files']:
            keys(record, ['path', 'bytes', 'sha256'], ['path', 'bytes', 'sha256'], 'verify record')
            name = record['path']
            if not isinstance(name, str) or name in members or not (name in fixed or re.fullmatch(r'case-studies/[a-z][a-z0-9-]{0,39}\.html', name)):
                raise BuildError('verify: unexpected or duplicate path')
            if type(record['bytes']) is not int or record['bytes'] < 0 or record['bytes'] > MAX_OUTPUT or not isinstance(record['sha256'], str) or not re.fullmatch(r'[a-f0-9]{64}', record['sha256']):
                raise BuildError('verify: invalid record')
            data = read(name, record['bytes']); total += len(data)
            if total > MAX_OUTPUT or len(data) != record['bytes'] or sha(data) != record['sha256']:
                raise BuildError('verify: changed member bytes')
            members[name] = data
        if not fixed <= set(members): raise BuildError('verify: required content missing')
        members['MANIFEST.json'] = raw_manifest
        expected_sums = ''.join(sha(v) + '  ' + k + '\n' for k, v in sorted(members.items())).encode('ascii')
        if read('SHA256SUMS', 16384) != expected_sums: raise BuildError('verify: checksum list differs')
        members['SHA256SUMS'] = expected_sums
        archive_data = read('portfolio-bundle.zip')
        if read('portfolio-bundle.zip.sha256', 256) != (sha(archive_data) + '  portfolio-bundle.zip\n').encode('ascii'):
            raise BuildError('verify: archive checksum differs')
        expected_paths = set(members) | {'portfolio-bundle.zip', 'portfolio-bundle.zip.sha256'}
        found = set()
        for item in folder.iterdir():
            if item.name == 'case-studies':
                plain_path(item)
                for child in item.iterdir():
                    found.add('case-studies/' + child.name)
                    if len(found) > 20: raise BuildError('verify: too many files')
            else: found.add(item.name)
            if len(found) > 20: raise BuildError('verify: too many files')
        if found != expected_paths: raise BuildError('verify: unlisted or missing output files')
        with zipfile.ZipFile(io.BytesIO(archive_data)) as archive:
            if len(archive.infolist()) != len(members) or set(archive.namelist()) != set(members):
                raise BuildError('verify: ZIP member inventory differs')
            for info in archive.infolist():
                if info.file_size != len(members[info.filename]) or archive.read(info) != members[info.filename]:
                    raise BuildError('verify: ZIP member bytes differ')
        return {'status': 'PASS', 'files': len(expected_paths), 'archive_sha256': sha(archive_data)}
    except (OSError, UnicodeError, json.JSONDecodeError, zipfile.BadZipFile, TypeError, KeyError, AttributeError, RuntimeError, NotImplementedError):
        raise BuildError('verify: unreadable or malformed bundle') from None

def write_input(document, base, output):
    normalized = validate(document)
    for e in normalized['evidence']:
        if e['kind'] == 'file': e['source'] = str(Path(os.path.abspath(Path(base) / e['source'])))
    encoded = json_bytes(normalized)
    if len(encoded) > MAX_INPUT: raise BuildError('input save: formatted private JSON exceeds 256 KiB')
    path = plain_path(output, existing=False)
    plain_path(path.parent)
    if path.suffix.lower() != '.json': raise BuildError('input save: choose a new .json file')
    try:
        with path.open('xb') as stream: stream.write(encoded)
    except OSError:
        raise BuildError('input save: cannot create a new file; existing files are never replaced') from None

class PreparedBundle(NamedTuple):
    """Frozen export bytes; review and writing use this same snapshot."""
    members: dict[str, bytes]
    archive: bytes
    projects: int

def check_output(output):
    output = plain_path(output, existing=False)
    plain_path(output.parent)
    if output.exists(): raise BuildError('output: choose a new directory; existing directories are never replaced')
    return output

def prepare_export(document, base, check_files=False, cancel=None, progress: Callable[[str], None] = lambda _: None):
    progress('Validating content, optional evidence hashes, and PDF layout...')
    members = build_members(document, base, check_files, cancel)
    check_cancel(cancel); progress('Verifying ZIP members and checksums...')
    archive = zip_members(members)
    if len(archive) > MAX_OUTPUT: raise BuildError('ZIP exceeds 32 MiB')
    check_cancel(cancel)
    return PreparedBundle(members, archive, len(document['projects']))

def write_prepared(prepared: PreparedBundle, output, cancel=None):
    output = check_output(output)
    members, archive = prepared.members, prepared.archive
    check_cancel(cancel)
    try:
        # All rendering/verification occurs first. Never merge, overwrite or delete a destination.
        output.mkdir(mode=0o700)
        all_files = {**members, 'portfolio-bundle.zip': archive,
                     'portfolio-bundle.zip.sha256': (sha(archive) + '  portfolio-bundle.zip\n').encode('ascii')}
        for name, data in sorted(all_files.items()):
            check_cancel(cancel)
            target = output / name
            target.parent.mkdir(exist_ok=True)
            with target.open('xb') as stream: stream.write(data)
            if sha(target.read_bytes()) != sha(data): raise BuildError('output: written bytes differ')
    except OSError:
        raise BuildError('output: write failed; a partial new directory may remain') from None
    verify_bundle(output)
    return {'status': 'PASS', 'files': len(all_files), 'projects': prepared.projects,
            'archive_sha256': sha(archive), 'evidence_contents_included': False}

def export(document, base, output, check_files=False, cancel=None, progress: Callable[[str], None] = lambda _: None):
    check_output(output)
    prepared = prepare_export(document, base, check_files, cancel, progress)
    return write_prepared(prepared, output, cancel)

def cli(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', nargs='?', help='Explicit private input JSON')
    parser.add_argument('--output', help='New bundle directory with an existing parent')
    parser.add_argument('--check-evidence', action='store_true', help='Read and hash explicitly selected local evidence files')
    parser.add_argument('--demo', action='store_true', help='Use the bundled fictional example')
    parser.add_argument('--verify', help='Read-only verification of an existing bundle folder')
    parser.add_argument('--version', action='version', version=VERSION)
    args = parser.parse_args(argv)
    if not any([args.input, args.output, args.check_evidence, args.demo, args.verify]):
        from portfolio_gui import main
        main(); return 0
    try:
        if args.verify:
            if args.input or args.output or args.check_evidence or args.demo: raise BuildError('verify cannot be combined with export options')
            print(json.dumps(verify_bundle(args.verify))); return 0
        if not args.output or bool(args.input) == bool(args.demo):
            raise BuildError('choose one input or --demo, plus --output')
        selected = Path(__file__).with_name('examples') / 'workshop.json' if args.demo else args.input
        document, base = read_input(selected)
        result = export(document, base, args.output, args.check_evidence)
        print(json.dumps(result)); return 0
    except (BuildError, OSError) as error:
        print(json.dumps({'status': 'FAIL', 'code': str(error) if isinstance(error, BuildError) else 'filesystem operation failed',
                          'partial_new_output_possible': True}), file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(cli())
