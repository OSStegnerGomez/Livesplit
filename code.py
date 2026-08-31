from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
from datetime import datetime
from typing import Any, Iterable, List, Optional, Sequence, Tuple

import time
import tkinter as tk
from tkinter import ttk, filedialog
import keyboard
import json
from base64 import b64encode, b64decode

# =========================
# Utility functions
# =========================

def b64_lock(data,layers=1):
    for layer in range(layers):
        json_str = json.dumps(data)
        json_bytes = json_str.encode("utf-8")
        b64_bytes = b64encode(json_bytes)
        data = b64_bytes.decode("utf-8")
    return data

def b64_unlock(data,layers=1):
    for layer in range(layers):
        b64_bytes = data.encode("utf-8")
        json_bytes = b64decode(b64_bytes)
        json_str = json_bytes.decode("utf-8")
        data = json.loads(json_str)
    return data
        

def flatten_list(x: Iterable[Iterable[Any]]) -> List[Any]:
    return [n for ns in x for n in ns]


def formatA(x: float | None) -> str:
    """Format a float as 8-wide, 2 decimals, with sign handling."""
    if x is None: return "-----.--"
    if x < 0:
        return f"-{formatA(-x)}"
    return f"{x:08.2f}"


def formatB(x: float) -> str:
    """Format an int as 5-wide, with sign handling."""
    if x < 0:
        return f"-{formatB(-x)}"
    return f"{int(x)}".zfill(5)


def ordinal_num(n: int) -> str:
    """Convert an integer into its ordinal representation (e.g. 1 -> '1st')."""
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = ["th", "st", "nd", "rd", "th"][min(n % 10, 4)]
    return f"{n}{suffix}"


def el_by_ind(
    _list: Sequence[Any],
    ind: int,
    *args: str,
    default: Any = None,
) -> Any:
    """Safe index access with optional restriction for negative indices."""
    if ind < 0 and "restr_neg_ind" in args:
        return default
    try:
        return _list[ind]
    except IndexError:
        return default


# =========================
# Segment representation
# =========================

@dataclass
class RawSegment:
    """Internal representation used by segment_order, matching your original structure."""
    depth: int
    depth_index: int
    start: int
    end: int
    name: str

    @classmethod
    def from_triplet(cls, triplet: List[Any]) -> "RawSegment":
        (depth, depth_index), (start, end), name = triplet
        return cls(depth=depth, depth_index=depth_index, start=start, end=end, name=name)

    def to_triplet(self) -> List[Any]:
        return [[self.depth, self.depth_index], [self.start, self.end], self.name]


# =========================
# Segment ordering
# =========================

def segment_order(seg_names: Sequence[str]) -> List[List[Any]]:
    """
    Build the segment order list from segment names.

    This preserves your original logic:
    - Leading '-' increases depth.
    - '|' splits a segment into nested parts.
    - latest[] and val_cnt[] track indices per depth.
    """
    final: List[List[Any]] = []
    segs: List[List[Any]] = [
        [[0, 0], [0, i], seg_name] for i, seg_name in enumerate(seg_names)
    ]

    latest = [0 for _ in range(10)]
    val_cnt = [0 for _ in range(10)]

    while segs:
        i = 0
        while i < len(segs):
            seg = segs[i]
            depth_info, range_info, name = seg

            # Handle leading '-' → increase depth
            if name and name[0] == "-":
                depth_info[0] += 1
                seg[2] = name[1:]
                i += 1
                continue

            # Handle '|' splits
            vert_bar = name.find("|")
            if vert_bar != -1:
                seg_copy = deepcopy(seg)
                seg_copy[2] = name[:vert_bar]
                seg_copy[1][0] = latest[seg_copy[0][0]]
                seg_copy[0][1] = val_cnt[seg_copy[0][0]]
                val_cnt[seg_copy[0][0]] += 1
                final.append(seg_copy)

                latest[seg_copy[0][0]] = seg_copy[1][1] + 1
                seg[2] = name[vert_bar + 1 :]
                seg[0][0] += 1
                break
            else:
                # No more splits → finalize
                popp = segs.pop(i)
                popp[1][0] = popp[1][1]
                popp[0][1] = val_cnt[popp[0][0]]
                val_cnt[popp[0][0]] += 1
                final.append(popp)

    return final


# =========================
# Segment list info
# =========================

def get_seg_list_info(seg_list: List[List[Any]], **kwargs: Any) -> dict:
    """
    Compute chain and final_list for a given current segment index (curseg).

    This is a cleaned version of your original logic, preserving behavior.
    """
    curseg: Optional[int] = kwargs.get("curseg")
    info: dict = {"list": seg_list}

    if curseg is None:
        info["final_list"] = info["list"]
        return info

    max_end = max(e[1][1] for e in seg_list)
    if curseg >= max_end:
        curseg = max_end - 1

    curdepth = 0
    seg_chain: List[List[Any]] = []

    while True:
        bucket = [e for e in seg_list if e[0][0] == curdepth]
        espege = next((e for e in bucket if e[1][1] >= curseg), None)
        if not espege:
            break
        seg_chain.append(espege)
        curdepth += 1

    seg_blocks: List[List[List[Any]]] = [[e for e in seg_list if e[0][0] == 0]]
    for seg in seg_chain[:-1]:
        seg_blocks.append(
            [
                e
                for e in seg_list
                if e[0][0] == seg[0][0] + 1
                and e[1][0] >= seg[1][0]
                and e[1][0] <= seg[1][1]
            ]
        )

    final_block_stack: List[List[Any]] = []
    next_choosen_ind = 0

    for i, block in enumerate(seg_blocks):
        for seg in block:
            if seg[1][1] >= curseg:
                final_block_stack[next_choosen_ind:next_choosen_ind] = block
                next_choosen_ind = final_block_stack.index(seg_chain[i]) + 1
                break

    info["chain"] = [e[2] for e in seg_chain]
    info["final_list"] = final_block_stack
    info["curseg_cursor"] = final_block_stack.index(seg_chain[-1])
    return info


# =========================
# Segment list representation
# =========================

def seg_list_repr(_list: List[List[Any]], **kwargs: Any) -> List[dict]:
    """
    Build a representation of segments including:
    - text (left, middle, right)
    - time (PB segment time)
    - best (best segment time)
    - latest (latest segment time)
    - start (start time of segment in latest_splits)
    """
    _repr: List[dict] = []

    best_segs: List[List[float]] = kwargs.get("best_segs") or []
    split_times: List[float] = kwargs.get("compare_to") or []
    latest_splits: List[float] = kwargs.get("split_times") or []

    while len(best_segs) < 10:
        best_segs.append([])

    for seg in _list:
        seg_depth, seg_depth_ind = seg[0]
        seg_start_ind, seg_end_ind = seg[1]

        split_time = el_by_ind(split_times, seg_end_ind)
        latest_split = el_by_ind(latest_splits, seg_end_ind)

        left, middle, right = (None, None, None)
        left = seg[2]
        right = latest_split or split_time

        try:
            seg_time = (
                el_by_ind(split_times, seg_end_ind)
                - el_by_ind(split_times, seg_start_ind - 1, "restr_neg_ind", default=0)
            )
        except (ValueError, TypeError):
            seg_time = None

        best_seg = el_by_ind(el_by_ind(best_segs, seg_depth, default=[]), seg_depth_ind, None)

        try:
            latest_seg = latest_split - el_by_ind(
                latest_splits, seg_start_ind - 1, "restr_neg_ind", default=0
            )
        except Exception:
            latest_seg = None

        if not (latest_split is None or split_time is None):
            middle = latest_split - split_time

        _repr.append(
            {
                "text": (left, middle, right),
                "time": seg_time,
                "best": best_seg,
                "range": seg[1],
                "depth_ind": seg[0],
                "latest": latest_seg,
                "start": el_by_ind(
                    latest_splits, seg_start_ind - 1, "restr_neg_ind", default=0
                ),
            }
        )

    return _repr


# =========================
# Main App
# =========================

