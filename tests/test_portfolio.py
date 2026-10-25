"""Original generated tests. MIT. Never uses a real portfolio or personal receipt."""
import copy
import gc
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest
from unittest import mock
import zipfile
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import portfolio as p
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='outlands-portfolio-test-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.doc, self.example_base = p.read_input(ROOT / 'examples/workshop.json')
    def export(self, **kw):
        target = self.base / ('bundle-' + str(len(list(self.base.iterdir()))))
        result = p.export(self.doc, self.example_base, target, **kw)
        return target, result
    def test_example_validates_with_explicit_claim_labels(self):
        self.assertEqual(len(self.doc['projects']), 2)
        self.assertEqual({x['status'] for q in self.doc['projects'] for x in q['outcomes']}, set(p.STATES))
    def test_no_evidence_read_without_opt_in(self):
        with mock.patch.object(p, 'hash_evidence', side_effect=AssertionError('unexpected content read')):
            data = p.public_data(self.doc, self.example_base)
        self.assertEqual(data['evidence'][0]['check'], 'not_checked')
        self.assertNotIn('source', data['evidence'][0])
    def test_selected_file_checksum_matches_independent_hash(self):
        data = p.public_data(self.doc, self.example_base, True)
        self.assertEqual(data['evidence'][0]['sha256'], hashlib.sha256((self.example_base/'receipt.txt').read_bytes()).hexdigest())
        self.assertEqual(data['evidence'][0]['check'], 'sha256_recorded')
    def test_public_output_omits_evidence_source_path_and_contents(self):
        receipt = self.base/'private-receipt.txt'; receipt.write_text('SECRET_EVIDENCE_CONTENT_123', encoding='utf8')
        self.doc['evidence'][0]['source'] = str(receipt)
        members = p.build_members(self.doc, self.example_base, True)
        for name, data in members.items():
            if name.endswith('.pdf'): data = '\n'.join(x.extract_text() for x in PdfReader(io.BytesIO(data)).pages).encode()
            self.assertNotIn(str(self.base).encode(), data)
            self.assertNotIn(b'SECRET_EVIDENCE_CONTENT_123', data)
            self.assertNotIn(b'private-receipt.txt', data)
    def test_pdf_is_three_pages_with_expected_text_and_neutral_machine_metadata(self):
        members = p.build_members(self.doc, self.example_base)
        reader = PdfReader(io.BytesIO(members['portfolio.pdf']))
        self.assertEqual(len(reader.pages), 3)
        text = '\n'.join(x.extract_text() for x in reader.pages)
        self.assertIn('Alex Example', text); self.assertIn('Planned', text); self.assertIn('Unverified', text)
        self.assertEqual(reader.metadata.author, 'Alex Example')
        self.assertNotIn(str(self.base), str(reader.metadata)); self.assertNotIn('/JavaScript', str(reader.trailer))
    def test_html_escapes_markup_and_has_no_scripts_or_external_assets(self):
        self.doc['profile']['summary'] = '<script>bad()</script> & "quoted"'
        self.doc['projects'][0]['problem'] = '<img src="https://example.invalid/beacon">'
        members = p.build_members(self.doc, self.example_base)
        text = members['index.html'].decode()
        self.assertIn('&lt;script&gt;', text); self.assertNotIn('<script>', text)
        self.assertNotIn('<img', members['case-studies/workshop-inventory.html'].decode())
        self.assertIn('default-src', text)
    def test_pdf_markup_is_text_not_remote_resource_instructions(self):
        self.doc['projects'][0]['summary'] = '<img src="https://example.invalid/secret"/> and <b>literal text</b>'
        with mock.patch.object(socket, 'socket', side_effect=AssertionError('network use')):
            data = p.build_members(self.doc, self.example_base)
        self.assertIn('<img src=', PdfReader(io.BytesIO(data['portfolio.pdf'])).pages[0].extract_text())
    def test_windows_1252_accent_and_typography_are_supported(self):
        self.doc['profile']['name'] = 'René Example'
        self.doc['profile']['summary'] = 'A café project with a € budget and “quoted” text.'
        data = p.build_members(self.doc, self.example_base)
        self.assertIn('René Example', PdfReader(io.BytesIO(data['portfolio.pdf'])).pages[0].extract_text())
    def test_unsupported_font_characters_fail_before_output_creation(self):
        self.doc['profile']['name'] = 'Example \U0001f600'
        target = self.base/'blocked'
        with self.assertRaisesRegex(p.BuildError, 'unsupported PDF character'): p.export(self.doc, self.example_base, target)
        self.assertFalse(target.exists())
    def test_controls_and_unexpected_fields_are_rejected(self):
        for change in [('name', 'bad\x00value'), ('extra', 'private')]:
            doc = copy.deepcopy(self.doc); doc['profile'][change[0]] = change[1]
            with self.assertRaises(p.BuildError): p.validate(doc)
    def test_duplicate_ids_and_unknown_evidence_references_are_rejected(self):
        for kind in ['project', 'evidence', 'reference']:
            doc = copy.deepcopy(self.doc)
            if kind == 'project': doc['projects'][1]['id'] = doc['projects'][0]['id']
            elif kind == 'evidence': doc['evidence'][1]['id'] = doc['evidence'][0]['id']
            else: doc['projects'][0]['outcomes'][0]['evidence'] = ['missing']
            with self.assertRaises(p.BuildError): p.validate(doc)
    def test_path_like_and_reserved_project_ids_are_rejected(self):
        for value in ['../escape', 'x/y', 'C:bad', 'CON', 'con', 'lpt1', '-bad']:
            doc = copy.deepcopy(self.doc); doc['projects'][0]['id'] = value
            with self.assertRaises(p.BuildError): p.validate(doc)
    def test_invalid_kind_and_status_types_are_controlled_errors(self):
        for value in [[], {}, None, 10]:
            doc = copy.deepcopy(self.doc); doc['evidence'][0]['kind'] = value
            with self.assertRaises(p.BuildError): p.validate(doc)
            doc = copy.deepcopy(self.doc); doc['projects'][0]['outcomes'][0]['status'] = value
            with self.assertRaises(p.BuildError): p.validate(doc)
    def test_private_credential_and_active_scheme_urls_are_rejected(self):
        for value in ['javascript:alert(1)', 'http://example.invalid', 'https://user:pass@example.invalid',
                      'https://example.invalid/?token=secret', 'https://127.0.0.1/a', 'https://host.local/a', 'https://example.invalid/#secret']:
            with self.assertRaises(p.BuildError): p.public_url(value)
        self.assertEqual(p.public_url('https://example.invalid/guide'), 'https://example.invalid/guide')
    def test_input_schema_counts_and_text_limits_are_bounded(self):
        for key, value in [('projects', []), ('projects', self.doc['projects']*6), ('evidence', self.doc['evidence']*8), ('schema_version', True)]:
            doc = copy.deepcopy(self.doc); doc[key] = value
            with self.assertRaises(p.BuildError): p.validate(doc)
        self.doc['profile']['summary'] = 'x'*3001
        with self.assertRaises(p.BuildError): p.validate(self.doc)
    def test_json_duplicate_keys_depth_nonfinite_and_large_integer_fail(self):
        for i, value in enumerate(['{"schema_version":1,"schema_version":1}', '['*13+']'*13, '{"n":NaN}', '{"n":'+('9'*5000)+'}']):
            source = self.base/f'input-{i}.json'; source.write_text(value)
            with self.assertRaises(p.BuildError): p.read_input(source)
    def test_input_size_and_invalid_utf8_fail(self):
        for i, data in enumerate([b'x'*(p.MAX_INPUT+1), b'\xff']):
            source = self.base/f'input-{i}.json'; source.write_bytes(data)
            with self.assertRaises(p.BuildError): p.read_input(source)
    def test_existing_output_is_not_changed(self):
        target = self.base/'existing'; target.mkdir(); (target/'keep.txt').write_text('keep')
        with self.assertRaises(p.BuildError): p.export(self.doc, self.example_base, target)
        self.assertEqual((target/'keep.txt').read_text(), 'keep'); self.assertEqual(len(list(target.iterdir())), 1)
    def test_missing_output_parent_is_not_created(self):
        target = self.base/'missing'/'output'
        with self.assertRaises(p.BuildError): p.export(self.doc, self.example_base, target)
        self.assertFalse(target.parent.exists())
    def test_one_and_ten_project_bundles_have_valid_exact_inventories(self):
        for count in [1, 10]:
            self.doc['projects'] = [copy.deepcopy(self.doc['projects'][0]) for _ in range(count)]
            for n, project in enumerate(self.doc['projects']): project['id'] = f'project-{n}'
            target, result = self.export()
            self.assertEqual(result['files'], count+9); self.assertEqual(p.verify_bundle(target)['status'], 'PASS')
    def test_archive_members_exact_bytes_and_sha256_are_independently_checked(self):
        target, result = self.export(check_files=True)
        manifest = json.loads((target/'MANIFEST.json').read_text())
        for record in manifest['files']:
            data = (target/record['path']).read_bytes(); self.assertEqual(len(data), record['bytes'])
            self.assertEqual(hashlib.sha256(data).hexdigest(), record['sha256'])
        archive_data = (target/'portfolio-bundle.zip').read_bytes()
        self.assertEqual(hashlib.sha256(archive_data).hexdigest(), result['archive_sha256'])
        with zipfile.ZipFile(io.BytesIO(archive_data)) as archive:
            for name in archive.namelist(): self.assertEqual(archive.read(name), (target/name).read_bytes())
            self.assertFalse(any(name.endswith('.txt') and name!='README.txt' for name in archive.namelist()))
    def test_identical_inputs_produce_identical_bundles_on_one_runtime(self):
        a, _ = self.export(check_files=True); b, _ = self.export(check_files=True)
        self.assertEqual((a/'portfolio-bundle.zip').read_bytes(), (b/'portfolio-bundle.zip').read_bytes())
    def test_verifier_detects_changed_missing_and_extra_files(self):
        for operation in ['changed', 'missing', 'extra']:
            target, _ = self.export()
            if operation=='changed': (target/'index.html').write_text('changed')
            elif operation=='missing': (target/'portfolio.pdf').unlink()
            else: (target/'unexpected.txt').write_text('extra')
            with self.assertRaises((p.BuildError, OSError)): p.verify_bundle(target)
    def test_verifier_rejects_manifest_path_escape(self):
        target, _ = self.export(); manifest = json.loads((target/'MANIFEST.json').read_text())
        manifest['files'][0]['path'] = '../outside'; (target/'MANIFEST.json').write_text(json.dumps(manifest))
        with self.assertRaises(p.BuildError): p.verify_bundle(target)
    def test_verifier_detects_archive_and_checksum_tampering(self):
        for name in ['SHA256SUMS', 'portfolio-bundle.zip', 'portfolio-bundle.zip.sha256']:
            target, _ = self.export(); (target/name).write_bytes(b'bad')
            with self.assertRaises(p.BuildError): p.verify_bundle(target)
    def test_csv_cells_are_spreadsheet_formula_escaped(self):
        self.doc['evidence'][0]['label'] = '=HYPERLINK("https://example.invalid")'
        data = p.build_members(self.doc, self.example_base)
        self.assertIn("'=HYPERLINK", data['evidence.csv'].decode())
    def test_private_input_save_rebases_file_paths_and_is_exclusive(self):
        target = self.base/'private-input.json'; p.write_input(self.doc, self.example_base, target)
        loaded, _ = p.read_input(target)
        self.assertEqual(Path(loaded['evidence'][0]['source']), self.example_base/'receipt.txt')
        before = target.read_bytes()
        with self.assertRaises(p.BuildError): p.write_input(self.doc, self.example_base, target)
        self.assertEqual(target.read_bytes(), before)
    def test_evidence_size_budget_and_missing_file_fail(self):
        selected = self.base/'receipt'; selected.write_bytes(b'12345')
        with self.assertRaises(p.BuildError): p.hash_evidence(selected, None, 4)
        with self.assertRaises(p.BuildError): p.hash_evidence(self.base/'absent', None, 100)
    def test_formatted_private_input_size_is_checked_before_creation(self):
        target = self.base/'too-large-private.json'
        compact = len(json.dumps(p.validate(self.doc), ensure_ascii=True))
        pretty = len(p.json_bytes(p.validate(self.doc)))
        self.assertLess(compact, pretty)
        with mock.patch.object(p, 'MAX_INPUT', pretty-1):
            with self.assertRaisesRegex(p.BuildError, 'formatted private JSON'): p.write_input(self.doc, self.example_base, target)
        self.assertFalse(target.exists())
    def test_symlink_inputs_are_rejected_where_creation_is_available(self):
        source = self.base/'source'; source.write_text('fixture')
        link = self.base/'alias'
        try: link.symlink_to(source)
        except (OSError, NotImplementedError): self.skipTest('Native symbolic-link fixture unavailable')
        with self.assertRaises(p.BuildError): p.hash_evidence(link, None, 100)
    def test_cancellation_before_export_leaves_no_folder(self):
        stop = threading.Event(); stop.set(); target = self.base/'cancelled'
        with self.assertRaisesRegex(p.BuildError, 'cancelled'): p.export(self.doc, self.example_base, target, cancel=stop)
        self.assertFalse(target.exists())
    def test_cooperative_cancel_during_evidence_hash_is_controlled(self):
        stop = threading.Event(); stop.set()
        with self.assertRaisesRegex(p.BuildError, 'cancelled'): p.hash_evidence(self.example_base/'receipt.txt', stop, p.MAX_FILE)
    def test_cancel_after_rendering_still_prevents_destination_creation(self):
        stop = threading.Event(); target = self.base/'cancel-after-render'
        def progress(value):
            if value.startswith('Verifying ZIP'): stop.set()
        with self.assertRaisesRegex(p.BuildError, 'cancelled'):
            p.export(self.doc, self.example_base, target, cancel=stop, progress=progress)
        self.assertFalse(target.exists())
    def test_evidence_mutation_while_reading_discards_hash(self):
        selected = self.base/'changing.txt'; selected.write_bytes(b'first content')
        original = Path.open
        class ChangingReader:
            def __enter__(self): self.stream = original(selected, 'rb'); return self
            def fileno(self): return self.stream.fileno()
            def read(self, size):
                with original(selected, 'ab') as other: other.write(b'changed')
                return self.stream.read(size)
            def __exit__(self, *args): self.stream.close()
        with mock.patch.object(Path, 'open', return_value=ChangingReader()):
            with self.assertRaisesRegex(p.BuildError, 'grew|changed'): p.hash_evidence(selected, None, 100)
    def test_write_failure_preserves_partial_new_output_without_touching_existing_data(self):
        target = self.base/'partial'; keep = self.base/'keep.txt'; keep.write_text('existing')
        original = Path.open
        def open_file(path, *args, **kwargs):
            if path == target/'portfolio.pdf' and args and args[0]=='xb': raise OSError('controlled fixture write failure')
            return original(path, *args, **kwargs)
        with mock.patch.object(Path, 'open', open_file):
            with self.assertRaisesRegex(p.BuildError, 'partial new directory'): p.export(self.doc, self.example_base, target)
        self.assertTrue(target.exists()); self.assertTrue((target/'index.html').exists()); self.assertEqual(keep.read_text(), 'existing')
    def test_cli_demo_verify_and_existing_destination_status(self):
        target = self.base/'cli'
        with mock.patch('sys.stdout', new_callable=io.StringIO) as out:
            self.assertEqual(p.cli(['--demo','--output',str(target)]), 0)
            self.assertEqual(json.loads(out.getvalue())['status'], 'PASS')
        with mock.patch('sys.stdout', new_callable=io.StringIO): self.assertEqual(p.cli(['--verify',str(target)]), 0)
        with mock.patch('sys.stderr', new_callable=io.StringIO) as error:
            self.assertEqual(p.cli(['--demo','--output',str(target)]), 2)
            self.assertNotIn(str(target), error.getvalue())

