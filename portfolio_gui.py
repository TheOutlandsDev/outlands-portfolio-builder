"""Original MIT Tk desktop editor. Exports use an isolated in-memory document copy."""
from __future__ import annotations
import copy
import csv
import io
import os
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import portfolio as core

def empty_document():
    return {'schema_version': 1, 'profile': {'name': '', 'title': '', 'summary': '', 'skills': [], 'contact': []},
            'projects': [], 'evidence': []}

class App(ttk.Frame):
    def __init__(self, root):
        super().__init__(root, padding=16)
        self.root = root
        self.document = empty_document()
        self.base = Path.cwd()
        self.current = None
        self.busy = False
        self.dirty = False
        self.cancel = threading.Event()
        self.events = queue.Queue()
        self.worker = None
        self.pack(fill='both', expand=True)
        root.title('Outlands Portfolio Builder')
        root.geometry('1120x820'); root.minsize(940, 700)
        ttk.Label(self, text='Portfolio & Case Study Builder', font=('Segoe UI', 19, 'bold')).pack(anchor='w')
        ttk.Label(self, text='Write your own project story. Keep claims and evidence distinct. Export PDF, HTML and a checked ZIP.').pack(anchor='w', pady=(3, 12))
        tools = ttk.Frame(self); tools.pack(fill='x')
        for label, command in [('New', self.new), ('Load fictional example', self.demo),
                               ('Open JSON...', self.open), ('Save input as new JSON...', self.save)]:
            ttk.Button(tools, text=label, command=command).pack(side='left', padx=(0, 7))
        self.book = ttk.Notebook(self); self.book.pack(fill='both', expand=True, pady=12)
        self.profile_tab = ttk.Frame(self.book, padding=12); self.book.add(self.profile_tab, text='Profile')
        self.project_tab = ttk.Frame(self.book, padding=12); self.book.add(self.project_tab, text='Projects')
        self.evidence_tab = ttk.Frame(self.book, padding=12); self.book.add(self.evidence_tab, text='Evidence')
        self.profile_fields = {}
        for row, (key, label, lines) in enumerate([('name', 'Name', 1), ('title', 'Professional title', 1),
                ('summary', 'Profile summary', 5), ('skills', 'Skills - one per line', 4), ('contact', 'Public contact text - one per line (optional)', 3)]):
            self.profile_fields[key] = self.field(self.profile_tab, row, label, lines)
        self.profile_tab.columnconfigure(1, weight=1)
        ttk.Label(self.profile_tab, text=core.FONT_NOTE, wraplength=900).grid(row=5, column=0, columnspan=2, sticky='w', pady=14)
        self.build_projects(); self.build_evidence()
        bottom = ttk.LabelFrame(self, text='Export a new bundle', padding=10); bottom.pack(fill='x')
        self.output = tk.StringVar(value='')
        ttk.Entry(bottom, textvariable=self.output).grid(row=0, column=0, sticky='ew')
        ttk.Button(bottom, text='Choose new folder...', command=self.choose_output).grid(row=0, column=1, padx=8)
        self.hash_files = tk.BooleanVar(value=False)
        ttk.Checkbutton(bottom, text='Hash selected evidence files (reads contents; never includes their contents)', variable=self.hash_files).grid(row=1, column=0, columnspan=2, sticky='w', pady=8)
        actions = ttk.Frame(bottom); actions.grid(row=0, column=2, rowspan=2)
        self.export_button = ttk.Button(actions, text='Export bundle', command=self.start_export); self.export_button.pack(side='left', padx=4)
        self.stop_button = ttk.Button(actions, text='Stop', command=self.request_stop, state='disabled'); self.stop_button.pack(side='left', padx=4)
        bottom.columnconfigure(0, weight=1)
        self.status = tk.StringVar(value='Start with your own profile or load the fictional example. Nothing is exported automatically.')
        ttk.Label(self, textvariable=self.status, wraplength=1040).pack(anchor='w', pady=(10, 0))
        ttk.Label(self, text='Exports contain your supplied text, URLs, evidence labels and optional hashes. Review before sharing. Source evidence files are not copied.', wraplength=1040).pack(anchor='w', pady=(7, 0))
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.bind('<KeyRelease>', lambda _e: setattr(self, 'dirty', True))
        self.poll_id = self.after(100, self.poll)

    @staticmethod
    def field(parent, row, label, lines):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky='nw', padx=(0, 12), pady=6)
        if lines == 1:
            widget = ttk.Entry(parent)
        else:
            widget = tk.Text(parent, height=lines, wrap='word', font=('Segoe UI', 10), undo=True)
        widget.grid(row=row, column=1, sticky='ew', pady=6)
        return widget

    @staticmethod
    def get(widget):
        return widget.get('1.0', 'end-1c') if isinstance(widget, tk.Text) else widget.get()

    @staticmethod
    def set(widget, value):
        if isinstance(widget, tk.Text): widget.delete('1.0', 'end'); widget.insert('1.0', value)
        else: widget.delete(0, 'end'); widget.insert(0, value)

    def build_projects(self):
        self.project_tab.columnconfigure(1, weight=1); self.project_tab.rowconfigure(0, weight=1)
        left = ttk.Frame(self.project_tab); left.grid(row=0, column=0, sticky='nsew', padx=(0, 15))
        self.projects = tk.Listbox(left, width=26, height=17, exportselection=False)
        self.projects.pack(fill='both', expand=True); self.projects.bind('<<ListboxSelect>>', self.select_project)
        buttons = ttk.Frame(left); buttons.pack(fill='x', pady=8)
        ttk.Button(buttons, text='Add', command=self.add_project).pack(side='left')
        ttk.Button(buttons, text='Remove', command=self.remove_project).pack(side='left', padx=5)
        pane = ttk.Frame(self.project_tab); pane.grid(row=0, column=1, sticky='nsew')
        canvas = tk.Canvas(pane, highlightthickness=0)
        scroll = ttk.Scrollbar(pane, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set); scroll.pack(side='right', fill='y'); canvas.pack(side='left', fill='both', expand=True)
        right = ttk.Frame(canvas); window = canvas.create_window((0, 0), window=right, anchor='nw')
        right.bind('<Configure>', lambda _e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda e: canvas.itemconfigure(window, width=e.width))
        right.columnconfigure(1, weight=1)
        self.project_fields = {}
        for row, (key, label, lines) in enumerate([('id', 'Stable project ID', 1), ('title', 'Project title', 1),
                ('role', 'Your role', 1), ('summary', 'Summary', 3), ('problem', 'Problem', 3), ('approach', 'Approach', 3),
                ('limitations', 'Limits / next steps', 3), ('outcomes', 'Outcomes - one per line', 5)]):
            self.project_fields[key] = self.field(right, row, label, lines)
        ttk.Label(right, text='Outcome format: reported | Statement | evidence-id,other-id\nStatuses: observed, reported, planned, unverified. Leave evidence IDs blank if none.', wraplength=700).grid(row=8, column=0, columnspan=2, sticky='w', pady=6)

    def build_evidence(self):
        self.evidence_tab.columnconfigure(1, weight=1)
        self.evidence_list = ttk.Treeview(self.evidence_tab, columns=('label', 'kind'), height=6, selectmode='browse')
        self.evidence_list.heading('#0', text='ID'); self.evidence_list.heading('label', text='Public label'); self.evidence_list.heading('kind', text='Kind')
        self.evidence_list.column('#0', width=180); self.evidence_list.column('label', width=500); self.evidence_list.column('kind', width=100)
        self.evidence_list.grid(row=0, column=0, columnspan=3, sticky='ew', pady=(0, 8)); self.evidence_list.bind('<<TreeviewSelect>>', self.select_evidence)
        self.evidence_fields = {}
        for row, (key, label, lines) in enumerate([('id', 'Evidence ID', 1), ('label', 'Public label', 1),
                ('kind', 'Kind: note, file or link', 1), ('source', 'Private file path / public HTTPS URL', 1), ('note', 'Public note', 4)], 1):
            self.evidence_fields[key] = self.field(self.evidence_tab, row, label, lines)
        ttk.Button(self.evidence_tab, text='Choose file...', command=self.choose_evidence).grid(row=4, column=2, padx=8)
        self.set(self.evidence_fields['kind'], 'note')
        bar = ttk.Frame(self.evidence_tab); bar.grid(row=6, column=0, columnspan=3, sticky='w', pady=10)
        ttk.Button(bar, text='Save evidence entry', command=self.save_evidence).pack(side='left')
        ttk.Button(bar, text='Remove selected', command=self.remove_evidence).pack(side='left', padx=8)
        ttk.Label(self.evidence_tab, text='Evidence edits must be saved with Save evidence entry. File paths stay in private input JSON; exports use labels and optional SHA-256 values. Links are never fetched.', wraplength=980).grid(row=7, column=0, columnspan=3, sticky='w')

    def notify_error(self, error):
        self.status.set(str(error) if isinstance(error, core.BuildError) else 'Operation failed. Check the selected paths and settings.')
        messagebox.showerror('Portfolio Builder', self.status.get(), parent=self.root)

    def flush_project(self):
        if self.current is None: return
        result = {key: self.get(widget) for key, widget in self.project_fields.items() if key != 'outcomes'}
        outcomes = []
        try:
            for parts in csv.reader(io.StringIO(self.get(self.project_fields['outcomes'])), delimiter='|', skipinitialspace=True, strict=True):
                if not parts or not any(x.strip() for x in parts): continue
                if len(parts) not in (2, 3): raise core.BuildError('outcomes: use status | statement | optional evidence IDs; quote a statement containing a pipe')
                outcomes.append({'status': parts[0].strip(), 'statement': parts[1].strip(),
                                 'evidence': [x.strip() for x in parts[2].split(',') if x.strip()] if len(parts) == 3 else []})
        except csv.Error:
            raise core.BuildError('outcomes: invalid pipe-separated CSV quoting') from None
        result['outcomes'] = outcomes
        self.document['projects'][self.current] = result

    def collect(self):
        self.flush_project()
        p = {key: self.get(widget) for key, widget in self.profile_fields.items()}
        for key in ('skills', 'contact'): p[key] = [line.strip() for line in p[key].splitlines() if line.strip()]
        self.document['profile'] = p
        return copy.deepcopy(self.document)

    def show_document(self, document, base):
        self.document = copy.deepcopy(document); self.base = Path(base); self.current = None
        for key, widget in self.profile_fields.items():
            value = self.document['profile'].get(key, '')
            self.set(widget, '\n'.join(value) if isinstance(value, list) else value)
        self.refresh_projects()
        self.refresh_evidence()
        for widget in self.project_fields.values(): self.set(widget, '')
        if self.document['projects']:
            self.projects.selection_set(0); self.load_project(0)
        self.status.set('Input loaded in memory. Review each tab; no files have been exported.')
        self.dirty = False

    def refresh_projects(self):
        self.projects.delete(0, 'end')
        for p in self.document['projects']: self.projects.insert('end', p.get('title') or p.get('id') or 'New project')

    def load_project(self, index):
        self.current = index
        project = self.document['projects'][index]
        for key, widget in self.project_fields.items():
            value = project.get(key, '')
            if key == 'outcomes':
                stream=io.StringIO(); writer=csv.writer(stream,delimiter='|',lineterminator='\n')
                for item in value: writer.writerow([item['status'],item['statement'],','.join(item.get('evidence',[]))])
                value=stream.getvalue().rstrip('\n')
            self.set(widget, value)

    def select_project(self, _event=None):
        if self.busy or not self.projects.curselection(): return
        index = self.projects.curselection()[0]
        if index == self.current: return
        try: self.flush_project(); self.load_project(index)
        except core.BuildError as error:
            self.projects.selection_clear(0, 'end')
            if self.current is not None: self.projects.selection_set(self.current)
            self.notify_error(error)

    def add_project(self):
        if self.busy: return
        try: self.flush_project()
        except core.BuildError as error: self.notify_error(error); return
        if len(self.document['projects']) >= 10: self.notify_error(core.BuildError('projects: at most 10')); return
        used = {p['id'] for p in self.document['projects']}; n = 1
        while f'project-{n}' in used: n += 1
        self.document['projects'].append({'id': f'project-{n}', 'title': 'New project', 'role': '', 'summary': '',
            'problem': '', 'approach': '', 'limitations': '', 'outcomes': [{'status': 'unverified', 'statement': 'Describe what remains to be checked.', 'evidence': []}]})
        self.refresh_projects(); self.projects.selection_set(len(self.document['projects']) - 1); self.load_project(len(self.document['projects']) - 1)
        self.dirty = True

    def remove_project(self):
        if self.busy or self.current is None: return
        del self.document['projects'][self.current]; self.current = None
        self.dirty = True
        self.refresh_projects()
        for widget in self.project_fields.values(): self.set(widget, '')
        if self.document['projects']: self.projects.selection_set(0); self.load_project(0)

    def refresh_evidence(self):
        for item in self.evidence_list.get_children(): self.evidence_list.delete(item)
        for item in self.document['evidence']: self.evidence_list.insert('', 'end', iid=item['id'], text=item['id'], values=(item['label'], item['kind']))

    def select_evidence(self, _event=None):
        if self.busy or not self.evidence_list.selection(): return
        selected = self.evidence_list.selection()[0]
        item = next(e for e in self.document['evidence'] if e['id'] == selected)
        for key, widget in self.evidence_fields.items(): self.set(widget, item.get(key, ''))

    def choose_evidence(self):
        if self.busy: return
        selected = filedialog.askopenfilename(parent=self.root, title='Choose one evidence file; its content will not be bundled')
        if selected: self.set(self.evidence_fields['source'], selected); self.set(self.evidence_fields['kind'], 'file')

    def save_evidence(self):
        if self.busy: return
        item = {key: self.get(widget).strip() for key, widget in self.evidence_fields.items()}
        try:
            core.identifier(item['id'], 'evidence.id')
            if not item['label'] or item['kind'] not in ('note', 'file', 'link'): raise core.BuildError('evidence: provide a label and note/file/link kind')
            if item['kind'] == 'note': item.pop('source')
            if item['kind'] == 'link': core.public_url(item['source'])
            prior = [e for e in self.document['evidence'] if e['id'] != item['id']]
            if len(prior) >= 20: raise core.BuildError('evidence: at most 20 entries')
            self.document['evidence'] = prior + [item]; self.refresh_evidence()
            self.dirty = True
            self.status.set('Evidence entry saved in memory. Use its ID in project outcomes.')
        except core.BuildError as error: self.notify_error(error)

    def remove_evidence(self):
        if self.busy or not self.evidence_list.selection(): return
        selected = self.evidence_list.selection()[0]
        self.document['evidence'] = [e for e in self.document['evidence'] if e['id'] != selected]; self.refresh_evidence()
        self.dirty = True
        self.status.set('Evidence entry removed from memory. Remove any project references to its ID before exporting.')

    def new(self):
        if not self.busy and self.allow_replace(): self.show_document(empty_document(), Path.cwd())
    def allow_replace(self):
        return not self.dirty or messagebox.askyesno('Unsaved input', 'Discard the current unsaved editor input? Save it as a new JSON first if you want to keep it.', parent=self.root)
    def demo(self):
        if self.busy or not self.allow_replace(): return
        try: document, base = core.read_input(Path(__file__).with_name('examples') / 'workshop.json'); self.show_document(document, base)
        except (core.BuildError, OSError) as error: self.notify_error(error)
    def open(self):
        if self.busy: return
        selected = filedialog.askopenfilename(parent=self.root, filetypes=[('Input JSON', '*.json')])
        if selected:
            try:
                document, base = core.read_input(selected)
                if self.allow_replace(): self.show_document(document, base)
            except (core.BuildError, OSError) as error: self.notify_error(error)
    def save(self):
        if self.busy: return
        try: document = core.validate(self.collect())
        except core.BuildError as error: self.notify_error(error); return
        selected = filedialog.asksaveasfilename(parent=self.root, title='Create a new private input JSON', defaultextension='.json', filetypes=[('Input JSON', '*.json')], confirmoverwrite=False)
        if selected:
            try:
                core.write_input(document, self.base, selected); self.dirty = False
                self.status.set('New private input JSON saved. Evidence file paths are private configuration, not public bundle data.')
            except (core.BuildError, OSError) as error: self.notify_error(error)
    def choose_output(self):
        if self.busy: return
        selected = filedialog.asksaveasfilename(parent=self.root, title='Choose a NEW bundle folder name', initialfile='portfolio-export', confirmoverwrite=False)
        if selected: self.output.set(selected)
    def start_export(self):
        if self.busy: return
        try:
            document = core.validate(self.collect())
            if not self.output.get().strip(): raise core.BuildError('output: choose a new bundle folder')
        except core.BuildError as error: self.notify_error(error); return
        self.busy = True; self.cancel.clear(); self.export_button.configure(state='disabled'); self.stop_button.configure(state='normal')
        output, base, hashes = self.output.get(), self.base, self.hash_files.get()
        events, cancel = self.events, self.cancel
        def work():
            try:
                result = core.export(document, base, output, hashes, cancel, lambda s: events.put(('status', s)))
                events.put(('done', result))
            except Exception as error:
                events.put(('error', str(error) if isinstance(error, core.BuildError) else 'Export failed. Check dependency installation, input and writable local storage.'))
        self.worker = threading.Thread(target=work, name='portfolio-export', daemon=True); self.worker.start()
    def request_stop(self):
        self.cancel.set(); self.status.set('Stop requested. Waiting for the current bounded operation; partial new output may remain.')
    def poll(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == 'status': self.status.set(value)
                else:
                    self.busy = False; self.export_button.configure(state='normal'); self.stop_button.configure(state='disabled')
                    self.status.set(f'Export complete: {value["files"]} files, checked ZIP. Review all output before sharing.' if kind == 'done' else str(value) + ' A partial new folder may remain.')
        except queue.Empty: pass
        self.poll_id = self.after(100, self.poll)
    def destroy(self):
        if getattr(self, 'poll_id', None):
            self.after_cancel(self.poll_id); self.poll_id = None
        super().destroy()
    def close(self):
        if self.busy: self.request_stop(); self.status.set('Wait for the export worker to return, then close this window.'); return
        if self.allow_replace(): self.root.destroy()

def main():
    root = tk.Tk(); App(root); root.mainloop()
if __name__ == '__main__': main()