class App:
    TIMER_SPEED = 1
    SEG_ROW_COUNT = 11
    
    def __init__(self) -> None:
        # control
        self.curseg: int = 0
        self.seg_names: List[str] = ["NEU"]
        self.seg_order: List[List[Any]] = segment_order(self.seg_names)
        self.seg_count: int = len(self.seg_names)

        self.best_segs: List[List[float]] = []
        self.split_times: List[float] = []
        self.latest_splits: List[float] = []

        self.seg_info_cache: dict = get_seg_list_info(
            self.seg_order, curseg=self.curseg + 1
        )

        self.game_name: str = ""
        self.run_category: str = ""

        # timing
        self.main_timer: float = 0.0
        self.start: Optional[float] = None
        self.seg_timer: float = 0.0
        self.stop: Optional[float] = None

        # description

        self.description = ["Hier können sie eure Bescreibung geben."]

        # logs

        self.log_count: int = 0
        self.cur_log_page = None
        self.log_pages = []

        # tkinter
        self.root = tk.Tk()

        self.setup_window()
        self.create_labels()
        self.setup_labels()
        self.setup_hotkeys()
        self.update_loop()

    # -------------------------
    # Setup
    # -------------------------

    # -------------------------
    # - Window
    # -------------------------

    def setup_window(self) -> None:
        self.root.title("Custom Livesplit App v3.0.1 (Cleaned)")
        self.root.geometry("450x450")
        self.root.option_add("*Background", "black")
        self.root.option_add("*Foreground", "white")
        self.root.resizable(False, False)
        self.note_book = ttk.Notebook(self.root)
        self.note_book.pack(expand=True,fill="both")

        style = ttk.Style()
        style.configure("Custom.TFrame", background="black")

        self.main_timer_tab = ttk.Frame(self.note_book,style="Custom.TFrame")
        self.settings_tab = ttk.Frame(self.note_book,style="Custom.TFrame")
        self.description_tab = ttk.Frame(self.note_book,style="Custom.TFrame")
        self.logs_tab = ttk.Frame(self.note_book,style="Custom.TFrame")

        self.note_book.add(self.description_tab, text="Beschreibung")
        self.note_book.add(self.main_timer_tab, text="Haupt-Tab")
        self.note_book.add(self.settings_tab, text="Einstellungen")
        self.note_book.add(self.logs_tab, text="Protokolle")
        self.setup_description_tab()
        self.setup_logs_tab()


    def setup_description_tab(self) -> None:
        self.description_pagebook = ttk.Notebook(self.description_tab,style="Custom.TFrame")
        self.description_pagebook.pack(expand=True,fill="both")
        self.description_pages = [
            ttk.Frame(self.description_pagebook,style="Custom.TFrame") for e in self.description
        ]
        for i,(content,page) in enumerate(zip(self.description,self.description_pages)):
            self.description_pagebook.add(page,text=i+1)
            description_lbl = tk.Label(
                page,text=content,font=("Consolas", 8),wraplength=440
                )
            description_lbl.place(relx=0.5, y=30,anchor="n")

    def setup_logs_tab(self) -> None:
        self.logs_pagebook = ttk.Notebook(self.logs_tab,style="Custom.TFrame")
        self.logs_pagebook.pack(expand=True,fill="both")
        
    # -------------------------
    # - Hotkeys
    # -------------------------

    def setup_hotkeys(self) -> None:
            keyboard.add_hotkey("z", lambda: self.read_instruction("START"))
            keyboard.add_hotkey("x", lambda: self.read_instruction("HELLO!"))
            keyboard.add_hotkey("shift + q", lambda: self.read_instruction("PAUSE"))
            keyboard.add_hotkey("s", lambda: self.read_instruction("SPLIT"))
            keyboard.add_hotkey("shift + s", lambda: self.read_instruction("DESPLIT"))
            keyboard.add_hotkey("ctrl + shift + q", lambda: self.read_instruction("RESET"))

    # -------------------------
    # - Labels
    # -------------------------

    def create_labels(self) -> None:
        # settings
        self.export_btn = tk.Button(
            self.settings_tab,text="Exportieren",font=("Consolas", 10),command=self.export_data
            )
        self.import_btn = tk.Button(
            self.settings_tab,text="Importieren",font=("Consolas", 10),command=self.import_data
            )
        self.export_text = tk.Text(
            self.settings_tab,font=("Consolas", 10)
        )
        self.download_btn = tk.Button(
            self.settings_tab,text="Herunterladen",font=("Consolas", 10),command=self.download_data
            )
        self.import_file_btn = tk.Button(
            self.settings_tab,text="Datei importieren",font=("Consolas", 10),command=self.import_data_by_file
            )

        self.clear_logs_btn = tk.Button(
            self.settings_tab,text="Alle Protokolle löschen",font=("Consolas", 10),command=self.clear_logs
            )
        
        self.game_name_label = tk.Label(self.main_timer_tab, font=("Consolas", 12))
        self.run_category_label = tk.Label(self.main_timer_tab, font=("Consolas", 8))

        self.main_timer_label = tk.Label(self.main_timer_tab,font=("Consolas", 25))
        self.seg_timer_label = tk.Label(self.main_timer_tab,font=("Consolas", 15))
        self.best_seg_labels = [tk.Label(self.main_timer_tab,font=("Consolas", 8)) for _ in range(2)]
        self.pb_seg_labels = [tk.Label(self.main_timer_tab,font=("Consolas", 8)) for _ in range(2)]
        self.bpt_label = tk.Label(self.main_timer_tab,font=("Consolas", 8))

        self.seg_backframes = [tk.Frame(self.main_timer_tab) for _ in range(11)]
        self.left_segment_labels = [tk.Label(self.main_timer_tab,font=("Consolas", 10)) for _ in range(App.SEG_ROW_COUNT)]
        self.middle_segment_labels = [tk.Label(self.main_timer_tab,font=("Consolas", 10)) for _ in range(App.SEG_ROW_COUNT)]
        self.right_segment_labels = [tk.Label(self.main_timer_tab,font=("Consolas", 10)) for _ in range(App.SEG_ROW_COUNT)]



    def setup_labels(self) -> None:

        # settings
        #self.export_btn.place(relx=0.35,y=20,anchor="n")
        #self.import_btn.place(relx=0.65,y=20,anchor="n")
        self.download_btn.place(relx=0.35,y=20,anchor="n")
        self.import_file_btn.place(relx=0.65,y=20,anchor="n")
        
        self.clear_logs_btn.place(relx=0.5,y=60,anchor="center")
        #self.export_text.place(relx=0,rely=0.3,width=400,height=200)
        
        # timers
        self.main_timer_label.place(relx=0.5, rely=0.82, anchor="center")
        self.seg_timer_label.place(relx=0.5, rely=0.88, anchor="center")
        #self.bpt_label.place(relx=0.5, rely=0.92, anchor="center")

        for i, label in enumerate(self.best_seg_labels):
            label.place(relx=0, rely=0.76 + 0.08 * i)
        for i, label in enumerate(self.pb_seg_labels):
            label.place(relx=0, rely=0.8 + 0.08 * i)

        # segments
        for i, frame in enumerate(self.seg_backframes):
            frame.place(relwidth=1, height=21, y=i * 21 + 80)
        for i, label in enumerate(self.left_segment_labels):
            label.place(relx=0, y=i * 21 + 90, anchor="w")
        for i, label in enumerate(self.middle_segment_labels):
            label.place(relx=0.88, y=i * 21 + 90, anchor="e")
        for i, label in enumerate(self.right_segment_labels):
            label.place(relx=1, y=i * 21 + 90, anchor="e")

        self.game_name_label.place(relx=0.5, y=20, anchor="center")
        self.run_category_label.place(relx=0.5, y=40, anchor="center")

    # -------------------------
    # Commands
    # -------------------------

    def download_data(self):
        app_data = b64_lock(self.get_data())
        file_path = filedialog.asksaveasfilename(
        defaultextension=".txt",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        title="App-Daten herunterladen"
        )
    
        # 3. If the user didn't cancel, write the data locally
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write(app_data)
                self.log("Datei erfolgreich heruntergeladen!", type="INFO")
            except Exception as e:
                self.log(f"Der Versuch, eine Datei herunterzuladen, ist aufgrund des folgenden Fehlers fehlgeschlagen: {e}", type="ERROR"  )

    def import_data_by_file(self):
        # 1. Open the file selection dialog box
        file_path = filedialog.askopenfilename(
        defaultextension=".txt",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        title="App-Daten öffnen"
        )
    
        # 2. If the user selects a file, read it
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    file_contents = file.read()
            
            # 3. Clear existing text and insert the new data into the app
                self.import_data(file_contents)
            
                self.log("Datei erfolgreich importiert!",type="INFO")
            except Exception as e:
                self.log(f"Datei konnte nicht gelesen werden: {e}",type="ERROR")

    def get_data(self):
        return {
            "Stoppuhr": self.main_timer,
            "Zwischenzeiten": self.split_times,
            "Aktuelle Zwischenzeiten": self.latest_splits,
            "Beste Segmente": self.best_segs,
            "Spielname": self.game_name,
            "Durchlaufkategorie": self.run_category,
            "Segmentnamen": self.seg_names,
            "Beschreibung": self.description,
            }

    def export_data(self):
        data = self.get_data()
        b64_string = b64_lock(data)
        self.export_text.delete("1.0", tk.END)
        self.export_text.insert("1.0", b64_string)

    def import_data(self,data=None):
        try:
            b64_str = data or self.export_text.get("1.0", "end-1c")
            kwargs = b64_unlock(b64_str)
            # control
            self.seg_names: List[str] = list(kwargs.get("Segmentnamen"))
            self.seg_order: List[List[Any]] = segment_order(self.seg_names)
            self.seg_count: int = len(self.seg_names)

            self.best_segs: List[List[float]] = kwargs.get("Beste Segmente") or []
            self.split_times: List[float] = kwargs.get("Zwischenzeiten") or []
            self.latest_splits: List[float] = kwargs.get("Aktuelle Zwischenzeiten") or []

            self.curseg: int = len(self.latest_splits)

            self.seg_info_cache: dict = get_seg_list_info(
                self.seg_order, curseg=self.curseg + 1
            )

            self.game_name: str = kwargs.get("Spielname") or ""
            self.run_category: str = kwargs.get("Durchlaufkategorie") or ""

            # timing
            self.main_timer: float = kwargs.get("Stoppuhr") or 0.0
            self.start: Optional[float] = None
            self.seg_timer: float = 0.0
            self.stop: Optional[float] = None

            # description

            self.description = kwargs.get("Beschreibung") or ["Hier können sie eure bescreibung eingeben."]

            if type(self.description) is not list:
                self.description = [f"Der Datentyp aus Ihrer Beschreibung ist ungültig.\n -> Erwartet: „{list}“, erhalten: „{type(self.description)}“"]

            self.description_pagebook.destroy()
            self.setup_description_tab()
            self.log("Erfolgreich importiert!",type="INFO")

            self.game_name_label.configure(text=self.game_name)
            self.run_category_label.configure(text=self.run_category)
        except Exception as e:
            self.log("Beim Importieren ist ein Fehler aufgetreten.",type="ERROR")

    def log(self,message,**kwargs):
        print(message)
        _type = kwargs.get("type")
        match _type:
            case "FATAL": fg = "red"
            case "ERROR": fg = "pink"
            case "WARN": fg = "yellow"
            case "INFO": fg = "lime"
            case "DEBUG": fg = "blue"
            case "TRACE": fg = "cyan"
            case _: fg = "white"
        wiga = self.log_count % 12
        if wiga == 0:
            self.cur_log_page = ttk.Frame(self.logs_pagebook,style="Custom.TFrame")
            self.log_pages.append(self.cur_log_page)
            self.logs_pagebook.add(self.cur_log_page,text=len(self.log_pages))

        page = self.cur_log_page
        logs_lbl = tk.Label(
            page,text=f"[{datetime.now()}]\n{message}",font=("Consolas", 7),wraplength=440,fg=fg
            )
        logs_lbl.place(relx=0.5, y=30+30*wiga,anchor="n")
        self.log_count+=1
        
    def clear_logs(self):
        self.logs_pagebook.destroy()
        self.log_count=0
        self.cur_log_page = None
        self.log_pages = []
        self.setup_logs_tab()
        

    def read_instruction(self, cmd: str) -> None:
        cur_tab = self.note_book.index("current")
        if cur_tab != 1: return False
        match cmd:
            case "START":
                self._start_main_timer()
            case "PAUSE":
                self._pause_main_timer()
            case "RESET":
                self._reset_run()
            case "SPLIT":
                self._split()
            case "DESPLIT":
                self._desplit()

    # -------------------------
    # Timer control
    # -------------------------

    def main_timer_running(self) -> bool:
        return self.start is not None and self.stop is None

    def _start_main_timer(self) -> None:
        if not self.main_timer_running() and len(self.latest_splits) != self.seg_count:
            self.log(f"Haupttimer gestartet.",type="TRACE")
            self.stop = None
            self.start = time.time() - self.main_timer/App.TIMER_SPEED
            self.bpt_label.place(relx=0.5, rely=0.92, anchor="center")
            self.bpt_label.configure(text=f"Bestmögliche Zeit: {formatA(self.get_bpt())}")


    def _pause_main_timer(self) -> None:
        if self.main_timer_running():
            self.stop = time.time()
            if len(self.latest_splits) == self.seg_count:
                self.log(
                    f"🏁 Durchlauf bei {formatA(self.main_timer)} beendet.",type="TRACE"
                )
            else:
                self.log(
                    f"Haupttimer {formatA(self.main_timer)} angehalten.",type="TRACE"
                )
            self.bpt_label.place_forget()


    def _reset_run(self) -> None:
        self.log(f"Durchlauf zurückgesetzt",type="TRACE")
        self.start = None
        self.stop = None
        self.main_timer = 0.0
        self.latest_splits = []
        self.seg_info_cache = get_seg_list_info(self.seg_order, curseg=len(self.latest_splits))
        self.bpt_label.configure(text="")


    def _split(self) -> bool:
        if not self.main_timer_running():
            return False
        if len(self.latest_splits)+1 == self.seg_count:
            self._pause_main_timer()
            self.log(
                f"Bei {formatA(self.main_timer)} den Durchlauf beendet!",type="TRACE"
            )

        else:
            self.log(
                f"Bei {formatA(self.main_timer)} in das {len(self.latest_splits) + 1}. Gesamtsegment aufgeteilt.",type="TRACE"
            )

        self.latest_splits.append(self.main_timer)

        seg_repr = seg_list_repr(
        self.seg_info_cache["final_list"],
        compare_to=self.split_times,
        split_times=self.latest_splits,
        best_segs=self.best_segs,
        )

        seg_cursors = [
                next(
                    (e for e in seg_repr if e["range"][1] == self.curseg and e["depth_ind"][0] == i),
                    None,
                )
                for i in range(len(self.best_seg_labels))
            ]
        for seg in [e for e in seg_cursors if e is not None]:
            d = seg["depth_ind"]
            if seg["best"] is None or (seg["latest"] is not None and seg["latest"] < seg["best"]):
                self.log(
                 f"Neue Bestzeit auf dem {d[1]+1}. Segment v. Tiefe {d[0]} mit einer Zeit von {seg['latest']:08.2f} erzielt.",type="INFO"
                )
        self.bpt_label.configure(text=f"Bestmögliche Zeit: {formatA(self.get_bpt())}")
        self.seg_info_cache = get_seg_list_info(self.seg_order, curseg=len(self.latest_splits))
        return True

    def _desplit(self) -> bool:
        if not self.latest_splits:
            return False

        if self.main_timer_running():
            self.log(
                f"Zurück in den {len(self.latest_splits)}. Gesamtsegment wiedervereinigt.",type="TRACE"
            )
            self.latest_splits.pop()
            self.seg_info_cache = get_seg_list_info(self.seg_order, curseg=len(self.latest_splits))
        elif len(self.latest_splits) == self.seg_count:
            self.log(
                f"Zurück in den {len(self.latest_splits)}. Gesamtsegment wiedervereinigt.",type="TRACE"
            )
            self.latest_splits.pop()
            self._start_main_timer()
        self.bpt_label.configure(text=f"Bestmögliche Zeit: {formatA(self.get_bpt())}")
        return True

    # -------------------------
    # Get Best Possible Time
    # -------------------------

    def get_bpt(self):
        seg_order = self.seg_order
        best_segs = self.best_segs
        latest = self.latest_splits
        split_times = self.split_times

        _repr = seg_list_repr(
                seg_order
                ,best_segs=best_segs
                ,split_times=latest
                ,compare_to=split_times
                )

        filtered = [e for e in _repr if e["range"][0]== e["range"][1]]
        best_seg_times = [e["best"] for e in filtered]

        curseg = len(latest)
        try:
            seg_a = [e for e in _repr if e["range"][0] == e["range"][1] and e["range"][1]==curseg][0]["start"]
            bpt = sum(best_seg_times[curseg:])+seg_a
        except:
            return None
        return bpt
        
        

    # -------------------------
    # Update loop
    # -------------------------
        

    def update_loop(self) -> None:
        if self.main_timer_running():
            self.curseg = len(self.latest_splits)
            
        now = time.time()
        self.main_timer = App.TIMER_SPEED*((self.stop or now) - self.start) if self.start else self.main_timer
        self.seg_timer = self.main_timer - (self.latest_splits[-1] if self.latest_splits else 0.0)

        self.update_labels()
        self.root.after(10, self.update_loop)

    # -------------------------
    # Label updates
    # -------------------------



    def update_labels(self) -> None:
        right_fg = "white"
        curseg = self.curseg
        split_times = self.split_times

        seg_info = self.seg_info_cache
        seg_count = self.seg_count
        final_list = seg_info["final_list"]

        seg_repr = seg_list_repr(
            final_list,
            compare_to=split_times,
            split_times=self.latest_splits,
            best_segs=self.best_segs,
        )

        # main timer color logic
        try:
            main_slower_than_pb = self.seg_timer > (
                el_by_ind(split_times, curseg)
                - el_by_ind(split_times, curseg - 1, "restr_neg_ind", default=0)
            )
        except Exception:
            main_slower_than_pb = None

        if self.main_timer_running():
            if curseg < len(split_times) and split_times[curseg] and split_times[curseg] < self.main_timer:
                right_fg = "red" if main_slower_than_pb else "#FF8080"
            else:
                right_fg = "#80FF80" if main_slower_than_pb else "green"

        if len(self.latest_splits) == self.seg_count:
            right_fg = "red" if split_times and self.main_timer > split_times[-1] else "blue"

        self.main_timer_label.configure(text=formatA(self.main_timer), fg=right_fg)
        self.seg_timer_label.configure(text=formatA(self.seg_timer))

        # best / pb labels
        curseg_cursors = [
            next(
                (e for e in seg_repr if e["range"][1] >= self.curseg and e["depth_ind"][0] == i),
                None,
            )
            for i in range(len(self.best_seg_labels))
        ]

        for i, (cursor, best_l, pb_l) in enumerate(
            zip(curseg_cursors, self.best_seg_labels, self.pb_seg_labels)
        ):
                best_text = cursor.get("best") if cursor else None
                time_text = cursor.get("time") if cursor else None

                best_str = "-----.--" if best_text is None else formatA(best_text)
                time_str = "-----.--" if time_text is None else formatA(time_text)

                if not self.main_timer_running():
                    best_str = time_str = ""
                else:
                    best_str = f"BEST [↧{i}]: {best_str}"
                    time_str = f"ZEIT [↧{i}]: {time_str}"

                best_l.configure(text=best_str)
                pb_l.configure(text=time_str)

        # segment rows
        for i, (left, middle, right, bgframe) in enumerate(
            zip(
                self.left_segment_labels,
                self.middle_segment_labels,
                self.right_segment_labels,
                self.seg_backframes,
            )
        ):
            try:
                seg_r = seg_repr[i]
                seg_i = final_list[i]
            except IndexError:
                left.configure(text="")
                middle.configure(text="")
                right.configure(text="")
                continue

            bg = "#202020" if i % 2 else "#000000"
            if (
                self.curseg in range(seg_i[1][0], seg_i[1][1] + 1)
                and self.start is not None
                and len(self.latest_splits) != self.seg_count
            ):
                bg = "#000080" if seg_i[0][0] % 2 else "#000060"

            bgframe.configure(bg=bg)
            left.configure(bg=bg)
            middle.configure(bg=bg)
            right.configure(bg=bg)

            left_text, mid_timer, right_time = seg_r["text"]
            left.configure(text=f"{' ' * seg_r['depth_ind'][0]}{left_text}")

            seg_in_cursors = seg_r in curseg_cursors

            if mid_timer is None:
                if not seg_in_cursors or not seg_r.get("time"):
                    mid_text = ""
                else:
                    if (
                        seg_r["depth_ind"][0] + 1 == len(curseg_cursors)
                        and (
                            (seg_r.get("time") and seg_r["text"][2] and self.main_timer > seg_r["text"][2])
                            or (seg_r.get("best") and self.main_timer - seg_r["start"] > seg_r["best"])
                        )
                    ):
                        mid_text = f"{(self.main_timer - seg_r['text'][2]):+.1f}"
                    elif seg_in_cursors and seg_r != curseg_cursors[-1]:
                        mid_text = formatA(self.main_timer - seg_r["start"])
                    else: mid_text = ""
            else:
                mid_text = f"{mid_timer:+.1f}"

            try:
                if (
                    len(self.latest_splits) != seg_count
                    and seg_in_cursors
                    and seg_r["depth_ind"][0] + 1 != len(curseg_cursors)
                ):
                    if seg_r.get("time") and (self.main_timer - seg_r["start"]) < seg_r["time"]:
                        right_text = formatB(seg_r["time"])
                    else:
                        right_text = f"{(self.main_timer - seg_r['start'] - seg_r['time']):+.1f}"
                else:
                    right_text = formatB(right_time)
            except Exception:
                right_text = "-----"

            slower_than_pb = (
                seg_r["latest"] and seg_r["time"] and (seg_r["latest"] > seg_r["time"])
            )
            timer_fg = "white"
            if mid_timer is not None:
                timer_fg = (
                "gold"
                if (seg_r.get("best") and seg_r["latest"] < seg_r["best"])
                else ("#80FF80" if slower_than_pb else "green")
                if mid_timer < 0
                else ("red" if slower_than_pb else "#FF8080")
                )
            mid_fg = not (seg_in_cursors and seg_r != curseg_cursors[-1])
            if len(self.latest_splits) == seg_count:
                start = seg_r["start"]
                super_seg_timer = (
                    None if not seg_r["time"] else self.main_timer - start - seg_r["time"]
                )

                if mid_fg:
                    mid_text = "" if not mid_timer else f"{mid_timer:+.1f}"
                    right_text = formatB(right_time or 0)
                else:
                    mid_text = formatA(self.main_timer - start)
                    right_text = (
                        "-----" if not super_seg_timer else f"{super_seg_timer:+.1f}"
                    )
                    if seg_r.get("time"):
                        timer_fg = (
                            "gold"
                            if (seg_r.get("best") and self.main_timer - start < seg_r["best"])
                            else "green"
                            if super_seg_timer < 0
                            else "red"
                        )

            middle.configure(text=mid_text, fg="white" if not mid_fg else timer_fg)
            right.configure(text=right_text, fg="white" if mid_fg else timer_fg)

    # -------------------------
    # Run
    # -------------------------

    def run(self) -> None:
        self.root.mainloop()