class GuiTests(unittest.TestCase):
    def setUp(self):
        try:
            import tkinter as tk
            self.root = tk.Tk(); self.root.withdraw()
        except Exception as error:
            if os.environ.get('PORTFOLIO_REQUIRE_TK') == '1': raise
            self.skipTest('Tk display unavailable: '+type(error).__name__)
        from portfolio_gui import App
        self.app = App(self.root); self.root.update()
        def clean():
            self.app.destroy(); self.root.destroy(); self.app = None; self.root = None
            # Tk objects must be reclaimed on their owning thread, before the next worker starts.
            gc.collect()
        self.addCleanup(clean)
    def test_gui_starts_empty_and_demo_populates_model(self):
        self.assertEqual(self.app.get(self.app.profile_fields['name']), '')
        self.app.demo(); self.assertEqual(self.app.get(self.app.profile_fields['name']), 'Alex Example')
        self.assertEqual(len(self.app.document['projects']), 2); self.assertFalse(self.app.hash_files.get())
    def test_gui_project_edit_survives_switch_and_collect(self):
        self.app.demo(); self.app.set(self.app.project_fields['title'], 'Edited fixture')
        self.app.projects.selection_clear(0,'end'); self.app.projects.selection_set(1); self.app.select_project()
        self.assertEqual(self.app.collect()['projects'][0]['title'], 'Edited fixture')
    def test_gui_worker_exports_real_fixture_without_tk_thread_calls(self):
        self.app.demo()
        with tempfile.TemporaryDirectory(prefix='outlands-portfolio-gui-') as folder:
            target = Path(folder)/'bundle'; self.app.output.set(str(target)); self.app.start_export()
            deadline = time.monotonic()+20
            while self.app.busy and time.monotonic()<deadline: self.root.update(); time.sleep(.02)
            self.assertFalse(self.app.busy); self.assertIn('Export complete', self.app.status.get())
            self.assertEqual(p.verify_bundle(target)['status'],'PASS')
    def test_gui_stop_requests_cancellation_and_retains_worker_state(self):
        self.app.demo(); self.app.output.set('unused-generated-output')
        entered = threading.Event()
        def controlled(_document, _base, _output, _hashes, cancel, _progress):
            entered.set()
            if not cancel.wait(5): raise AssertionError('Stop was not requested')
            raise p.BuildError('cancelled')
        with mock.patch.object(p,'export',controlled):
            self.app.start_export(); self.assertTrue(entered.wait(2)); self.app.request_stop()
            self.assertTrue(self.app.busy)
            deadline=time.monotonic()+5
            while self.app.busy and time.monotonic()<deadline: self.root.update(); time.sleep(.02)
        self.assertFalse(self.app.busy); self.assertIn('cancelled', self.app.status.get())
    def test_gui_plain_text_does_not_interpret_html(self):
        self.app.demo(); self.app.set(self.app.profile_fields['summary'],'<img src="https://example.invalid">')
        self.assertEqual(self.app.get(self.app.profile_fields['summary']),'<img src="https://example.invalid">')
    def test_gui_round_trips_outcome_pipes_quotes_and_newlines(self):
        self.app.demo(); value='A | B with "quoted" text\nand a second line.'
        self.app.document['projects'][0]['outcomes'][0]['statement']=value
        self.app.load_project(0)
        self.assertEqual(self.app.collect()['projects'][0]['outcomes'][0]['statement'],value)

if __name__=='__main__': unittest.main()
