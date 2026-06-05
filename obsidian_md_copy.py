#!/usr/bin/env python3

# --- IRC shared bootstrap ---
# Rende disponibili i moduli in Python/shared/ senza dipendere da PYTHONPATH.
# Saltato se eseguito da bundle PyInstaller (sys.frozen=True): in quel caso
# i moduli sono gia' inclusi nel bundle.
import sys as _sys
from pathlib import Path as _Path
if not getattr(_sys, 'frozen', False):
    _shared = _Path.home() / "Library/CloudStorage/Dropbox/Documenti_IRC/Python/shared"
    if str(_shared) not in _sys.path:
        _sys.path.insert(0, str(_shared))
# --- end IRC shared bootstrap ---

VERSION = "1.1.0"
# obsidian_md_copy.py  v1.1.0
# Copia selettiva di file Markdown da una cartella sorgente (es. Dropbox)
# verso la vault Obsidian su iCloud Drive.

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
# ── path_widgets (modulo condiviso) ──────────────────────────────────────────
import sys as _sys
_sys.path.insert(0, str(__import__('pathlib').Path.home() /
    "Library/CloudStorage/Dropbox/Documenti_IRC/Python/shared"))
# ─────────────────────────────────────────────────────────────────────────────
from path_widgets import PathVar, PathEntry
import json
import hashlib
import shutil
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Icona SVG embedded (usata per generare .icns con AppBuilder_PyInstaller)
# ---------------------------------------------------------------------------
ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <rect width="512" height="512" rx="115" fill="#6B4FBB"/>
  <rect x="80" y="110" width="190" height="17" rx="4" fill="white" opacity="0.95"/>
  <rect x="80" y="142" width="150" height="11" rx="3" fill="white" opacity="0.55"/>
  <rect x="80" y="167" width="168" height="11" rx="3" fill="white" opacity="0.55"/>
  <rect x="80" y="192" width="130" height="11" rx="3" fill="white" opacity="0.55"/>
  <rect x="80" y="228" width="190" height="17" rx="4" fill="white" opacity="0.95"/>
  <rect x="80" y="260" width="155" height="11" rx="3" fill="white" opacity="0.55"/>
  <rect x="80" y="285" width="140" height="11" rx="3" fill="white" opacity="0.55"/>
  <rect x="80" y="310" width="170" height="11" rx="3" fill="white" opacity="0.55"/>
  <circle cx="370" cy="340" r="95" fill="#4CAF82"/>
  <rect x="345" y="285" width="18" height="72" rx="3" fill="white"/>
  <polygon points="370,265 410,305 386,305 386,357 354,357 354,305 330,305" fill="white"/>