# =========================
# App startup
# =========================

if __name__ == "__main__":
    app = App()
    app.run()


"""

eyJTdG9wcHVociI6IDAuMCwgIlp3aXNjaGVuemVpdGVuIjogWzM5LjEyLCA1OS4yOSwgMTAzLjgxLCAxMzEuOTcsIDE5Ni41NSwgMjgzLjc5LCAzMDUuODMsIDQxNy40LCA0NDUuNzUsIDU3NS42MywgNjUyLjM2LCA2OTAuNywgNzU1LjkxLCA3NzIuMTgsIDkwMy43NCwgOTY4LjIzLCAxMDA3LjgxLCAxMTMwLjEyLCAxMTgyLjg3LCAxMjM1LjMxLCAxMzE3Ljg5LCAxMzgwLjAzLCAxNDQ4Ljk3LCAxNDg5LjAxLCAxNTgzLjI5XSwgIkFrdHVlbGxlIFp3aXNjaGVuemVpdGVuIjogW10sICJCZXN0ZSBTZWdtZW50ZSI6IFtbMTkyLjYzNjYxMTcwMDA1Nzk4LCAzNTkuNjYsIDMyOC4xMSwgMjA0LCAxODcuMDksIDI2NS4yNl0sWzM3LjAyMzc4MDM0NTkxNjc1LCAxOC42LCA0MywgMjYsIDYxLjY5MDA3NzA2NjQyMTUxLCAzNy4wMjM3ODAzNDU5MTY3NSwgMTguOSwgOTQuOSwgMjguMjUsIDExNy41NiwgNzUuMTA1Njc4NTU4MzQ5NjEsIDM4LjM0LCA2My4wNzQxODI5ODcyMTMxMzUsIDE1LCAxMzEuNTYsIDYwLjMzLCAzMy41LCAxMDYuNzE4OTA1NDQ4OTEzNTcsIDUyLjc1LCA0OS4wOCwgODIuNTgsIDYyLjE0LCA2NC4zLCAzOS40OSwgODBdLCBbXSwgW10sIFtdLCBbXSwgW10sIFtdLCBbXSwgW11dLCAiU3BpZWxuYW1lIjogIlNvbmljIFRoZSBIZWRnZWhvZyBHZW5lc2lzIChHQkEgLSBVU0EpIiwgIkR1cmNobGF1ZmthdGVnb3JpZSI6ICJbVGFnIDAwMTM5XSBBbGxlIFNtYXJhZ2RlIGltIEp1YmlsXHUwMGU0dW1zbW9kdXMiLCAiU2VnbWVudG5hbWVuIjogWyItQWt0IDE6IFdhcyBmXHUwMGZjciBlaW4gc2Nod2VyZXIgQW5mYW5nISIsICItU3BlemlhbCAxOiBFcyBnZWh0IHNjaG5lbGwgd2llZGVyIHdlZyIsICItQWt0IDI6IFdpbGwgZGVuIE1vdG9idWcgbmljaHQgdFx1MDBmNnRlbi4iLCAiLVNwZXppYWwgMjogRGllc2VzIFRpbWluZy4uLiIsICJcdTI2NDBcdWQ4M2NcdWRmYzAgMDAuMDggKlJFU0VULSpUdXJuaGFsbGUgW05vcm1hbF18QWt0IDM6IEJpdHRlIGtlaW5lIFRyZWZmZXIgdmVyZmVobGVuISIsICItQWt0IDE6IERJRSBaWUtMRU4hIiwgIi1TcGV6aWFsIDM6IFNQUklORyEiLCAiLUFrdCAyOiBCaXR0ZSBuaWNodCBnZXRyb2ZmZW4gd2VyZGVuISIsICItU3BlemlhbCA0OiBWZXJtYXNzZWwgZGFzIG5pY2h0LiIsICJcdTI2NDJcdWQ4M2NcdWRmNzMgMDAuMjUgSGF1cHRrXHUwMGZjY2hlIGRlciBTY2h1bGV8QWt0IDM6IEdlZlx1MDBlNGhybGljaGVzIEVuZGUgZWluZXIgWm9uZSIsICItQWt0IDE6IE5PQ0ggRUlOIFpZS0xVUyEiLCAiLVNwZXppYWwgNTogTUVJTkUgR1JcdTAwZDZTU1RFIFNDSFdcdTAwYzRDSEUgRE9SVCEiLCAiLUFrdCAyOiBFVFdBUyBIRUlLTElHISIsICItU3BlemlhbCA2OiBTUFJJTkchISIsICJcdTI2NDBcdWQ4M2NcdWRmZjAgMDAuMDggVHVybmhhbGxlIFtBa3Q9SFx1MDBmY3BmYnVyZ118QWt0IDM6IEhFSUtMSUcgQU0gQU5GQU5HISIsICItQWt0L1dhc2NoYmVja2VuIDE6IFdhc3NlcnBoeXNpayEiLCAiLUFrdC9XYXNjaGJlY2tlbiAyOiBOXHUwMGZjdHpsaWNoZXIgU3BydW5nZmVkZXIhIiwgIlx1MjY0Mlx1ZDgzZFx1ZGViZiAwMC4xMSBUdXJuaGFsbGUtVW1rbGVpZGVyYXVtfEFrdC9XYXNjaGJlY2tlbiAzOiBQQVJLT1VSWkVJVCEiLCAiLUFrdCAxOiBTaWUgc2NoYXVlbiBkYSBlaW4gZ3V0ZW4gRmlsbSIsICItQWt0IDI6IFNpZSBzY2hhdWVuIHNpY2ggZ2VyYWRlIFx1MjAxZUdvbGRlblx1MjAxYyBhbi4iLCAiXHUyNjQyXHVkODNjXHVkZmFjIDEwLjA1IEd5bW5hc3Rpa3JhdW0gW0tpbm9yYXVtXXxBa3QgMzogRGllc2VyIEZpbG06IEtQb3AgRGVtb24gSHVudGVycyIsICItXHVkODNkXHVkY2NkIEFrdCAxIFtSYXVtbWl0dGVdOiBEYSB3aXJkIGF1Y2ggRmlsbSBnZXNjaGF1dCEiLCAiLVx1ZDgzY1x1ZGY3MyBBa3QgMiBbS29jaG5pc2NoZShcdTIxOTMpXTogRGEgd2lyZCBnZWtvY2h0ISIsICItXHVkODNkXHVkZWIwIEFrdCAzIFtXYXNjaGJlY2tlbl06IFNvIGh5Z2llbmlzY2ggc2NobGF1ISIsICJcdTI2NDBcdWQ4M2NcdWRmOTIgMTAuMjggS2xhc3NlbnJhdW0gW1NlaHVzYXNjaHVsZV18XHVkODNjXHVkZjdkIEJPU1MgW0tvY2huaXNjaGUoXHUyMTkxKV06IFdJRURFUiBIRUlLTElHISJdLCAiQmVzY2hyZWlidW5nIjogWyJcbk1laW5lIEJlc2NocmVpYnVuZyBkZXMgRHVyY2hsYXVmc1xuXG5cblNwaWVsdmVyc2lvbjogU2NobGVjaHRlc3RlIG9mZml6aWVsbGUgUG9ydGllcnVuZyBkZXMgU3BpZWxzXG4tPiBTaWUgaGFiZW4gZXJ3YXJ0ZXQsIGRhc3MgZGllc2UgU3BpZWxwb3J0aWVydW5nIGd1dCB3aXJkLlxuLT4gRWluZSBLYXRhc3Ryb3BoZSwgbWl0IGRlciBzaWUgbmljaHQgZ2VyZWNobmV0IGhhdHRlbi5cbi0+IERpZXNlIFBvcnRpZXJ1bmcgYmFzaWVydCBzaWNoIGF1ZiBlaW5lIGFuZGVyZSBQb3J0aWVydW5nLlxuLT4gRGFzIGVpZ2VudGxpY2hlIFNwaWVsIGhhdCBuaXggbWl0IEhvcnJvciB6dSB0dW4uXG5NZXRhc2NvcmU6IDMzLzEwMFxuQW56YWhsIGRlciBab25lbjogNiArIDEgPSA3XG5BbnphaGwgZGVyIHZvbGxzdFx1MDBlNG5kaWdlbiBSXHUwMGU0dW1lOiA1XG5SYXVtbnVtbWVybiwgR2VzY2hsZWNodCB1bmQgTmFtZW4gZGllc2VyIFJcdTAwZTR1bWU6XG5cdTI1Y2YgMDAuMDggVHVybmhhbGxlIFt3ZWlibGljaF1cblx1MjVjZiAwMC4yNSBIYXVwdGtcdTAwZmNjaGUgW21cdTAwZTRubmxpY2hdXG5cdTI1Y2YgMDAuMTEgVHVybmhhbGxlLVVta2xlaWRlcmF1bSBbbVx1MDBlNG5ubGljaF1cblx1MjVjZiAxMC4wNSBHeW1uYXN0aWtyYXVtIFttXHUwMGU0bm5saWNoXVxuXHUyNWNmIDEwLjI4IEtsYXNzZW5yYXVtIFt3ZWlibGljaF1cblxuU3BpZWxyZWloZW5mb2xnZSBkZXIgYW5nZWdlYmVuZW4gUlx1MDBlNHVtZTpcblx1MjVjZiBUdXJuaGFsbGUgKE5vcm1hbCkgLT4gSGF1cHRrXHUwMGZjY2hlIC0+IFR1cm5oYWxsZSAoSFx1MDBmY3BmYnVyZ2VuKSAtPiBUdXJuaGFsbGUtVW1rbGVpZGVyYXVtIC0+IEd5bW5hc3Rpa3JhdW0gLT4gS2xhc3NlbnJhdW0gLT4gS2xhc3NlbnJhdW0gKEJPU1MpXG5cbkFuemFobCBkZXIgU3BlemlhbC1Cb3hlbjogNlxuICAgICAgICAiLCAiXG5JY2ggYmVzY2hyZWliZSBkaWVzZW4gTGF1ZiBmb2xnZW5kZXJtYVx1MDBkZmVuOlxuXG5cbkRpZSBlcnN0ZSBab25lIGJlZmluZGV0IHNpY2ggaW4gZGVyIFR1cm5oYWxsZS5cblNpZSBiZWdyXHUwMGZjXHUwMGRmdCBkZW4gSGVsZCBtaXQgdmllbCBCZXdlZ3VuZ3NmcmVpaGVpdC5cblxuTmFjaGRlbSBlciBkZW4gU2NobGVjaHRlbiBpbiBkZXIgZXJzdGVuIFpvbmUgYmVzaWVndCBoYXQsIGZcdTAwZmNsbHQgZGVyIEhlbGQgZWluIGdyb1x1MDBkZmVuIEh1bmdlciwgZGFzcyBlciBuaWNodCBtZWhyIGF1c2hhbHRlbiBrYW5uLlxuRGllIHp3ZWl0ZSBab25lIGJlZmluZGV0IHNpY2ggaW4gZGVyIEhhdXB0a1x1MDBmY2NoZS5cbkVyIGVudGhcdTAwZTRsdCBkcmVpIEtcdTAwZmNjaGVuemVpbGVuLCB3b2JlaSBqZWRlciBBa3QgZWluZSBLXHUwMGZjY2hlbnplaWxlIGRhcnN0ZWxsdC5cbk9oIE5laW4hIERlciBIZWxkIGhhdCB3YWhyc2NoZWlubGljaCBlaW5lbiBGZWhsZXIgZ2VtYWNodC5cbkRvcnQgc29sbCBlciB2ZXJzdWNoZW4gZGllIGhlaVx1MDBkZmUgVGVtcGVyYXR1cmVuIGF1c3p1d2VpY2hlbi5cblxuRGVyIEhlbGQgYmVrb21tdCBlcyBudW4gbWl0IGRlciBIaXR6ZSB6dSB0dW4uXG5EZXNoYWxiIHJlbm50IGVyIHp1clx1MDBmY2NrIGluIGRpZSBUdXJuaGFsbGUgXHUyMDEzIGRvcnQgYmVmaW5kZXQgc2ljaCBhdWNoIGRpZSBkcml0dGUgWm9uZSBcdTIwMTMsIGRvY2ggZXIgYWhudCBuaWNodCwgZGFzcyBkaWUgTGVocmVyIGdlcGxhbnQgaGFiZW4sIHNpZSB6dSB2ZXJ3YW5kZWxuLCBpbmRlbSBzaWUgZHJlaSBIXHUwMGZjcGZidXJnZW4gaW4gaWhyZW0gSW5uZXJlbiBhdWZibGFzZW4sIHdcdTAwZTRocmVuZCBlciBzaWNoIG5vY2ggaW4gZGVyIEhhdXB0a1x1MDBmY2NoZSBhdWZoXHUwMGU0bHRcbk51biBtdXNzIGVyIGRpZXNlIEhcdTAwZmNwZmJ1cmdlbiBiZXRyZXRlbi4gSmVkZXIgZG9ydGlnZSBBa3QgZW50c3ByaWNodCBlaW5lciBIXHUwMGZjcGZidXJnLlxuU2llIGhhYmVuIHNpZSB2b24gZWluZW0gZnJpZWRsaWNoZW4gUmF1bSBpbiBlaW5lbiBwb3RlbnppZWxsIGJcdTAwZjZzZW4gT3J0IHZlcndhbmRlbHQsIGRlciBkZW0gSGVsZGVuIHdvbVx1MDBmNmdsaWNoIFx1MDBmY2JsZSBTdHJlaWNoZSBzcGllbHQgW3ouQi4gbVx1MDBmNmdsaWNoZSB1bmVyd2FydGV0ZSBUb2Rlc3N0ZWxsZW5dLlxuIiwgIlxuRGEgZGllIFR1cm5oYWxsZSBudW4gZWluZSBiZWRyb2hsaWNoZSBBdXNzdHJhaGx1bmcgaGF0LCB3aXJkIHNpZSBkZW4gSGVsZGVuIFx1MjAxMyBuYWNoZGVtIGVyIGRlbiBCXHUwMGY2c2V3aWNodCBpbiBpaHJlbSBJbm5lcmVuIGVybmV1dCBiZXNpZWd0IGhhdCBcdTIwMTMgZGlyZWt0IGluIGVpbmVyIHNlaW5lciBVbWtsZWlkZXJcdTAwZTR1bWUgc2NoaWNrZW47IGRvcnQgYmVmaW5kZXQgc2ljaCBkaWUgdmllcnRlIFpvbmUuXG5JbiBkaWVzZW0gUmF1bSBzdGVoZW4gZHJlaSBXYXNjaGJlY2tlbiwgZGllIGRlciBIZWxkIHBhc3NpZXJlbiBtdXNzLCB1bSBpbiBkZW4gblx1MDBlNGNoc3RlbiBSYXVtIHp1IGdlbGFuZ2VuOyBkYWJlaSBzdGVodCBqZWRlcyBkZXIgV2FzY2hiZWNrZW4gZlx1MDBmY3IgZWluZW4gZGVyIGRvcnRpZ2VuIEFrdC5cbkplZGVyIGRpZXNlciBkcmVpIFdhc2NoYmVja2VuIHNpbmQgbWl0IFdhc3NlciBnZWZcdTAwZmNsbHQuIERlciBIZWxkIGthbm4gZGVuIEF0ZW0gbnVyIDMwIFNla3VuZGVuIGxhbmcgYW5oYWx0ZW4sIGJldm9yIGVyIGRlbiBXYXNzZXJ0b2Qgc3RpcmJ0LlxuXG5OYWNoZGVtIGVyIGF1cyBkZW0gVW1rbGVpZGVyYXVtIGVudGtvbW1lbiBpc3QsIGJldHJpdHQgZXIgZWluZW4gZnJpZWRsaWNoZW4gUmF1bSwgZGVyIEd5bW5hc3Rpa3JhdW0uIEhpZXIgYmVmaW5kZXQgc2ljaCBkaWUgZlx1MDBmY25mdGUgWm9uZS5cbldcdTAwZTRocmVuZCBzaWNoIGRlciBIZWxkIGRvcnQgYXVmaFx1MDBlNGx0LCBzY2hhdWVuIHNpY2ggZGllIEFud2VzZW5kZW4gZ2VyYWRlIGVpbmVuIGd1dGVuIEZpbG0gbmFtZW5zIFx1MjAxZUtQb3AgRGVtb24gSHVudGVyc1x1MjAxYyBhbi5cbiIsICJcbk5hY2hkZW0gZXIgZGVuIEJcdTAwZjZzZXdpY2h0IGltIEd5bW5hc3Rpa3JhdW0gYmVzaWVndCBoYXQsIGVycmVpY2h0IGVyIGRhcyBLbGFzc2VuemltbWVyLCBpbiBkZW0gc2ljaCBkaWUgbGV0enRlbiBiZWlkZW4gWm9uZW4gYmVmaW5kZW4uXG5cblZvbiBhdVx1MDBkZmVuIHdpcmt0IHNpZSB1bnNjaHVsZGlnIHVuZCB2b24gaW5uZW4gZ2VtXHUwMGZjdGxpY2gsIGRvY2ggc2llIGJpcmd0IGlocmUgZWlnZW5lbiBGYWxsZW4sIGRpZSBkZW0gSGVsZGVuIG5hY2ggZGVtIExlYmVuIHRyYWNodGVuLlxuXG5JbiBBa3QgMSBiZW1lcmt0IGRlciBIZWxkLCBkYXNzIGRpZSBMZXV0ZSBpbiBpaHJlbSBJbm5lcmVuIGVpbmVuIEZpbG0gYW5zZWhlbi4gRGllc2VyIEZpbG0gZW50aFx1MDBlNGx0IHphaGxyZWljaGUgR2VyXHUwMGU0dXNjaGUgdm9uIHplcmJyZWNoZW5kZW0gR2xhcywgZGllIGxhdXQgaW4gaWhyIGFiZ2VzcGllbHQgd2VyZGVuLlxuSW4gQWt0IDIgYmVtZXJrdCBkZXIgSGVsZCwgZGFzcyBpbiBpaHJlbSBJbm5lcmVuIGF1Y2ggZ2Vrb2NodCB3aXJkIFx1MjAxMyBzaWUgdmVyZlx1MDBmY2d0IGFsc28gXHUwMGZjYmVyIGVpbmUgS29jaG5pc2NoZS4gRXIgYmVmaW5kZXQgc2ljaCBkb3J0IGltIHVudGVyZW4gQmVyZWljaCBkaWVzZXIgS29jaG5pc2NoZSBhdWYuXG5JbiBBa3QgMyBcdTAwZmNiZXJyYXNjaHQgc2llIGRlbiBIZWxkZW4sIGluZGVtIHNpZSBpaG4gaW4gZWluIHdlaXRlcmVzIFdhc2NoYmVja2VuIGJlZlx1MDBmNnJkZXJ0IFx1MjAxMyBzaWUgdmVyZlx1MDBmY2d0IGFsc28gXHUwMGZjYmVyIGVpbiBXYXNjaGJlY2tlbi5cbk5hY2hkZW0gZGVyIEhlbGQgZGllc2VtIFdhc2NoYmVja2VuIGVudGtvbW1lbiBpc3QsIHN0ZWxsdCBlciBzaWNoIGRlbSBlaWdlbnRsaWNoZW4gQm9zc2thbXBmIGdlZ2VuIHNpZS5cbkRlciBIZWxkIGJlZmluZGV0IHNpY2ggaW1tZXIgbm9jaCBpbSBLbGFzc2VucmF1bS4gIEVyIGJlZmluZGV0IHNpY2ggZG9ydCBpbSBvYmVyZW4gQmVyZWljaCBzZWluZXIgS29jaG5pc2NoZSBhdWYuXG5cbk5hY2hkZW0gZGVyIEhlbGQgZGVuIEJvc3MgaW4gaWhyZW0gSW5uZXJlbiBiZXNpZWd0IGhhdCwga2VocnQgZXIgaW4gZGllIFR1cm5oYWxsZSBbZG9ydCB3aXJkIGVpbmUgQWJzY2hsdXNzZmVpZXIgZ2VmZWllcnRdIHp1clx1MDBmY2NrIChkaWUgd2llZGVyIGlocmVuIE5vcm1hbHp1c3RhbmQgYW5nZW5vbW1lbiBoYXQpLCBsXHUwMGU0c3N0IGRpZSBTdGVpbmUgXHUyMDBiXHUyMDBiXHUwMGZjYmVyIHNpY2ggc2Nod2ViZW4gdW5kIHZvbGxmXHUwMGZjaHJ0IGFuc2NobGllXHUwMGRmZW5kIGVpbmVuIFNpZWdlcnNwcnVuZy5cbkRhbWl0IGVuZGV0IGRpZSBHZXNjaGljaHRlLlxuIiwgIlxuRnJhZ2U6IFdpZSBnZWxhbmd0IG1hbiBpbiBkaWVzZSBTcGV6aWFsLUJveGVuPyBcbkFudHdvcnQ6IER1cmNoIEhpbmVpbnNwcmluZ2VuIGluIGRlbiByaWVzaWdlbiBSaW5nIGFtIEVuZGUgdm9uIEFrdCAxIHVuZC9vZGVyIDIsIGplZGVyIFpvbmUgW2ZcdTAwZmNyIG1cdTAwZTRubmxpY2ggdW5kIHdlaWJsaWNoXSwgd2VubiBkdSBtaW5kZXN0ZW5zIDUwIEVpbmhlaXRlbiBlaW5lciBXXHUwMGU0aHJ1bmcgaGFzdCwgYmV2b3IgZHUgZGFzIEtsYXNzZW56aW1tZXIgZXJyZWljaHRzLlxuRmFrdDogRGFzIGd1dGUgRW5kZSBsXHUwMGU0c3N0IHNpY2ggZXJyZWljaGVuLCBpbmRlbSBtYW4gZGVuIEJvc3MgaW0gS2xhc3NlbnppbW1lciBiZXNpZWd0LCBuYWNoZGVtIGFsbGUgU3BlemlhbC1Cb3hlbiBlcmZvbGdyZWljaCBhYnNvbHZpZXJ0IHd1cmRlbi5cbiAgICAgICAgXG5XZW5uIGR1IGltIGVpZ2VudGxpY2hlbiBTcGllbCBHbGFzIHplcmJyaWNoc3QsIHplcmJyaWNoc3QgZHUgYXVjaCBHbGFzIGluIGRlbSBlbnRzcHJlY2hlbmRlbiBSYXVtIChiYXNpZXJlbmQgYXVmIGRlciBqZXdlaWxpZ2VuIFpvbmUpLlxuRHUga2FubnN0IGVpbmVuIFJhdW0ga29tcGxldHQgdmVyd1x1MDBmY3N0ZW4sIHdlbm4gZHUgXHUyMDFlamVkZXMgZWluemVsbmVcdTIwMWMgR2xhc29iamVrdCBpbiBkZXIvZGVuIGVudHNwcmVjaGVuZGVuIFpvbmUobikgKGdlbVx1MDBlNFx1MDBkZiBCZXNjaHJlaWJ1bmcpIHplcmJyaWNoc3QuXG5CZXNvbmRlcmhlaXQ6IEltIHZvbGxzdFx1MDBlNG5kaWdlbiBTcGllbGR1cmNobGF1ZiBrYW5uc3QgZHUgZGllIFR1cm5oYWxsZSB0YXRzXHUwMGU0Y2hsaWNoIHp3ZWltYWwgdmVyd1x1MDBmY3N0ZW4uXG5cbldlbm4gZHUgYmVtZXJrc3QsIGRhc3MgZGFzIFNwaWVsIHJ1Y2tlbHQsIGJlZGV1dGV0IGRhcywgZGFzcyBkdSBkZW4gQXRlbSBlaW5lcyB3ZWlibGljaGVuIFJhdW1zIHNwXHUwMGZjcmVuIGtcdTAwZjZubnRlc3QuXG4gICAgICAgICJdfQ==

"""

"""

eyJTdG9wcHVociI6IDE1OTkuNzI5MzEwNzUwOTYxMywgIlp3aXNjaGVuemVpdGVuIjogWzM5LjEyLCA1OS4yOSwgMTAzLjgxLCAxMzEuOTcsIDE5Ni41NSwgMjgzLjc5LCAzMDUuODMsIDQxNy40LCA0NDUuNzUsIDU3NS42MywgNjUyLjM2LCA2OTAuNywgNzU1LjkxLCA3NzIuMTgsIDkwMy43NCwgOTY4LjIzLCAxMDA3LjgxLCAxMTMwLjEyLCAxMTgyLjg3LCAxMjM1LjMxLCAxMzE3Ljg5LCAxMzgwLjAzLCAxNDQ4Ljk3LCAxNDg5LjAxLCAxNTgzLjI5XSwgIkFrdHVlbGxlIFp3aXNjaGVuemVpdGVuIjogWzM3LjAyMzc4MDM0NTkxNjc1LCA1Ny4xMTQ2NzEyMzAzMTYxNiwgMTAxLjU3OTI5ODQ5NjI0NjM0LCAxMzAuOTQ2NTM0NjMzNjM2NDcsIDE5Mi42MzY2MTE3MDAwNTc5OCwgMjc5LjQ0MDg0MTkxMzIyMzI3LCAyOTkuMjcxNzAzOTU4NTExMzUsIDQwMi42MTkwNjE5NDY4Njg5LCA0NDAuNjc5MDA2MDk5NzAwOSwgNTY1LjQxNzEyMDIxODI3NywgNjQwLjUyMjc5ODc3NjYyNjYsIDY4MS44NjA1OTgwODczMTA4LCA3NDQuOTM0NzgxMDc0NTIzOSwgNzYxLjQxNzY3NDMwMzA1NDgsIDkwNS4zODkyMzA0ODk3MzA4LCA5NjkuMTQzODYzMjAxMTQxNCwgMTAwNC4xMDMxMzMyMDE1OTkxLCAxMTEwLjgyMjAzODY1MDUxMjcsIDExNjYuNzgxMTA1Mjc5OTIyNSwgMTIxOS4yNjM5MTYwMTU2MjUsIDEzMzAuNTg2NTUwOTUxMDA0LCAxMzkzLjE3MTM4NzkxMDg0MywgMTQ2Mi4zMDIxMTE2MjU2NzE0LCAxNTA1LjU1MTgzMTI0NTQyMjQsIDE1OTkuNjgzMTc5NjE2OTI4XSwgIkJlc3RlIFNlZ21lbnRlIjogW1sxOTMuNTQsIDM1OS42NiwgMzI4LjExLCAyMDQsIDE4Ny4wOSwgMjY1LjI2XSwgWzM3LjE1LCAxOC42LCA0MywgMjYsIDYzLjE0LCA4Ni44OSwgMTguOSwgOTQuOSwgMjguMjUsIDExNy41NiwgNzYuNzMsIDM4LjM0LCA2My4zMSwgMTUsIDEzMS41NiwgNjAuMzMsIDMzLjUsIDEwNy45NiwgNTIuNzUsIDQ5LjA4LCA4Mi41OCwgNjIuMTQsIDY0LjMsIDM5LjQ5LCA4MF0sIFtdLCBbXSwgW10sIFtdLCBbXSwgW10sIFtdLCBbXV0sICJTcGllbG5hbWUiOiAiU29uaWMgVGhlIEhlZGdlaG9nIEdlbmVzaXMgKEdCQSAtIFVTQSBWZXJzaW9uKSIsICJEdXJjaGxhdWZrYXRlZ29yaWUiOiAiW1RhZyAwMDEzOV0gQWxsZSBTbWFyYWdkZSBpbSBKdWJpbFx1MDBlNHVtc21vZHVzIiwgIlNlZ21lbnRuYW1lbiI6IFsiLUFrdCAxOiBXYXMgZlx1MDBmY3IgZWluIHNjaHdlcmVyIEFuZmFuZyEiLCAiLVNwZXppYWwgMTogRXMgZ2VodCBzY2huZWxsIHdpZWRlciB3ZWciLCAiLUFrdCAyOiBXaWxsIGRlbiBNb3RvYnVnIG5pY2h0IHRcdTAwZjZ0ZW4uIiwgIi1TcGV6aWFsIDI6IERpZXNlcyBUaW1pbmcuLi4iLCAiXHUyNjQwXHVkODNjXHVkZmMwIDAwLjA4ICpSRVNFVC0qVHVybmhhbGxlIFtOb3JtYWxdfEFrdCAzOiBCaXR0ZSBrZWluZSBUcmVmZmVyIHZlcmZlaGxlbiEiLCAiLUFrdCAxOiBESUUgWllLTEVOISIsICItU3BlemlhbCAzOiBTUFJJTkchIiwgIi1Ba3QgMjogQml0dGUgbmljaHQgZ2V0cm9mZmVuIHdlcmRlbiEiLCAiLVNwZXppYWwgNDogVmVybWFzc2VsIGRhcyBuaWNodC4iLCAiXHUyNjQyXHVkODNjXHVkZjczIDAwLjI1IEhhdXB0a1x1MDBmY2NoZSBkZXIgU2NodWxlfEFrdCAzOiBHZWZcdTAwZTRocmxpY2hlcyBFbmRlIGVpbmVyIFpvbmUiLCAiLUFrdCAxOiBOT0NIIEVJTiBaWUtMVVMhIiwgIi1TcGV6aWFsIDU6IE1FSU5FIEdSXHUwMGQ2U1NURSBTQ0hXXHUwMGM0Q0hFIERPUlQhIiwgIi1Ba3QgMjogRVRXQVMgSEVJS0xJRyEiLCAiLVNwZXppYWwgNjogU1BSSU5HISEiLCAiXHUyNjQwXHVkODNjXHVkZmYwIDAwLjA4IFR1cm5oYWxsZSBbQWt0PUhcdTAwZmNwZmJ1cmddfEFrdCAzOiBIRUlLTElHIEFNIEFORkFORyEiLCAiLUFrdC9XYXNjaGJlY2tlbiAxOiBXYXNzZXJwaHlzaWshIiwgIi1Ba3QvV2FzY2hiZWNrZW4gMjogTlx1MDBmY3R6bGljaGVyIFNwcnVuZ2ZlZGVyISIsICJcdTI2NDJcdWQ4M2RcdWRlYmYgMDAuMTEgVHVybmhhbGxlLVVta2xlaWRlcmF1bXxBa3QvV2FzY2hiZWNrZW4gMzogUEFSS09VUlpFSVQhIiwgIi1Ba3QgMTogU2llIHNjaGF1ZW4gZGEgZWluIGd1dGVuIEZpbG0iLCAiLUFrdCAyOiBTaWUgc2NoYXVlbiBzaWNoIGdlcmFkZSBcdTIwMWVHb2xkZW5cdTIwMWMgYW4uIiwgIlx1MjY0Mlx1ZDgzY1x1ZGZhYyAxMC4wNSBHeW1uYXN0aWtyYXVtIFtLaW5vcmF1bV18QWt0IDM6IERpZXNlciBGaWxtOiBLUG9wIERlbW9uIEh1bnRlcnMiLCAiLVx1ZDgzZFx1ZGNjZCBBa3QgMSBbUmF1bW1pdHRlXTogRGEgd2lyZCBhdWNoIEZpbG0gZ2VzY2hhdXQhIiwgIi1cdWQ4M2NcdWRmNzMgQWt0IDIgW0tvY2huaXNjaGUoXHUyMTkzKV06IERhIHdpcmQgZ2Vrb2NodCEiLCAiLVx1ZDgzZFx1ZGViMCBBa3QgMyBbV2FzY2hiZWNrZW5dOiBTbyBoeWdpZW5pc2NoIHNjaGxhdSEiLCAiXHUyNjQwXHVkODNjXHVkZjkyIDEwLjI4IEtsYXNzZW5yYXVtIFtTZWh1c2FzY2h1bGVdfFx1ZDgzY1x1ZGY3ZCBCT1NTIFtLb2NobmlzY2hlKFx1MjE5MSldOiBXSUVERVIgSEVJS0xJRyEiXSwgIkJlc2NocmVpYnVuZyI6IFsiXG5NZWluZSBCZXNjaHJlaWJ1bmcgZGVzIER1cmNobGF1ZnNcblxuXG5TcGllbHZlcnNpb246IFNjaGxlY2h0ZXN0ZSBvZmZpemllbGxlIFBvcnRpZXJ1bmcgZGVzIFNwaWVsc1xuLT4gU2llIGhhYmVuIGVyd2FydGV0LCBkYXNzIGRpZXNlIFNwaWVscG9ydGllcnVuZyBndXQgd2lyZC5cbi0+IEVpbmUgS2F0YXN0cm9waGUsIG1pdCBkZXIgc2llIG5pY2h0IGdlcmVjaG5ldCBoYXR0ZW4uXG4tPiBEaWVzZSBQb3J0aWVydW5nIGJhc2llcnQgc2ljaCBhdWYgZWluZSBhbmRlcmUgUG9ydGllcnVuZy5cbi0+IERhcyBlaWdlbnRsaWNoZSBTcGllbCBoYXQgbml4IG1pdCBIb3Jyb3IgenUgdHVuLlxuTWV0YXNjb3JlOiAzMy8xMDBcbkFuemFobCBkZXIgWm9uZW46IDYgKyAxID0gN1xuQW56YWhsIGRlciB2b2xsc3RcdTAwZTRuZGlnZW4gUlx1MDBlNHVtZTogNVxuUmF1bW51bW1lcm4sIEdlc2NobGVjaHQgdW5kIE5hbWVuIGRpZXNlciBSXHUwMGU0dW1lOlxuXHUyNWNmIDAwLjA4IFR1cm5oYWxsZSBbd2VpYmxpY2hdXG5cdTI1Y2YgMDAuMjUgSGF1cHRrXHUwMGZjY2hlIFttXHUwMGU0bm5saWNoXVxuXHUyNWNmIDAwLjExIFR1cm5oYWxsZS1VbWtsZWlkZXJhdW0gW21cdTAwZTRubmxpY2hdXG5cdTI1Y2YgMTAuMDUgR3ltbmFzdGlrcmF1bSBbbVx1MDBlNG5ubGljaF1cblx1MjVjZiAxMC4yOCBLbGFzc2VucmF1bSBbd2VpYmxpY2hdXG5cblNwaWVscmVpaGVuZm9sZ2UgZGVyIGFuZ2VnZWJlbmVuIFJcdTAwZTR1bWU6XG5cdTI1Y2YgVHVybmhhbGxlIChOb3JtYWwpIC0+IEhhdXB0a1x1MDBmY2NoZSAtPiBUdXJuaGFsbGUgKEhcdTAwZmNwZmJ1cmdlbikgLT4gVHVybmhhbGxlLVVta2xlaWRlcmF1bSAtPiBHeW1uYXN0aWtyYXVtIC0+IEtsYXNzZW5yYXVtIC0+IEtsYXNzZW5yYXVtIChCT1NTKVxuXG5BbnphaGwgZGVyIFNwZXppYWwtQm94ZW46IDZcbiAgICAgICAgIiwgIlxuSWNoIGJlc2NocmVpYmUgZGllc2VuIExhdWYgZm9sZ2VuZGVybWFcdTAwZGZlbjpcblxuXG5EaWUgZXJzdGUgWm9uZSBiZWZpbmRldCBzaWNoIGluIGRlciBUdXJuaGFsbGUuXG5TaWUgYmVnclx1MDBmY1x1MDBkZnQgZGVuIEhlbGQgbWl0IHZpZWwgQmV3ZWd1bmdzZnJlaWhlaXQuXG5cbk5hY2hkZW0gZXIgZGVuIFNjaGxlY2h0ZW4gaW4gZGVyIGVyc3RlbiBab25lIGJlc2llZ3QgaGF0LCBmXHUwMGZjbGx0IGRlciBIZWxkIGVpbiBncm9cdTAwZGZlbiBIdW5nZXIsIGRhc3MgZXIgbmljaHQgbWVociBhdXNoYWx0ZW4ga2Fubi5cbkRpZSB6d2VpdGUgWm9uZSBiZWZpbmRldCBzaWNoIGluIGRlciBIYXVwdGtcdTAwZmNjaGUuXG5FciBlbnRoXHUwMGU0bHQgZHJlaSBLXHUwMGZjY2hlbnplaWxlbiwgd29iZWkgamVkZXIgQWt0IGVpbmUgS1x1MDBmY2NoZW56ZWlsZSBkYXJzdGVsbHQuXG5PaCBOZWluISBEZXIgSGVsZCBoYXQgd2FocnNjaGVpbmxpY2ggZWluZW4gRmVobGVyIGdlbWFjaHQuXG5Eb3J0IHNvbGwgZXIgdmVyc3VjaGVuIGRpZSBoZWlcdTAwZGZlIFRlbXBlcmF0dXJlbiBhdXN6dXdlaWNoZW4uXG5cbkRlciBIZWxkIGJla29tbXQgZXMgbnVuIG1pdCBkZXIgSGl0emUgenUgdHVuLlxuRGVzaGFsYiByZW5udCBlciB6dXJcdTAwZmNjayBpbiBkaWUgVHVybmhhbGxlIFx1MjAxMyBkb3J0IGJlZmluZGV0IHNpY2ggYXVjaCBkaWUgZHJpdHRlIFpvbmUgXHUyMDEzLCBkb2NoIGVyIGFobnQgbmljaHQsIGRhc3MgZGllIExlaHJlciBnZXBsYW50IGhhYmVuLCBzaWUgenUgdmVyd2FuZGVsbiwgaW5kZW0gc2llIGRyZWkgSFx1MDBmY3BmYnVyZ2VuIGluIGlocmVtIElubmVyZW4gYXVmYmxhc2VuLCB3XHUwMGU0aHJlbmQgZXIgc2ljaCBub2NoIGluIGRlciBIYXVwdGtcdTAwZmNjaGUgYXVmaFx1MDBlNGx0XG5OdW4gbXVzcyBlciBkaWVzZSBIXHUwMGZjcGZidXJnZW4gYmV0cmV0ZW4uIEplZGVyIGRvcnRpZ2UgQWt0IGVudHNwcmljaHQgZWluZXIgSFx1MDBmY3BmYnVyZy5cblNpZSBoYWJlbiBzaWUgdm9uIGVpbmVtIGZyaWVkbGljaGVuIFJhdW0gaW4gZWluZW4gcG90ZW56aWVsbCBiXHUwMGY2c2VuIE9ydCB2ZXJ3YW5kZWx0LCBkZXIgZGVtIEhlbGRlbiB3b21cdTAwZjZnbGljaCBcdTAwZmNibGUgU3RyZWljaGUgc3BpZWx0IFt6LkIuIG1cdTAwZjZnbGljaGUgdW5lcndhcnRldGUgVG9kZXNzdGVsbGVuXS5cbiIsICJcbkRhIGRpZSBUdXJuaGFsbGUgbnVuIGVpbmUgYmVkcm9obGljaGUgQXVzc3RyYWhsdW5nIGhhdCwgd2lyZCBzaWUgZGVuIEhlbGRlbiBcdTIwMTMgbmFjaGRlbSBlciBkZW4gQlx1MDBmNnNld2ljaHQgaW4gaWhyZW0gSW5uZXJlbiBlcm5ldXQgYmVzaWVndCBoYXQgXHUyMDEzIGRpcmVrdCBpbiBlaW5lciBzZWluZXIgVW1rbGVpZGVyXHUwMGU0dW1lIHNjaGlja2VuOyBkb3J0IGJlZmluZGV0IHNpY2ggZGllIHZpZXJ0ZSBab25lLlxuSW4gZGllc2VtIFJhdW0gc3RlaGVuIGRyZWkgV2FzY2hiZWNrZW4sIGRpZSBkZXIgSGVsZCBwYXNzaWVyZW4gbXVzcywgdW0gaW4gZGVuIG5cdTAwZTRjaHN0ZW4gUmF1bSB6dSBnZWxhbmdlbjsgZGFiZWkgc3RlaHQgamVkZXMgZGVyIFdhc2NoYmVja2VuIGZcdTAwZmNyIGVpbmVuIGRlciBkb3J0aWdlbiBBa3QuXG5KZWRlciBkaWVzZXIgZHJlaSBXYXNjaGJlY2tlbiBzaW5kIG1pdCBXYXNzZXIgZ2VmXHUwMGZjbGx0LiBEZXIgSGVsZCBrYW5uIGRlbiBBdGVtIG51ciAzMCBTZWt1bmRlbiBsYW5nIGFuaGFsdGVuLCBiZXZvciBlciBkZW4gV2Fzc2VydG9kIHN0aXJidC5cblxuTmFjaGRlbSBlciBhdXMgZGVtIFVta2xlaWRlcmF1bSBlbnRrb21tZW4gaXN0LCBiZXRyaXR0IGVyIGVpbmVuIGZyaWVkbGljaGVuIFJhdW0sIGRlciBHeW1uYXN0aWtyYXVtLiBIaWVyIGJlZmluZGV0IHNpY2ggZGllIGZcdTAwZmNuZnRlIFpvbmUuXG5XXHUwMGU0aHJlbmQgc2ljaCBkZXIgSGVsZCBkb3J0IGF1ZmhcdTAwZTRsdCwgc2NoYXVlbiBzaWNoIGRpZSBBbndlc2VuZGVuIGdlcmFkZSBlaW5lbiBndXRlbiBGaWxtIG5hbWVucyBcdTIwMWVLUG9wIERlbW9uIEh1bnRlcnNcdTIwMWMgYW4uXG4iLCAiXG5OYWNoZGVtIGVyIGRlbiBCXHUwMGY2c2V3aWNodCBpbSBHeW1uYXN0aWtyYXVtIGJlc2llZ3QgaGF0LCBlcnJlaWNodCBlciBkYXMgS2xhc3NlbnppbW1lciwgaW4gZGVtIHNpY2ggZGllIGxldHp0ZW4gYmVpZGVuIFpvbmVuIGJlZmluZGVuLlxuXG5Wb24gYXVcdTAwZGZlbiB3aXJrdCBzaWUgdW5zY2h1bGRpZyB1bmQgdm9uIGlubmVuIGdlbVx1MDBmY3RsaWNoLCBkb2NoIHNpZSBiaXJndCBpaHJlIGVpZ2VuZW4gRmFsbGVuLCBkaWUgZGVtIEhlbGRlbiBuYWNoIGRlbSBMZWJlbiB0cmFjaHRlbi5cblxuSW4gQWt0IDEgYmVtZXJrdCBkZXIgSGVsZCwgZGFzcyBkaWUgTGV1dGUgaW4gaWhyZW0gSW5uZXJlbiBlaW5lbiBGaWxtIGFuc2VoZW4uIERpZXNlciBGaWxtIGVudGhcdTAwZTRsdCB6YWhscmVpY2hlIEdlclx1MDBlNHVzY2hlIHZvbiB6ZXJicmVjaGVuZGVtIEdsYXMsIGRpZSBsYXV0IGluIGlociBhYmdlc3BpZWx0IHdlcmRlbi5cbkluIEFrdCAyIGJlbWVya3QgZGVyIEhlbGQsIGRhc3MgaW4gaWhyZW0gSW5uZXJlbiBhdWNoIGdla29jaHQgd2lyZCBcdTIwMTMgc2llIHZlcmZcdTAwZmNndCBhbHNvIFx1MDBmY2JlciBlaW5lIEtvY2huaXNjaGUuIEVyIGJlZmluZGV0IHNpY2ggZG9ydCBpbSB1bnRlcmVuIEJlcmVpY2ggZGllc2VyIEtvY2huaXNjaGUgYXVmLlxuSW4gQWt0IDMgXHUwMGZjYmVycmFzY2h0IHNpZSBkZW4gSGVsZGVuLCBpbmRlbSBzaWUgaWhuIGluIGVpbiB3ZWl0ZXJlcyBXYXNjaGJlY2tlbiBiZWZcdTAwZjZyZGVydCBcdTIwMTMgc2llIHZlcmZcdTAwZmNndCBhbHNvIFx1MDBmY2JlciBlaW4gV2FzY2hiZWNrZW4uXG5OYWNoZGVtIGRlciBIZWxkIGRpZXNlbSBXYXNjaGJlY2tlbiBlbnRrb21tZW4gaXN0LCBzdGVsbHQgZXIgc2ljaCBkZW0gZWlnZW50bGljaGVuIEJvc3NrYW1wZiBnZWdlbiBzaWUuXG5EZXIgSGVsZCBiZWZpbmRldCBzaWNoIGltbWVyIG5vY2ggaW0gS2xhc3NlbnJhdW0uICBFciBiZWZpbmRldCBzaWNoIGRvcnQgaW0gb2JlcmVuIEJlcmVpY2ggc2VpbmVyIEtvY2huaXNjaGUgYXVmLlxuXG5OYWNoZGVtIGRlciBIZWxkIGRlbiBCb3NzIGluIGlocmVtIElubmVyZW4gYmVzaWVndCBoYXQsIGtlaHJ0IGVyIGluIGRpZSBUdXJuaGFsbGUgW2RvcnQgd2lyZCBlaW5lIEFic2NobHVzc2ZlaWVyIGdlZmVpZXJ0XSB6dXJcdTAwZmNjayAoZGllIHdpZWRlciBpaHJlbiBOb3JtYWx6dXN0YW5kIGFuZ2Vub21tZW4gaGF0KSwgbFx1MDBlNHNzdCBkaWUgU3RlaW5lIFx1MjAwYlx1MjAwYlx1MDBmY2JlciBzaWNoIHNjaHdlYmVuIHVuZCB2b2xsZlx1MDBmY2hydCBhbnNjaGxpZVx1MDBkZmVuZCBlaW5lbiBTaWVnZXJzcHJ1bmcuXG5EYW1pdCBlbmRldCBkaWUgR2VzY2hpY2h0ZS5cbiIsICJcbkZyYWdlOiBXaWUgZ2VsYW5ndCBtYW4gaW4gZGllc2UgU3BlemlhbC1Cb3hlbj8gXG5BbnR3b3J0OiBEdXJjaCBIaW5laW5zcHJpbmdlbiBpbiBkZW4gcmllc2lnZW4gUmluZyBhbSBFbmRlIHZvbiBBa3QgMSB1bmQvb2RlciAyLCBqZWRlciBab25lIFtmXHUwMGZjciBtXHUwMGU0bm5saWNoIHVuZCB3ZWlibGljaF0sIHdlbm4gZHUgbWluZGVzdGVucyA1MCBFaW5oZWl0ZW4gZWluZXIgV1x1MDBlNGhydW5nIGhhc3QsIGJldm9yIGR1IGRhcyBLbGFzc2VuemltbWVyIGVycmVpY2h0cy5cbkZha3Q6IERhcyBndXRlIEVuZGUgbFx1MDBlNHNzdCBzaWNoIGVycmVpY2hlbiwgaW5kZW0gbWFuIGRlbiBCb3NzIGltIEtsYXNzZW56aW1tZXIgYmVzaWVndCwgbmFjaGRlbSBhbGxlIFNwZXppYWwtQm94ZW4gZXJmb2xncmVpY2ggYWJzb2x2aWVydCB3dXJkZW4uXG4gICAgICAgIFxuV2VubiBkdSBpbSBlaWdlbnRsaWNoZW4gU3BpZWwgR2xhcyB6ZXJicmljaHN0LCB6ZXJicmljaHN0IGR1IGF1Y2ggR2xhcyBpbiBkZW0gZW50c3ByZWNoZW5kZW4gUmF1bSAoYmFzaWVyZW5kIGF1ZiBkZXIgamV3ZWlsaWdlbiBab25lKS5cbkR1IGthbm5zdCBlaW5lbiBSYXVtIGtvbXBsZXR0IHZlcndcdTAwZmNzdGVuLCB3ZW5uIGR1IFx1MjAxZWplZGVzIGVpbnplbG5lXHUyMDFjIEdsYXNvYmpla3QgaW4gZGVyL2RlbiBlbnRzcHJlY2hlbmRlbiBab25lKG4pIChnZW1cdTAwZTRcdTAwZGYgQmVzY2hyZWlidW5nKSB6ZXJicmljaHN0LlxuQmVzb25kZXJoZWl0OiBJbSB2b2xsc3RcdTAwZTRuZGlnZW4gU3BpZWxkdXJjaGxhdWYga2FubnN0IGR1IGRpZSBUdXJuaGFsbGUgdGF0c1x1MDBlNGNobGljaCB6d2VpbWFsIHZlcndcdTAwZmNzdGVuLlxuXG5XZW5uIGR1IGJlbWVya3N0LCBkYXNzIGRhcyBTcGllbCBydWNrZWx0LCBiZWRldXRldCBkYXMsIGRhc3MgZHUgZGVuIEF0ZW0gZWluZXMgd2VpYmxpY2hlbiBSYXVtcyBzcFx1MDBmY3JlbiBrXHUwMGY2bm50ZXN0LlxuICAgICAgICAiXX0=


"""