</svg>"""

# ---------------------------------------------------------------------------
# Configurazione
# ---------------------------------------------------------------------------
APP_NAME    = "ObsidianMDCopy"
CONFIG_DIR  = Path.home() / "Library" / "CloudStorage" / "Dropbox" / "Documenti_IRC" / "Python" / "_config" / "ObsidianMD"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_SRC = str(Path.home() / "Library/CloudStorage/Dropbox/Documenti_IRC/Viaggi")
DEFAULT_DST = str(Path.home() / "Library/Mobile Documents/iCloud~md~obsidian/Documents/Viaggi")

# ---------------------------------------------------------------------------
# Utilità
# ---------------------------------------------------------------------------


def _path_to_cfg(p) -> str:
    """Salva il path relativo alla home, per portabilità tra Mac."""
    try:
        return str(Path(str(p)).expanduser().resolve().relative_to(Path.home()))
    except ValueError:
        return str(p)

def _path_from_cfg(s: str) -> str:
    """Ricostruisce il path assoluto: se relativo, prepende Path.home()."""
    if not s:
        return s
    p = Path(s)
    if p.is_absolute():
        # retrocompatibilità: path assoluto vecchio stile
        return str(p)
    return str(Path.home() / p)

def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            if "src" in cfg: cfg["src"] = _path_from_cfg(cfg["src"])
            if "dst" in cfg: cfg["dst"] = _path_from_cfg(cfg["dst"])
            return cfg
        except Exception:
            pass
    return {"src": DEFAULT_SRC, "dst": DEFAULT_DST, "flat": False}


def save_config(cfg: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    out = dict(cfg)
    if "src" in out: out["src"] = _path_to_cfg(out["src"])
    if "dst" in out: out["dst"] = _path_to_cfg(out["dst"])
    CONFIG_FILE.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")


def file_md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def files_identical(src: Path, dst: Path) -> bool:
    if not dst.exists():
        return False
    if src.stat().st_size != dst.stat().st_size:
        return False
    return file_md5(src) == file_md5(dst)


def find_md_files(root: Path) -> list[Path]:
    return sorted(root.rglob("*.md"))


def dst_path_for(fp: Path, src_root: Path, dst_root: Path, flat: bool) -> Path:
    if flat:
        return dst_root / fp.name
    return dst_root / fp.relative_to(src_root)


# ---------------------------------------------------------------------------
# Widget albero con checkbox grandi
# ---------------------------------------------------------------------------

class CheckboxTree(ttk.Frame):

    CHECK   = "☑"
    UNCHECK = "☐"
    PARTIAL = "▣"

    TAG_IDENTICAL = "identical"
    TAG_NEW       = "new"
    TAG_CHANGED   = "changed"
    TAG_FOLDER    = "folder"

    def __init__(self, master, on_selection_change=None, **kw):
        super().__init__(master, **kw)
        self._vars: dict[str, bool]       = {}
        self._item_paths: dict[str, Path] = {}
        self._on_selection_change = on_selection_change
        self._build()

    def _build(self):
        style = ttk.Style()
        # Righe alte per checkbox visibili, font normale per il testo
        style.configure("CheckTree.Treeview",
                        rowheight=28,
                        font=("SF Pro Text", 11))
        style.configure("CheckTree.Treeview.Heading",
                        font=("SF Pro Text", 11, "bold"))

        cols = ("stato", "modifica", "dimensione", "note")
        self.tv = ttk.Treeview(self, columns=cols, show="tree headings",
                               selectmode="none", style="CheckTree.Treeview")

        self.tv.heading("#0",         text="File / Cartella")
        self.tv.heading("stato",      text="")
        self.tv.heading("modifica",   text="Modificato")
        self.tv.heading("dimensione", text="Dim.")
        self.tv.heading("note",       text="Stato")

        self.tv.column("#0",          width=320, stretch=True)
        self.tv.column("stato",       width=40,  stretch=False, anchor="center")
        self.tv.column("modifica",    width=120, stretch=False, anchor="center")
        self.tv.column("dimensione",  width=72,  stretch=False, anchor="e")
        self.tv.column("note",        width=110, stretch=False, anchor="center")

        sb = ttk.Scrollbar(self, orient="vertical", command=self.tv.yview)
        self.tv.configure(yscrollcommand=sb.set)
        self.tv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self.tv.bind("<Button-1>", self._on_click)

        # Colori semantici
        self.tv.tag_configure(self.TAG_IDENTICAL, foreground="#999999")
        self.tv.tag_configure(self.TAG_NEW,       foreground="#1a7f2e")
        self.tv.tag_configure(self.TAG_CHANGED,   foreground="#c06000")
        self.tv.tag_configure(self.TAG_FOLDER,    foreground="#333333",
                              font=("SF Pro Text", 11, "bold"))

    # ------------------------------------------------------------------
    def populate(self, src_root: Path, dst_root: Path, flat: bool):
        self.tv.delete(*self.tv.get_children())
        self._vars.clear()
        self._item_paths.clear()

        md_files = find_md_files(src_root)
        if not md_files:
            self.tv.insert("", "end", text="  Nessun file .md trovato", values=("", "", "", ""))
            self._notify()
            return

        folder_iids: dict[Path, str] = {}

        def ensure_folder(folder: Path) -> str:
            if folder in folder_iids:
                return folder_iids[folder]
            if folder == src_root:
                iid = self.tv.insert("", "end",
                                     text=f"  📁  {folder.name}",
                                     values=("", "", "", ""),
                                     open=True, tags=(self.TAG_FOLDER,))
            else:
                parent_iid = ensure_folder(folder.parent)
                iid = self.tv.insert(parent_iid, "end",
                                     text=f"  📁  {folder.name}",
                                     values=("", "", "", ""),
                                     open=True, tags=(self.TAG_FOLDER,))
            folder_iids[folder] = iid
            return iid

        for fp in md_files:
            parent_iid = ensure_folder(fp.parent)
            dst_path   = dst_path_for(fp, src_root, dst_root, flat)
            stat       = fp.stat()
            size_str   = f"{stat.st_size / 1024:.1f} KB"
            modified   = datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%y %H:%M")

            if files_identical(fp, dst_path):
                note  = "identico"
                tag   = self.TAG_IDENTICAL
                check = False
            elif dst_path.exists():
                note  = "aggiornare"
                tag   = self.TAG_CHANGED
                check = True
            else:
                note  = "nuovo"
                tag   = self.TAG_NEW
                check = True

            sym = self.CHECK if check else self.UNCHECK
            iid = self.tv.insert(parent_iid, "end",
                                 text=f"     {fp.name}",
                                 values=(sym, modified, size_str, note),
                                 tags=(tag,))
            self._vars[iid]       = check
            self._item_paths[iid] = fp

        for fiid in folder_iids.values():
            self._update_folder_icon(fiid)

        self._notify()

    # ------------------------------------------------------------------
    def _get_file_children_recursive(self, iid) -> list[str]:
        result = []
        for child in self.tv.get_children(iid):
            if child in self._vars:
                result.append(child)
            else:
                result.extend(self._get_file_children_recursive(child))
        return result

    def _update_folder_icon(self, fiid):
        children = self._get_file_children_recursive(fiid)
        if not children:
            return
        checked = sum(1 for c in children if self._vars.get(c, False))
        if checked == 0:
            sym = self.UNCHECK
        elif checked == len(children):
            sym = self.CHECK
        else:
            sym = self.PARTIAL
        self.tv.set(fiid, "stato", sym)

    # ------------------------------------------------------------------
    def _on_click(self, event):
        region = self.tv.identify_region(event.x, event.y)
        iid    = self.tv.identify_row(event.y)
        if not iid:
            return

        if iid in self._vars:
            self._toggle_file(iid)
        elif region in ("tree", "cell"):
            children = self._get_file_children_recursive(iid)
            if not children:
                return
            current_all = all(self._vars.get(c, False) for c in children)
            for c in children:
                self._set_file(c, not current_all)
            self._update_folder_icon(iid)

        self._notify()

    def _toggle_file(self, iid):
        self._set_file(iid, not self._vars[iid])
        parent = self.tv.parent(iid)
        while parent:
            self._update_folder_icon(parent)
            parent = self.tv.parent(parent)

    def _set_file(self, iid, value: bool):
        self._vars[iid] = value
        self.tv.set(iid, "stato", self.CHECK if value else self.UNCHECK)

    def _notify(self):
        if self._on_selection_change:
            self._on_selection_change()

    # ------------------------------------------------------------------
    def get_selected_paths(self) -> list[Path]:
        return [self._item_paths[iid]
                for iid, checked in self._vars.items() if checked]

    def total_count(self) -> int:
        return len(self._vars)

    def selected_count(self) -> int:
        return sum(1 for v in self._vars.values() if v)

    def select_all(self):
        for iid in list(self._vars):
            self._set_file(iid, True)
        for iid in self.tv.get_children():
            self._update_folder_icon(iid)
        self._notify()

    def deselect_all(self):
        for iid in list(self._vars):
            self._set_file(iid, False)
        for iid in self.tv.get_children():
            self._update_folder_icon(iid)
        self._notify()


# ---------------------------------------------------------------------------
# Finestra principale
# ---------------------------------------------------------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Obsidian MD Copy")
        self.resizable(True, True)
        self.minsize(800, 540)
        self.cfg = load_config()
        self._build_ui()
        self.geometry("960x680")

    # ------------------------------------------------------------------
    def _build_ui(self):
        PAD = 12

        # ── Percorsi ────────────────────────────────────────────────────
        frm_paths = ttk.LabelFrame(self, text="Percorsi", padding=PAD)
        frm_paths.pack(fill="x", padx=PAD, pady=(PAD, 0))

        ttk.Label(frm_paths, text="Sorgente (Dropbox):").grid(
            row=0, column=0, sticky="w", pady=3)
        self.var_src = PathVar(value=self.cfg.get("src", DEFAULT_SRC))
        PathEntry(frm_paths, pathvar=self.var_src).grid(
            row=0, column=1, padx=6, sticky="ew", pady=3)
        ttk.Button(frm_paths, text="…", width=3,
                   command=self._browse_src).grid(row=0, column=2, pady=3)

        ttk.Label(frm_paths, text="Destinazione (Obsidian):").grid(
            row=1, column=0, sticky="w", pady=3)
        self.var_dst = PathVar(value=self.cfg.get("dst", DEFAULT_DST))
        PathEntry(frm_paths, pathvar=self.var_dst).grid(
            row=1, column=1, padx=6, sticky="ew", pady=3)
        ttk.Button(frm_paths, text="…", width=3,
                   command=self._browse_dst).grid(row=1, column=2, pady=3)

        frm_paths.columnconfigure(1, weight=1)

        # ── Opzione flat / sottocartelle ─────────────────────────────────
        frm_opt = ttk.Frame(frm_paths)
        frm_opt.grid(row=2, column=0, columnspan=3, sticky="w", pady=(8, 2))

        self.var_flat = tk.BooleanVar(value=self.cfg.get("flat", False))
        ttk.Checkbutton(
            frm_opt,
            text="Copia flat — tutti i file direttamente nella cartella radice (senza sottocartelle)",
            variable=self.var_flat,
            command=self._on_flat_change
        ).pack(side="left")

        ttk.Button(frm_paths, text="🔍  Scansiona", command=self._scan)\
            .grid(row=3, column=0, columnspan=3, pady=(10, 2), sticky="e")

        # ── Albero ──────────────────────────────────────────────────────
        frm_tree = ttk.LabelFrame(self, text="File Markdown trovati", padding=PAD)
        frm_tree.pack(fill="both", expand=True, padx=PAD, pady=(8, 0))

        self.tree = CheckboxTree(frm_tree,
                                  on_selection_change=self._update_count)
        self.tree.pack(fill="both", expand=True)

        # Legenda colori + selezione rapida
        frm_bottom = ttk.Frame(frm_tree)
        frm_bottom.pack(fill="x", pady=(6, 0))

        ttk.Button(frm_bottom, text="Seleziona tutto",
                   command=self.tree.select_all).pack(side="left", padx=2)
        ttk.Button(frm_bottom, text="Deseleziona tutto",
                   command=self.tree.deselect_all).pack(side="left", padx=2)

        # Legenda
        leg = ttk.Frame(frm_bottom)
        leg.pack(side="left", padx=20)
        ttk.Label(leg, text="● nuovo",      foreground="#1a7f2e", font=("SF Pro Text", 11)).pack(side="left", padx=4)
        ttk.Label(leg, text="● aggiornare", foreground="#c06000", font=("SF Pro Text", 11)).pack(side="left", padx=4)
        ttk.Label(leg, text="● identico",   foreground="#999999", font=("SF Pro Text", 11)).pack(side="left", padx=4)

        self.lbl_count = ttk.Label(frm_bottom, text="",
                                    font=("SF Pro Text", 11, "bold"))
        self.lbl_count.pack(side="right", padx=6)

        # ── Barra stato / pulsante copia ────────────────────────────────
        frm_btn = ttk.Frame(self)
        frm_btn.pack(fill="x", padx=PAD, pady=PAD)

        ttk.Button(frm_btn, text="Esci", command=self.destroy).pack(side="left")

        self.lbl_status = ttk.Label(frm_btn, text="Pronto.", anchor="w")
        self.lbl_status.pack(side="left", fill="x", expand=True, padx=(8, 0))

        self.btn_copy = ttk.Button(frm_btn, text="⬆  Copia selezionati",
                                    command=self._copy, state="disabled")
        self.btn_copy.pack(side="right", padx=(6, 0))

    # ------------------------------------------------------------------
    def _on_flat_change(self):
        if self.tree.total_count() > 0:
            self._scan()

    def _update_count(self):
        sel   = self.tree.selected_count()
        total = self.tree.total_count()
        if total == 0:
            self.lbl_count.config(text="")
            self.btn_copy.config(state="disabled")
        else:
            self.lbl_count.config(text=f"{sel} / {total} selezionati")
            self.btn_copy.config(state="normal" if sel > 0 else "disabled")

    # ------------------------------------------------------------------
    def _browse_src(self):
        d = filedialog.askdirectory(initialdir=self.var_src.get(),
                                    title="Cartella sorgente")
        if d:
            self.var_src.set(d)

    def _browse_dst(self):
        d = filedialog.askdirectory(initialdir=self.var_dst.get(),
                                    title="Cartella destinazione Obsidian")
        if d:
            self.var_dst.set(d)

    # ------------------------------------------------------------------
    def _scan(self):
        src = Path(self.var_src.get())
        dst = Path(self.var_dst.get())
        if not src.exists():
            messagebox.showerror("Errore", f"Cartella sorgente non trovata:\n{src}")
            return

        self._save_config()
        self.lbl_status.config(text="Scansione in corso…")
        self.update_idletasks()

        self.tree.populate(src, dst, self.var_flat.get())
        self._update_count()

        total = self.tree.total_count()
        sel   = self.tree.selected_count()
        mode  = "flat" if self.var_flat.get() else "con sottocartelle"
        self.lbl_status.config(
            text=f"Trovati {total} file .md ({mode}) — {sel} da copiare.")

    # ------------------------------------------------------------------
    def _copy(self):
        files = self.tree.get_selected_paths()
        if not files:
            messagebox.showinfo("Niente da fare", "Nessun file selezionato.")
            return

        src_root = Path(self.var_src.get())
        dst_root = Path(self.var_dst.get())
        flat     = self.var_flat.get()

        copied = skipped = errors = 0
        log_lines = []

        for fp in files:
            dst_path = dst_path_for(fp, src_root, dst_root, flat)

            if files_identical(fp, dst_path):
                skipped += 1
                log_lines.append(f"≡  {fp.name}  (identico, saltato)")
                continue

            try:
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(fp, dst_path)
                copied += 1
                log_lines.append(f"✓  {fp.name}")
            except Exception as e:
                errors += 1
                log_lines.append(f"✗  {fp.name}  → {e}")

        msg = (f"Copiati:            {copied}\n"
               f"Saltati (identici): {skipped}\n"
               f"Errori:             {errors}\n\n"
               + "\n".join(log_lines[:40])
               + ("\n…" if len(log_lines) > 40 else ""))

        if errors:
            messagebox.showwarning("Completato con errori", msg)
        else:
            messagebox.showinfo("Completato ✓", msg)

        self.lbl_status.config(
            text=f"Copia completata — {copied} copiati, {skipped} saltati, {errors} errori.")
        self._scan()

    # ------------------------------------------------------------------
    def _save_config(self):
        self.cfg["src"]  = self.var_src.get()
        self.cfg["dst"]  = self.var_dst.get()
        self.cfg["flat"] = self.var_flat.get()
        save_config(self.cfg)


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app = App()
    app.mainloop()