"""

eyJTdG9wcHVociI6IDAuMCwgIlp3aXNjaGVuemVpdGVuIjogWzM5LjEyLCA1OS4yOSwgMTAzLjgxLCAxMzEuOTcsIDE5Ni41NSwgMjgzLjc5LCAzMDUuODMsIDQxNy40LCA0NDUuNzUsIDU3NS42MywgNjUyLjM2LCA2OTAuNywgNzU1LjkxLCA3NzIuMTgsIDkwMy43NCwgOTY4LjIzLCAxMDA3LjgxLCAxMTMwLjEyLCAxMTgyLjg3LCAxMjM1LjMxLCAxMzE3Ljg5LCAxMzgwLjAzLCAxNDQ4Ljk3LCAxNDg5LjAxLCAxNTgzLjI5XSwgIkFrdHVlbGxlIFp3aXNjaGVuemVpdGVuIjogW10sICJCZXN0ZSBTZWdtZW50ZSI6IFtbMTkzLjU0LCAzNTkuNjYsIDMyOC4xMSwgMjA0LCAxODcuMDksIDI2NS4yNl0sIFszNy4xNSwgMTguNiwgNDMsIDI2LCA2My4xNCwgODYuODksIDE4LjksIDk0LjksIDI4LjI1LCAxMTcuNTYsIDc2LjczLCAzOC4zNCwgNjMuMzEsIDE1LCAxMzEuNTYsIDYwLjMzLCAzMy41LCAxMDcuOTYsIDUyLjc1LCA0OS4wOCwgODIuNTgsIDYyLjE0LCA2NC4zLCAzOS40OSwgODBdLCBbXSwgW10sIFtdLCBbXSwgW10sIFtdLCBbXSwgW11dLCAiU3BpZWxuYW1lIjogIlNvbmljIFRoZSBIZWRnZWhvZyBHZW5lc2lzIChHQkEgLSBVU0EgVmVyc2lvbikiLCAiRHVyY2hsYXVma2F0ZWdvcmllIjogIltUYWcgMDAxMzldIEFsbGUgU3RlaW5lIChpbSBKdWJpbFx1MDBlNHVtc21vZHVzKSIsICJTZWdtZW50bmFtZW4iOiBbIi1Ba3QgMTogV2FzIGZcdTAwZmNyIGVpbiBzY2h3ZXJlciBBbmZhbmchIiwgIi1TcGV6aWFsIDE6IEVzIGdlaHQgc2NobmVsbCB3aWVkZXIgd2VnIiwgIi1Ba3QgMjogV2lsbCBkZW4gTW90b2J1ZyBuaWNodCB0XHUwMGY2dGVuLiIsICItU3BlemlhbCAyOiBEaWVzZXMgVGltaW5nLi4uIiwgIlx1MjY0MFx1ZDgzY1x1ZGZjMCAwMC4wOCAqUkVTRVQtKlR1cm5oYWxsZSBbTm9ybWFsXXxBa3QgMzogQml0dGUga2VpbmUgVHJlZmZlciB2ZXJmZWhsZW4hIiwgIi1Ba3QgMTogRElFIFpZS0xFTiEiLCAiLVNwZXppYWwgMzogU1BSSU5HISIsICItQWt0IDI6IEJpdHRlIG5pY2h0IGdldHJvZmZlbiB3ZXJkZW4hIiwgIi1TcGV6aWFsIDQ6IFZlcm1hc3NlbCBkYXMgbmljaHQuIiwgIlx1MjY0Mlx1ZDgzY1x1ZGY3MyAwMC4yNSBIYXVwdGtcdTAwZmNjaGUgZGVyIFNjaHVsZXxBa3QgMzogR2VmXHUwMGU0aHJsaWNoZXMgRW5kZSBlaW5lciBab25lIiwgIi1Ba3QgMTogTk9DSCBFSU4gWllLTFVTISIsICItU3BlemlhbCA1OiBNRUlORSBHUlx1MDBkNlNTVEUgU0NIV1x1MDBjNENIRSBET1JUISIsICItQWt0IDI6IEVUV0FTIEhFSUtMSUchIiwgIi1TcGV6aWFsIDY6IFNQUklORyEhIiwgIlx1MjY0MFx1ZDgzY1x1ZGZmMCAwMC4wOCBUdXJuaGFsbGUgW0FrdD1IXHUwMGZjcGZidXJnXXxBa3QgMzogSEVJS0xJRyBBTSBBTkZBTkchIiwgIi1Ba3QvV2FzY2hiZWNrZW4gMTogV2Fzc2VycGh5c2lrISIsICItQWt0L1dhc2NoYmVja2VuIDI6IE5cdTAwZmN0emxpY2hlciBTcHJ1bmdmZWRlciEiLCAiXHUyNjQyXHVkODNkXHVkZWJmIDAwLjExIFR1cm5oYWxsZS1VbWtsZWlkZXJhdW18QWt0L1dhc2NoYmVja2VuIDM6IFBBUktPVVJaRUlUISIsICItQWt0IDE6IFNpZSBzY2hhdWVuIGRhIGVpbiBndXRlbiBGaWxtIiwgIi1Ba3QgMjogU2llIHNjaGF1ZW4gc2ljaCBnZXJhZGUgXHUyMDFlR29sZGVuXHUyMDFjIGFuLiIsICJcdTI2NDJcdWQ4M2NcdWRmYWMgMTAuMDUgR3ltbmFzdGlrcmF1bSBbS2lub3JhdW1dfEFrdCAzOiBEaWVzZXIgRmlsbTogS1BvcCBEZW1vbiBIdW50ZXJzIiwgIi1cdWQ4M2RcdWRjY2QgQWt0IDEgW1JhdW1taXR0ZV06IERhIHdpcmQgYXVjaCBGaWxtIGdlc2NoYXV0ISIsICItXHVkODNjXHVkZjczIEFrdCAyIFtLb2NobmlzY2hlKFx1MjE5MyldOiBEYSB3aXJkIGdla29jaHQhIiwgIi1cdWQ4M2RcdWRlYjAgQWt0IDMgW1dhc2NoYmVja2VuXTogU28gaHlnaWVuaXNjaCBzY2hsYXUhIiwgIlx1MjY0MFx1ZDgzY1x1ZGY5MiAxMC4yOCBLbGFzc2VucmF1bSBbU2VodXNhc2NodWxlXXxcdWQ4M2NcdWRmN2QgQk9TUyBbS29jaG5pc2NoZShcdTIxOTEpXTogV0lFREVSIEhFSUtMSUchIl0sICJCZXNjaHJlaWJ1bmciOiBbIlxuTWVpbmUgQmVzY2hyZWlidW5nIGRlcyBEdXJjaGxhdWZzXG5cblxuU3BpZWx2ZXJzaW9uOiBTY2hsZWNodGVzdGUgb2ZmaXppZWxsZSBQb3J0aWVydW5nIGRlcyBTcGllbHNcbi0+IFNpZSBoYWJlbiBlcndhcnRldCwgZGFzcyBkaWVzZSBTcGllbHBvcnRpZXJ1bmcgZ3V0IHdpcmQuXG4tPiBFaW5lIEthdGFzdHJvcGhlLCBtaXQgZGVyIHNpZSBuaWNodCBnZXJlY2huZXQgaGF0dGVuLlxuLT4gRGllc2UgUG9ydGllcnVuZyBiYXNpZXJ0IHNpY2ggYXVmIGVpbmUgYW5kZXJlIFBvcnRpZXJ1bmcuXG4tPiBEYXMgZWlnZW50bGljaGUgU3BpZWwgaGF0IG5peCBtaXQgSG9ycm9yIHp1IHR1bi5cbk1ldGFzY29yZTogMzMvMTAwXG5BbnphaGwgZGVyIFpvbmVuOiA2ICsgMSA9IDdcbkFuemFobCBkZXIgdm9sbHN0XHUwMGU0bmRpZ2VuIFJcdTAwZTR1bWU6IDVcblJhdW1udW1tZXJuLCBHZXNjaGxlY2h0IHVuZCBOYW1lbiBkaWVzZXIgUlx1MDBlNHVtZTpcblx1MjVjZiAwMC4wOCBUdXJuaGFsbGUgW3dlaWJsaWNoXVxuXHUyNWNmIDAwLjI1IEhhdXB0a1x1MDBmY2NoZSBbbVx1MDBlNG5ubGljaF1cblx1MjVjZiAwMC4xMSBUdXJuaGFsbGUtVW1rbGVpZGVyYXVtIFttXHUwMGU0bm5saWNoXVxuXHUyNWNmIDEwLjA1IEd5bW5hc3Rpa3JhdW0gW21cdTAwZTRubmxpY2hdXG5cdTI1Y2YgMTAuMjggS2xhc3NlbnJhdW0gW3dlaWJsaWNoXVxuXG5TcGllbHJlaWhlbmZvbGdlIGRlciBhbmdlZ2ViZW5lbiBSXHUwMGU0dW1lOlxuXHUyNWNmIFR1cm5oYWxsZSAoTm9ybWFsKSAtPiBIYXVwdGtcdTAwZmNjaGUgLT4gVHVybmhhbGxlIChIXHUwMGZjcGZidXJnZW4pIC0+IFR1cm5oYWxsZS1VbWtsZWlkZXJhdW0gLT4gR3ltbmFzdGlrcmF1bSAtPiBLbGFzc2VucmF1bSAtPiBLbGFzc2VucmF1bSAoQk9TUylcblxuQW56YWhsIGRlciBTcGV6aWFsLUJveGVuOiA2XG4gICAgICAgICIsICJcbkljaCBiZXNjaHJlaWJlIGRpZXNlbiBMYXVmIGZvbGdlbmRlcm1hXHUwMGRmZW46XG5cblxuRGllIGVyc3RlIFpvbmUgYmVmaW5kZXQgc2ljaCBpbiBkZXIgVHVybmhhbGxlLlxuU2llIGJlZ3JcdTAwZmNcdTAwZGZ0IGRlbiBIZWxkIG1pdCB2aWVsIEJld2VndW5nc2ZyZWloZWl0LlxuXG5OYWNoZGVtIGVyIGRlbiBTY2hsZWNodGVuIGluIGRlciBlcnN0ZW4gWm9uZSBiZXNpZWd0IGhhdCwgZlx1MDBmY2xsdCBkZXIgSGVsZCBlaW4gZ3JvXHUwMGRmZW4gSHVuZ2VyLCBkYXNzIGVyIG5pY2h0IG1laHIgYXVzaGFsdGVuIGthbm4uXG5EaWUgendlaXRlIFpvbmUgYmVmaW5kZXQgc2ljaCBpbiBkZXIgSGF1cHRrXHUwMGZjY2hlLlxuRXIgZW50aFx1MDBlNGx0IGRyZWkgS1x1MDBmY2NoZW56ZWlsZW4sIHdvYmVpIGplZGVyIEFrdCBlaW5lIEtcdTAwZmNjaGVuemVpbGUgZGFyc3RlbGx0LlxuT2ggTmVpbiEgRGVyIEhlbGQgaGF0IHdhaHJzY2hlaW5saWNoIGVpbmVuIEZlaGxlciBnZW1hY2h0LlxuRG9ydCBzb2xsIGVyIHZlcnN1Y2hlbiBkaWUgaGVpXHUwMGRmZSBUZW1wZXJhdHVyZW4gYXVzenV3ZWljaGVuLlxuXG5EZXIgSGVsZCBiZWtvbW10IGVzIG51biBtaXQgZGVyIEhpdHplIHp1IHR1bi5cbkRlc2hhbGIgcmVubnQgZXIgenVyXHUwMGZjY2sgaW4gZGllIFR1cm5oYWxsZSBcdTIwMTMgZG9ydCBiZWZpbmRldCBzaWNoIGF1Y2ggZGllIGRyaXR0ZSBab25lIFx1MjAxMywgZG9jaCBlciBhaG50IG5pY2h0LCBkYXNzIGRpZSBMZWhyZXIgZ2VwbGFudCBoYWJlbiwgc2llIHp1IHZlcndhbmRlbG4sIGluZGVtIHNpZSBkcmVpIEhcdTAwZmNwZmJ1cmdlbiBpbiBpaHJlbSBJbm5lcmVuIGF1ZmJsYXNlbiwgd1x1MDBlNGhyZW5kIGVyIHNpY2ggbm9jaCBpbiBkZXIgSGF1cHRrXHUwMGZjY2hlIGF1ZmhcdTAwZTRsdFxuTnVuIG11c3MgZXIgZGllc2UgSFx1MDBmY3BmYnVyZ2VuIGJldHJldGVuLiBKZWRlciBkb3J0aWdlIEFrdCBlbnRzcHJpY2h0IGVpbmVyIEhcdTAwZmNwZmJ1cmcuXG5TaWUgaGFiZW4gc2llIHZvbiBlaW5lbSBmcmllZGxpY2hlbiBSYXVtIGluIGVpbmVuIHBvdGVuemllbGwgYlx1MDBmNnNlbiBPcnQgdmVyd2FuZGVsdCwgZGVyIGRlbSBIZWxkZW4gd29tXHUwMGY2Z2xpY2ggXHUwMGZjYmxlIFN0cmVpY2hlIHNwaWVsdCBbei5CLiBtXHUwMGY2Z2xpY2hlIHVuZXJ3YXJ0ZXRlIFRvZGVzc3RlbGxlbl0uXG4iLCAiXG5EYSBkaWUgVHVybmhhbGxlIG51biBlaW5lIGJlZHJvaGxpY2hlIEF1c3N0cmFobHVuZyBoYXQsIHdpcmQgc2llIGRlbiBIZWxkZW4gXHUyMDEzIG5hY2hkZW0gZXIgZGVuIEJcdTAwZjZzZXdpY2h0IGluIGlocmVtIElubmVyZW4gZXJuZXV0IGJlc2llZ3QgaGF0IFx1MjAxMyBkaXJla3QgaW4gZWluZXIgc2VpbmVyIFVta2xlaWRlclx1MDBlNHVtZSBzY2hpY2tlbjsgZG9ydCBiZWZpbmRldCBzaWNoIGRpZSB2aWVydGUgWm9uZS5cbkluIGRpZXNlbSBSYXVtIHN0ZWhlbiBkcmVpIFdhc2NoYmVja2VuLCBkaWUgZGVyIEhlbGQgcGFzc2llcmVuIG11c3MsIHVtIGluIGRlbiBuXHUwMGU0Y2hzdGVuIFJhdW0genUgZ2VsYW5nZW47IGRhYmVpIHN0ZWh0IGplZGVzIGRlciBXYXNjaGJlY2tlbiBmXHUwMGZjciBlaW5lbiBkZXIgZG9ydGlnZW4gQWt0LlxuSmVkZXIgZGllc2VyIGRyZWkgV2FzY2hiZWNrZW4gc2luZCBtaXQgV2Fzc2VyIGdlZlx1MDBmY2xsdC4gRGVyIEhlbGQga2FubiBkZW4gQXRlbSBudXIgMzAgU2VrdW5kZW4gbGFuZyBhbmhhbHRlbiwgYmV2b3IgZXIgZGVuIFdhc3NlcnRvZCBzdGlyYnQuXG5cbk5hY2hkZW0gZXIgYXVzIGRlbSBVbWtsZWlkZXJhdW0gZW50a29tbWVuIGlzdCwgYmV0cml0dCBlciBlaW5lbiBmcmllZGxpY2hlbiBSYXVtLCBkZXIgR3ltbmFzdGlrcmF1bS4gSGllciBiZWZpbmRldCBzaWNoIGRpZSBmXHUwMGZjbmZ0ZSBab25lLlxuV1x1MDBlNGhyZW5kIHNpY2ggZGVyIEhlbGQgZG9ydCBhdWZoXHUwMGU0bHQsIHNjaGF1ZW4gc2ljaCBkaWUgQW53ZXNlbmRlbiBnZXJhZGUgZWluZW4gZ3V0ZW4gRmlsbSBuYW1lbnMgXHUyMDFlS1BvcCBEZW1vbiBIdW50ZXJzXHUyMDFjIGFuLlxuIiwgIlxuTmFjaGRlbSBlciBkZW4gQlx1MDBmNnNld2ljaHQgaW0gR3ltbmFzdGlrcmF1bSBiZXNpZWd0IGhhdCwgZXJyZWljaHQgZXIgZGFzIEtsYXNzZW56aW1tZXIsIGluIGRlbSBzaWNoIGRpZSBsZXR6dGVuIGJlaWRlbiBab25lbiBiZWZpbmRlbi5cblxuVm9uIGF1XHUwMGRmZW4gd2lya3Qgc2llIHVuc2NodWxkaWcgdW5kIHZvbiBpbm5lbiBnZW1cdTAwZmN0bGljaCwgZG9jaCBzaWUgYmlyZ3QgaWhyZSBlaWdlbmVuIEZhbGxlbiwgZGllIGRlbSBIZWxkZW4gbmFjaCBkZW0gTGViZW4gdHJhY2h0ZW4uXG5cbkluIEFrdCAxIGJlbWVya3QgZGVyIEhlbGQsIGRhc3MgZGllIExldXRlIGluIGlocmVtIElubmVyZW4gZWluZW4gRmlsbSBhbnNlaGVuLiBEaWVzZXIgRmlsbSBlbnRoXHUwMGU0bHQgemFobHJlaWNoZSBHZXJcdTAwZTR1c2NoZSB2b24gemVyYnJlY2hlbmRlbSBHbGFzLCBkaWUgbGF1dCBpbiBpaHIgYWJnZXNwaWVsdCB3ZXJkZW4uXG5JbiBBa3QgMiBiZW1lcmt0IGRlciBIZWxkLCBkYXNzIGluIGlocmVtIElubmVyZW4gYXVjaCBnZWtvY2h0IHdpcmQgXHUyMDEzIHNpZSB2ZXJmXHUwMGZjZ3QgYWxzbyBcdTAwZmNiZXIgZWluZSBLb2NobmlzY2hlLiBFciBiZWZpbmRldCBzaWNoIGRvcnQgaW0gdW50ZXJlbiBCZXJlaWNoIGRpZXNlciBLb2NobmlzY2hlIGF1Zi5cbkluIEFrdCAzIFx1MDBmY2JlcnJhc2NodCBzaWUgZGVuIEhlbGRlbiwgaW5kZW0gc2llIGlobiBpbiBlaW4gd2VpdGVyZXMgV2FzY2hiZWNrZW4gYmVmXHUwMGY2cmRlcnQgXHUyMDEzIHNpZSB2ZXJmXHUwMGZjZ3QgYWxzbyBcdTAwZmNiZXIgZWluIFdhc2NoYmVja2VuLlxuTmFjaGRlbSBkZXIgSGVsZCBkaWVzZW0gV2FzY2hiZWNrZW4gZW50a29tbWVuIGlzdCwgc3RlbGx0IGVyIHNpY2ggZGVtIGVpZ2VudGxpY2hlbiBCb3Nza2FtcGYgZ2VnZW4gc2llLlxuRGVyIEhlbGQgYmVmaW5kZXQgc2ljaCBpbW1lciBub2NoIGltIEtsYXNzZW5yYXVtLiAgRXIgYmVmaW5kZXQgc2ljaCBkb3J0IGltIG9iZXJlbiBCZXJlaWNoIHNlaW5lciBLb2NobmlzY2hlIGF1Zi5cblxuTmFjaGRlbSBkZXIgSGVsZCBkZW4gQm9zcyBpbiBpaHJlbSBJbm5lcmVuIGJlc2llZ3QgaGF0LCBrZWhydCBlciBpbiBkaWUgVHVybmhhbGxlIFtkb3J0IHdpcmQgZWluZSBBYnNjaGx1c3NmZWllciBnZWZlaWVydF0genVyXHUwMGZjY2sgKGRpZSB3aWVkZXIgaWhyZW4gTm9ybWFsenVzdGFuZCBhbmdlbm9tbWVuIGhhdCksIGxcdTAwZTRzc3QgZGllIFN0ZWluZSBcdTIwMGJcdTIwMGJcdTAwZmNiZXIgc2ljaCBzY2h3ZWJlbiB1bmQgdm9sbGZcdTAwZmNocnQgYW5zY2hsaWVcdTAwZGZlbmQgZWluZW4gU2llZ2Vyc3BydW5nLlxuRGFtaXQgZW5kZXQgZGllIEdlc2NoaWNodGUuXG4iLCAiXG5GcmFnZTogV2llIGdlbGFuZ3QgbWFuIGluIGRpZXNlIFNwZXppYWwtQm94ZW4/IFxuQW50d29ydDogRHVyY2ggSGluZWluc3ByaW5nZW4gaW4gZGVuIHJpZXNpZ2VuIFJpbmcgYW0gRW5kZSB2b24gQWt0IDEgdW5kL29kZXIgMiwgamVkZXIgWm9uZSBbZlx1MDBmY3IgbVx1MDBlNG5ubGljaCB1bmQgd2VpYmxpY2hdLCB3ZW5uIGR1IG1pbmRlc3RlbnMgNTAgRWluaGVpdGVuIGVpbmVyIFdcdTAwZTRocnVuZyBoYXN0LCBiZXZvciBkdSBkYXMgS2xhc3NlbnppbW1lciBlcnJlaWNodHMuXG5GYWt0OiBEYXMgZ3V0ZSBFbmRlIGxcdTAwZTRzc3Qgc2ljaCBlcnJlaWNoZW4sIGluZGVtIG1hbiBkZW4gQm9zcyBpbSBLbGFzc2VuemltbWVyIGJlc2llZ3QsIG5hY2hkZW0gYWxsZSBTcGV6aWFsLUJveGVuIGVyZm9sZ3JlaWNoIGFic29sdmllcnQgd3VyZGVuLlxuICAgICAgICBcbldlbm4gZHUgaW0gZWlnZW50bGljaGVuIFNwaWVsIEdsYXMgemVyYnJpY2hzdCwgemVyYnJpY2hzdCBkdSBhdWNoIEdsYXMgaW4gZGVtIGVudHNwcmVjaGVuZGVuIFJhdW0gKGJhc2llcmVuZCBhdWYgZGVyIGpld2VpbGlnZW4gWm9uZSkuXG5EdSBrYW5uc3QgZWluZW4gUmF1bSBrb21wbGV0dCB2ZXJ3XHUwMGZjc3Rlbiwgd2VubiBkdSBcdTIwMWVqZWRlcyBlaW56ZWxuZVx1MjAxYyBHbGFzb2JqZWt0IGluIGRlci9kZW4gZW50c3ByZWNoZW5kZW4gWm9uZShuKSAoZ2VtXHUwMGU0XHUwMGRmIEJlc2NocmVpYnVuZykgemVyYnJpY2hzdC5cbkJlc29uZGVyaGVpdDogSW0gdm9sbHN0XHUwMGU0bmRpZ2VuIFNwaWVsZHVyY2hsYXVmIGthbm5zdCBkdSBkaWUgVHVybmhhbGxlIHRhdHNcdTAwZTRjaGxpY2ggendlaW1hbCB2ZXJ3XHUwMGZjc3Rlbi5cblxuV2VubiBkdSBiZW1lcmtzdCwgZGFzcyBkYXMgU3BpZWwgcnVja2VsdCwgYmVkZXV0ZXQgZGFzLCBkYXNzIGR1IGRlbiBBdGVtIGVpbmVzIHdlaWJsaWNoZW4gUmF1bXMgc3BcdTAwZmNyZW4ga1x1MDBmNm5udGVzdC5cbiAgICAgICAgIiwiU2VpdCBkZW0gMjIuIE1haSAyMDIwIGlzdCBkZXIgU3BpZWx0b24gZXJmb3JkZXJsaWNoIHVuZCBtdXNzIHfDpGhyZW5kIGRlcyBnZXNhbXRlbiBSdW5zIGluIGjDtnJiYXJlciBMYXV0c3TDpHJrZSB2b3JoYW5kZW4gc2Vpbi5cblxuUmVnZWxuIGbDvHIgRW11bGF0b3JlbiAoU3RhbmQ6IDcuIERlemVtYmVyIDIwMjApOlxuRGVyIHZlcndlbmRldGUgRW11bGF0b3IgbXVzcyBhbiBpcmdlbmRlaW5lbSBQdW5rdCBkZXMgUnVucyAodm9yenVnc3dlaXNlIHp1IEJlZ2lubikgZWluZGV1dGlnIGVya2VubmJhciBzZWluIHVuZCBtdXNzIG1pdCB2b2xsZXIgR2VzY2h3aW5kaWdrZWl0IGxhdWZlbi5cblxuUmVnZWxuIGRlciBGdWxsLUdhbWUtS2F0ZWdvcmllOlxuRGllIFplaXRtZXNzdW5nIGVyZm9sZ3QgaW4gRWNodHplaXQgdW5kIGJlZ2lubnQgbWl0IGRlciBBdXN3YWhsIHZvbiDigJ5UdXJuaGFsbGUgKE5vcm1hbCnigJwgdW5kIGVuZGV0IG1pdCBkZXIgU2Nod2FyemJsZW5kZSBuYWNoIGRlbSBCT1NTIGltIEtsYXNzZW5yYXVt4oCcXG5SZWdlbCBkZXIgIOKAnkFsbGUgU3RlaW5l4oCcIEthdGVnb3JpZTpcbkRpZXNlIEthdGVnb3JpZSBzb2xsdGUgYW0gYmVzdGVuIGltIFJhaG1lbiBlaW5lcyBGdWxsLUdhbWUtUnVucyBhYnNvbHZpZXJ0IHdlcmRlbi5cbkR1IG11c3N0IHZlcnN1Y2hlbiwgZGllIFN0ZWluZSDigIvigIthdXMgYWxsZW4gU3BlemlhbGtpc3RlbiB6dSBob2xlbi5cbldlbm4gZHUgYXVjaCBudXIgZWlubWFsIHNjaGVpdGVyc3QsIHN0YXJ0ZXN0IGR1IGRlbiBEdXJjaGxhdWYgYW0gYmVzdGVuIG5ldS4iXX0=

"""
