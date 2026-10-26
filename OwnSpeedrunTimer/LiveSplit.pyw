from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
from datetime import datetime
from typing import Any, Iterable, List, Optional, Sequence, Tuple
from itertools import zip_longest

import time
import tkinter as tk
from tkinter import ttk, filedialog
import keyboard
import json
from base64 import b64encode, b64decode

# =========================
# Utility functions
#
# 28.09.2026
# [630, 20, 4804, 178, 4804, 178, 3760]
# =========================

def safe_float(x):
    try:
        return float(x)
    except ValueError:
        return None

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
    if type(x) not in (float, int): return "-----.--"
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
    if ind is None:
        return default
    if ind < 0 and "restr_neg_ind" in args:
        return default
    try:
        return _list[ind]
    except IndexError:
        return default

def validate_float(new_value):
    # Allow empty string (when user deletes everything)
    if new_value == "":
        return True
    # Allow a single minus sign or dot while typing
    if new_value in ("-", ".", "-.") or "|" in new_value:
        return True
    try:
        [float(e or 0) for e in new_value.split(",")]
        return True
    except ValueError:
        return False

# =========================
# Flexible List Class
# =========================

class FlexList:
    def __init__(*args):
        self.list = [*args]

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

import tkinter as tk
from tkinter import ttk


class ChildWindow:
    def __init__(self,parent = None,**kwargs) -> None:
        self.parent = parent
        self.type = kwargs.get("type")

        self.root = tk.Tk()
        self.root.option_add("*Background", "black")
        self.root.option_add("*Foreground", "white")

        match self.type:
            case "LOGS":
                self.setup_log_history_window()
            case "LOGS ORG":
                self.setup_log_history_window_original()
            case "EDIT SPLITS":
                self.setup_edit_splits_window()
            case "ANALYZER":
                self.setup_potential_analyzer_window()
            case "POST-RUN ANALYZER":
                self.setup_post_run_analyzer_window()
            case _:
                self.setup_description_window()

    def setup_post_run_analyzer_window(self):
        self.root.title("Der Nachrun-Analysator")
        self.root.geometry("500x300")
        self.root.grid_rowconfigure(0,weight=1)
        self.root.grid_columnconfigure(0,weight=1)
        root = self.root

        self.canvas = tk.Canvas(root, width=500, height=300, scrollregion=(0,0,1000000,1000000))
        canvas = self.canvas
        scrollbarY = tk.Scrollbar(root, orient="vertical",command=canvas.yview)
        scrollbarX = tk.Scrollbar(root, orient="horizontal",command=canvas.xview)

        canvas.configure(yscrollcommand=scrollbarY.set,xscrollcommand=scrollbarX.set)
        canvas.grid(row=0,column=0,sticky="nsew")
        scrollbarY.grid(row=0,column=1,sticky="ns")
        scrollbarX.grid(row=1,column=0,sticky="ew")
        
        frame = tk.Frame(canvas)
        canvas.create_window((0,0),window=frame,anchor="nw")

        frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        parent = self.parent
        split_times = parent.split_times
        best_segs = parent.best_segs
        seg_names = parent.seg_names
        seg_order = parent.seg_order
        seg_categories = parent.seg_categories
        latest_segs = parent.latest_splits

        if latest_segs:
            latest_seg_times =  [
                latest_segs[i]-(
                    0 if i == 0 else latest_segs[i-1]
                ) for i in range(len(latest_segs))
                ]

        seg_category_times = {}
        seg_total_time = 0
        self.seg_category_buckets = []
        for i,seg in enumerate(seg_order):
            depth_ind = seg[0]
            _range = seg[1]
            category = seg_categories[depth_ind[0]][depth_ind[1]]
            try:
                time = el_by_ind(latest_segs,_range[1])-el_by_ind(latest_segs,_range[0]-1,"restr_neg_ind",default=0)
            except TypeError:
                time = None
            self.seg_category_buckets.append((category, time, _range))


        for category,time,_ in self.seg_category_buckets:
            for cate in category.split(","):
                try:
                    if not cate in seg_category_times:
                        seg_category_times[cate] = time
                    else:
                        seg_category_times[cate] += time
                except (ValueError,TypeError):
                    seg_category_times[cate] = None

        def get_total_time(exclude_inds=[]):
            total_time = 0

            for i,time in enumerate(latest_seg_times):
                try:
                    if i not in exclude_inds:
                        total_time += time
                except ValueError:
                    total_time = None
            return total_time

            
        
        self.text_id = canvas.create_text(
                (10, 30), font=("Consolas",15),
                text=f"Gezählte Zeit: {formatA(get_total_time())} Sek.",
                fill="white",
                anchor="w"
                )

        def print_selection(seg):
            depth_ind = json.dumps(seg[0])
            _range = seg[1]
            subsegs = []
            checkbox_bool = self.checkbox_vars[depth_ind].get()
            
            print(seg_order)
            lookup_depth_inds = [
            e for e in seg_order if (
            e[1][0] >= _range[0] and (e[1][1] <= _range[1] or e[0][0] < seg[0][0])
            )
            ]
           
            #print("KWLP",[
            #(e[1], e[1][0] >= _range[0],e[1][1] <= _range[1]) for e in seg_order
            #])
           
            print("----------------")
            print(lookup_depth_inds)
            print("BOMBARDINO TORTILLA",[
            (e[0], self.checkbox_vars.get(json.dumps(e[0])).get()) for e in lookup_depth_inds
            ])

            print(depth_ind,_range, checkbox_bool)
            print("----------------")
            
        #    exclusion = []
        #    for e in self.vars:
        #        _bool = self.vars[e].get()
        #        if _bool:
        #            exclusion.append(e)
        #    self.canvas.itemconfig(self.text_id, text=f"Gezählte Zeit: {formatA(get_total_time(exclusion))} Sek.")            
        #        
        #
        #canvas.create_text(
        #        (10, 60), font=("Consolas",10),
        #        text=f"Die Zeit wurde von den folgenden Segmente gezählt:",
        #        fill="white",
        #        anchor="w"
        #        )
        #self.collapse_btns = {}
        
        def forgamisso(depth_ind,info):
            btn_id = self.collapse_btn_ids[depth_ind]
            btn = canvas.nametowidget(canvas.itemcget(btn_id,"window"))
            btn_tag = canvas.gettags(btn_id)[0]
            
            var = self.collapse_btn_vars[depth_ind]
            new_seg_depth = info[0][0]+1
            seg_range = info[1]
            
            targeted_segs = [
            e for e in seg_order if e[0][0]==new_seg_depth and e[1][0] >= seg_range[0] and e[1][1] <= seg_range[1]
                ]   
            
            if var:
                btn["text"]="▲"
                self.collapse_btn_vars[depth_ind] = False
                remove_segs(targeted_segs,  int(btn_tag[11:])  )
            else:
                btn["text"]="▼"
                self.collapse_btn_vars[depth_ind] = True
                insert_segs(targeted_segs,  int(btn_tag[11:]),depth_ind  )
                
        def insert_segs(segs,index,depth_inda):
            no_of_segs = len(segs)
            
            for i in range(self.seg_count,index,-1):
                matching_itemA = self.canvas.find_withtag(f"SegListSeg{i}")
                matching_itemB = self.canvas.find_withtag(f"CollapseBtn{i}")
                # 3. Check if the item exists and use its ID
                if matching_itemA:
                    item_id = matching_itemA[0]
                    self.canvas.move(item_id, 0, 20*no_of_segs)
                    self.canvas.itemconfig(item_id, tags=f"SegListSeg{i+no_of_segs}")
                # 3. Check if the item exists and use its ID
                if matching_itemB:
                    item_id = matching_itemB[0]
                    self.canvas.move(item_id, 0, 20*no_of_segs)
                    self.canvas.itemconfig(item_id, tags=f"CollapseBtn{i+no_of_segs}")
            
            depth_inda= json.loads(depth_inda)
            for i,e in enumerate(segs, index+1 ):
                depth_ind = json.dumps(e[0])
                #self.checkbox_vars[depth_ind]=tk.BooleanVar(
                #master=self.root,value=True
                #)
                checkbox = new_checkbox(e)
                win_id = canvas.create_window( (40+10*depth_inda[0],60+20*i), tags=f"SegListSeg{i}", window=checkbox, anchor="nw")
            
                if e[1][0] != e[1][1]:
                    collapse_btn = new_collapse_btn(depth_ind,e)
                    self.collapse_btn_vars[depth_ind] = False
                    self.collapse_btn_ids[depth_ind]=canvas.create_window( (20+10*depth_inda[0],65+20*i), tags=f"CollapseBtn{i}", window=collapse_btn, anchor="nw")
                    
            self.seg_count+=no_of_segs
                    
        def remove_segs(segs,index):
            no_of_segs = len(segs)
            bonito = index+no_of_segs+1
            
            for i in range(index+1,bonito):
                self.canvas.delete(f"SegListSeg{i}")
                self.canvas.delete(f"CollapseBtn{i}")
            for i in range(bonito,self.seg_count+1):
                matching_itemA = self.canvas.find_withtag(f"SegListSeg{i}")
                matching_itemB = self.canvas.find_withtag(f"CollapseBtn{i}")
                # 3. Check if the item exists and use its ID
                if matching_itemA:
                    item_id = matching_itemA[0]
                    self.canvas.move(item_id, 0, -20*no_of_segs)
                    self.canvas.itemconfig(item_id, tags=f"SegListSeg{i-no_of_segs}")
                # 3. Check if the item exists and use its ID
                if matching_itemB:
                    item_id = matching_itemB[0]
                    self.canvas.move(item_id, 0, -20*no_of_segs)
                    self.canvas.itemconfig(item_id, tags=f"CollapseBtn{i-no_of_segs}")
            self.seg_count-=no_of_segs
            
            
   
        #self.vars = [tk.BooleanVar(master=canvas,value=True) for i in range(len(
        #seg_order#seg_names
        #))]
        
        new_collapse_btn = lambda x,info=None: tk.Button (
            master=canvas, text="▲", font=("Consolas",7), command=lambda: forgamisso(x,info)
        )
        new_checkbox = lambda e: tk.Checkbutton(
            canvas, text=e[2], font=("Consolas",10), variable=self.checkbox_vars[json.dumps(e[0])], command=lambda: print_selection(e)
            )
        self.collapse_btn_ids = {}
        self.collapse_btn_vars = {}
        self.checkbox_vars = {}
        self.seg_inclusion_vars = [True for i in range(len(seg_names))]
        
        segs_to_put = [e for e in seg_order if e[0][0] == 0]
        self.seg_count = len(segs_to_put)

        for e in seg_order:
            depth_ind = json.dumps(e[0])
            self.checkbox_vars[depth_ind]=tk.BooleanVar(master=self.root,value=True)
            

        for i,e in enumerate(segs_to_put, 1):
            depth_ind = json.dumps(e[0])
            #self.checkbox_vars[depth_ind]=tk.BooleanVar(master=self.root,value=True)
            checkbox = new_checkbox(e)
            canvas.create_window( (30,60+20*i), tags=f"SegListSeg{i}", window=checkbox, anchor="nw")
            
            if e[1][0] != e[1][1]:
                collapse_btn = new_collapse_btn(depth_ind,e)
                self.collapse_btn_vars[depth_ind] = False
                self.collapse_btn_ids[depth_ind]=canvas.create_window( (10,65+20*i), tags=f"CollapseBtn{i}", window=collapse_btn, anchor="nw")

    def setup_potential_analyzer_window(self):
        self.root.title("Der Datenanalysator")
        self.root.geometry("500x300")
        self.root.grid_rowconfigure(0,weight=1)
        self.root.grid_columnconfigure(0,weight=1)
        root = self.root

        canvas = tk.Canvas(root, width=500, height=300, scrollregion=(0,0,1000000,1000000))
        scrollbarY = tk.Scrollbar(root, orient="vertical",command=canvas.yview)
        scrollbarX = tk.Scrollbar(root, orient="horizontal",command=canvas.xview)
        canvas.configure(yscrollcommand=scrollbarY.set,xscrollcommand=scrollbarX.set)
        canvas.grid(row=0,column=0,sticky="nsew")
        scrollbarY.grid(row=0,column=1,sticky="ns")
        scrollbarX.grid(row=1,column=0,sticky="ew")
        
        frame = tk.Frame(canvas)
        canvas.create_window((0,0),window=frame,anchor="nw")

        frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        split_times = self.parent.split_times
        best_segs = self.parent.best_segs
        seg_names = self.parent.seg_names
        seg_order = self.parent.seg_order
        latest_segs = self.parent.latest_splits
        seg_times =  [
            split_times[i]-(
                0 if i == 0 else split_times[i-1]
            ) for i in range(len(split_times))
            ]
        latest_seg_times = None
        if latest_segs:
            latest_seg_times =  [
                latest_segs[i]-(
                    0 if i == 0 else latest_segs[i-1]
                ) for i in range(len(latest_segs))
                ]
        sdi = [e for e in seg_order if e[1][0]==e[1][1]]
        chains = [
            [e[2] for e in seg_order if i in range(e[1][0],e[1][1]+1)
             ] for i in range(len(seg_names))]
        chains = [" → ".join(chain) for chain in chains]

        best_seg_times = []
        for di in sdi:
            di = di[0]
            while len(best_segs) <= di[0]:
                best_segs.append([])
            while len(best_segs[di[0]]) <= di[1]:
                best_segs[di[0]].append(None)
            best_seg_times.append(best_segs[di[0]][di[1]])
        differencesA = [safe_float(a-b) for a,b in zip(seg_times,best_seg_times)]

        self.analysator_info_id = canvas.create_text((10, 50), font=("Consolas",9), fill="white", anchor="w")
        self.seg_text_ids = [canvas.create_text((10, 120+40*i), font=("Consolas",10),state="hidden", fill="white", anchor="w") for i in range(len(split_times))]
        self.seg_card_ids = [canvas.create_text((10, 135+40*i), font=("Consolas",10),state="hidden", fill="white", anchor="w") for i in range(len(split_times))]


        def switch_sort():
            if self.way_to_sort == 1:
                self.way_to_sort = -self.way_to_sort
            else: self.way_to_sort += 1
            self.button.configure(
                text="Sortierung: {}".format(["Kleinste → Größte", "Erste → Letzte", "Größte → Kleinste"][self.way_to_sort+1]),
            )
            gouda()

            
        self.way_to_sort = 1
        self.button = tk.Button(canvas,
            text="Sortierung: {}".format(["Kleinste → Größte", "Erste → Letzte", "Größte → Kleinste"][self.way_to_sort+1]),
            font=("Consolas",10),
            command=switch_sort
            )
        self.button_id = canvas.create_window(10, 80, window=self.button, state="hidden", anchor="nw")

        def gouda(sort_type=None):
            sort_id = self.combobox.current()+1
            way_to_sort = self.way_to_sort 
            should_sort = self.way_to_sort != 0

            for _id in [*self.seg_text_ids,*self.seg_card_ids]:
                canvas.itemconfig(_id,state="hidden")

            match sort_id:
                case 1:
                    sort_with = lambda x:-way_to_sort*(x[1] or 0)
                    sort_by = [safe_float(a-b) for a,b in zip(seg_times,best_seg_times or [])]
                case 2:
                    sort_with = lambda x:-way_to_sort*(x[1] or 0)
                    sort_by = [safe_float(b-a) for a,b in zip(seg_times,latest_seg_times or [])]
                case 3:
                    sort_with = lambda x:-way_to_sort*(x[1] or 0)
                    sort_by = [safe_float(b-a) for a,b in zip(best_seg_times,latest_seg_times or [])]
                case 4:
                    sort_with = lambda x:-way_to_sort*(x[1] or 0)
                    sort_by = seg_times
                case 5:
                    sort_with = lambda x:-way_to_sort*(x[1] or 0)
                    sort_by = best_seg_times
                case 6:
                    sort_with = lambda x:-way_to_sort*(x[1] or 0)
                    sort_by = latest_seg_times
                case _:
                    sort_with = lambda x:True
                    sort_by = [safe_float(a-b) for a,b in zip(seg_times,best_seg_times)]

            result = zip_longest(chains,sort_by)
            sorted_result = result

            
            #if should_sort:
            sorted_result = [e for e in sorted(result, key= sort_with) if e[1] is not None]
        
            canvas.itemconfig(self.analysator_info_id,
            text=f"Der Analysator zeigt deine Segmente genauso wie es gefragt wird.\nEr zeigt gerade {len(sorted_result)} von {len(split_times)} Segmente.",
            )

            text_possibilities = [
            lambda x: f"Zeitgewinnpotenzial: {x:.2f} Sek.",
            lambda x: f"Zeitgewinnpotenzial: {x:.2f} Sek.",
            lambda x: f"Zeit gg. die geg. Segmentzetien {'verlor' if x>0 else 'gewonn'}en: {abs(x):.2f} Sek.",
            lambda x: f"Zeit gg. deine Bestzeiten {'verlor' if x>0 else 'gewonn'}en: {abs(x):.2f} Sek.",
            lambda x: f"Zeit im Vergleich der geg. Segmentzeiten gebraucht: {x:.2f} Sek.",
            lambda x: f"Zeit in deinem besten Fall gebraucht: {x:.2f} Sek.",
            lambda x: f"Zeit in diesem Fall gebraucht: {x:.2f} Sek.",
            ]
                
            for i,(name,time) in enumerate(sorted_result):
                seg_text_id = self.seg_text_ids[i]
                seg_card_id = self.seg_card_ids[i]
                canvas.itemconfig(seg_text_id, state="normal", text=f"Name des Segments: {name}")
                if time is not None:
                    time = max(0,time) if sort_id == 1 else time
                    canvas.itemconfig(seg_card_id, state="normal", text=text_possibilities[sort_id](time),
                    fill="white" if sort_id in (1,4,5,6) else ("red" if time>0 else "green"),  anchor="w")
            canvas.itemconfig(self.button_id, state="normal")

            
        choices =  (
            "Wo hast du Zeitgewinnpotential?",
            "Wo hast du gegen die geg. Segmentzeiten Zeitverluste?",
            "Wo hast du gegen deine Bestzeiten Zeitverluste?",
            "Wie lange sind die geg. Segmentzeiten?",
            "Wie lange sind deine Bestzeiten?",
            "Wie lange sind deine Segmentzeiten in diesen Versuch?",
            )
        self.combobox = ttk.Combobox(canvas, values=choices, state="readonly",width=50)
        self.combobox.set("Wo hast du ...")
        self.combobox.bind("<<ComboboxSelected>>", lambda x: gouda(x))
        canvas.create_window(10,5,window=self.combobox, anchor="nw")        

    def setup_edit_splits_window(self):
        self.root.title("Segmente bearbeiten")
        self.root.geometry("500x300")
        self.root.grid_rowconfigure(0,weight=1)
        self.root.grid_columnconfigure(0,weight=1)
        root = self.root
        split_times = self.parent.split_times
        best_segs = self.parent.best_segs
        seg_names = self.parent.seg_names
        seg_categories = self.parent.seg_categories
        self.seg_count = len(seg_names)
        
        self.canvas = tk.Canvas(root, width=500, height=300, scrollregion=(0,0,1000000,1000000))
        canvas = self.canvas
        scrollbarY = tk.Scrollbar(root, orient="vertical",command=canvas.yview)
        #scrollbarX = tk.Scrollbar(root, orient="horizontal",command=canvas.xview)
        canvas.configure(yscrollcommand=scrollbarY.set,
                         #xscrollcommand=scrollbarX.set
                         )
        canvas.grid(row=0,column=0,sticky="nsew")
        scrollbarY.grid(row=0,column=1,sticky="ns")
        #scrollbarX.grid(row=1,column=0,sticky="ew")

        frame = tk.Frame(canvas)
        canvas.create_window((0,0),window=frame,anchor="nw")
        
        name_entries = [
            tk.Entry(canvas, font=("Consolas",7)) for _ in seg_names
            ]
        split_time_entries = [
            tk.Entry(canvas, font=("Consolas",7)) for _ in seg_names
            ]
        best_seg_entries = [
            tk.Entry(canvas, font=("Consolas",7)) for _ in seg_names
            ]
        seg_category_entries = [
            tk.Entry(canvas, font=("Consolas",7)) for _ in seg_names
            ]
        
        self.best_segs_entry = tk.Entry(canvas, font=("Consolas",7))
        self.best_segs_entry.insert(0,b64_lock(self.parent.best_segs))

        for i,(name_entry,split_time_entry, best_seg_entry, seg_category_entry) in enumerate(
            zip(name_entries,split_time_entries,best_seg_entries,seg_category_entries)
            ):
            
            sdi = sorted([e[0] for e in self.parent.seg_order if e[1][1]==i])
            best_seg_text = ""

            for di in sdi:
                while len(best_segs) <= di[0]:
                     best_segs.append([])
                while len(best_segs[di[0]]) <= di[1]:
                    best_segs[di[0]].append(None)
                if best_seg_text != "":
                    best_seg_text += "  |  "
                best_seg_text += str(best_segs[di[0]][di[1]] or -1)

            category_text = ""
            for di in sdi:
                while len(seg_categories) <= di[0]:
                     seg_categories.append([])
                while len(seg_categories[di[0]]) <= di[1]:
                    seg_categories[di[0]].append("Keine")
                if category_text != "":
                    category_text += " | "
                category_text += str(seg_categories[di[0]][di[1]])
                        
            name = el_by_ind(seg_names,i) or ""
            name_entry.insert(0,name)
            timeA = el_by_ind(split_times,i)
            if timeA is not None:
                split_time_entry.insert(0,str(timeA))
            timeB = best_seg_text
            if timeB is not None:
                best_seg_entry.insert(0,str(timeB))
            if category_text != "":
                seg_category_entry.insert(0,str(category_text))
            canvas.create_window(( 10,100+60*i), tags =f"Name{i+1}", window=name_entry, width=300, height=20, anchor="nw")
            canvas.create_window((320,100+60*i), tags=f"Split{i+1}", window=split_time_entry, width=100, height=20, anchor="nw")
            canvas.create_window(( 10,130+60*i), tags=f"Best{i+1}", window=best_seg_entry, width=200, height=20, anchor="nw")
            canvas.create_window((220,130+60*i), tags=f"Category{i+1}", window=seg_category_entry, width=200, height=20, anchor="nw")


        frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_text(
            (10, 40), font=("Consolas",7), text="Hier kommen die beste Segmente", fill="white", anchor="w"
            )
        canvas.create_window(
            (10, 50), tags="BestSegs",window=self.best_segs_entry, width=300, height=20, anchor="nw"
            )

        canvas.create_text(
            (10,90), font=("Consolas",7), text="Name des Segments", fill="white", anchor="w"
            )
        canvas.create_text(
            (320,90), font=("Consolas",7), text="Abschnittszeit", fill="white", anchor="w"
            )

        self.menu = tk.Menu(self.root,tearoff=0)
        self.root.bind("<Button-3>", self.do_popup)
        self.menu.add_command(label = "Änderungen übernehmen", command=self.apply_changes_to_splits)
        self.menu.add_separator()
        self.menu.add_command(
        label = "Segment hinzufügen", command=lambda: self.insert_segs(no_of_segs=1)
        )
        self.menu.add_command(
        label = "Anzahl der Segmente hinzufügen", command=self.insert_segs
        )
        self.menu.add_command(
        label = "Segment entfernen", command=self.remove_seg
        )

    def insert_segs(self, **kwargs):
        no_of_segs = kwargs.get("no_of_segs") or tk.simpledialog.askinteger(
            "Abschnitte Editor","Wie viele Segmente sollen hinzugefügt werden?",minvalue=1, maxvalue=10
            )
        if no_of_segs is None:
            return False
        index = kwargs.get("index") or tk.simpledialog.askinteger(
            "Abschnitte Editor",f"{'Ab' if no_of_segs != 1 else 'Bei'} welchem Index sollen die Segmente hinzugefügt werden?",minvalue=1
            )
        if index is None:
            return False
        index = min(self.seg_count+1,index)
        name_entry=lambda: tk.Entry(self.canvas, font=("Consolas",7))
        split_time_entry =lambda: tk.Entry(self.canvas, font=("Consolas",7), validate="key", validatecommand=(self.root.register(validate_float), '%P'))
        best_segs_entry =lambda: tk.Entry(self.canvas, font=("Consolas",7), validate="key", validatecommand=(self.root.register(validate_float), '%P'))
        seg_category_entry =lambda: tk.Entry(self.canvas, font=("Consolas",7), validate="key", validatecommand=(self.root.register(validate_float), '%P'))

        for i in range(self.seg_count,index-1,-1):
            matching_itemA = self.canvas.find_withtag(f"Split{i}")
            matching_itemB = self.canvas.find_withtag(f"Name{i}")
            matching_itemC = self.canvas.find_withtag(f"Best{i}")
            matching_itemD = self.canvas.find_withtag(f"Category{i}")
            # 3. Check if the item exists and use its ID
            if matching_itemA:
                item_id = matching_itemA[0]
                self.canvas.move(item_id, 0, 60*no_of_segs)
                self.canvas.itemconfig(item_id, tags=f"Split{i+no_of_segs}")
            # 3. Check if the item exists and use its ID
            if matching_itemB:
                item_id = matching_itemB[0]
                self.canvas.move(item_id, 0, 60*no_of_segs)
                self.canvas.itemconfig(item_id, tags=f"Name{i+no_of_segs}")
            if matching_itemC:
                item_id = matching_itemC[0]
                self.canvas.move(item_id, 0, 60*no_of_segs)
                self.canvas.itemconfig(item_id, tags=f"Best{i+no_of_segs}")
            if matching_itemD:
                item_id = matching_itemD[0]
                self.canvas.move(item_id, 0, 60*no_of_segs)
                self.canvas.itemconfig(item_id, tags=f"Category{i+no_of_segs}")
                
        for i in range(no_of_segs):
            self.canvas.create_window(( 10,40+60*index), tags =f"Name{index}", window=name_entry(), width=300, height=20, anchor="nw")
            self.canvas.create_window((320,40+60*index), tags=f"Split{index}", window=split_time_entry(), width=100, height=20, anchor="nw")
            self.canvas.create_window(( 10,70+60*index), tags=f"Best{index}", window=best_segs_entry(), width=200, height=20, anchor="nw")
            self.canvas.create_window((220,70+60*index), tags=f"Category{index}", window=seg_category_entry(), width=200, height=20, anchor="nw")
            index+=1
        self.seg_count+=no_of_segs
        return True

    def remove_seg(self):
        if self.seg_count == 1:
            print("No removal possible")
        index = tk.simpledialog.askinteger("Abschnitte Editor","Bei welchem Index soll ein Segment entfernt werden?",minvalue=1, maxvalue=self.seg_count)
        if index is None:
            return False
        self.canvas.delete(f"Split{index}")
        self.canvas.delete(f"Name{index}")
        self.canvas.delete(f"Best{index}")
        self.canvas.delete(f"Category{index}")

        for i in range(index+1,self.seg_count+1):
            matching_itemA = self.canvas.find_withtag(f"Split{i}")
            matching_itemB = self.canvas.find_withtag(f"Name{i}")
            matching_itemC = self.canvas.find_withtag(f"Best{i}")
            matching_itemD = self.canvas.find_withtag(f"Category{i}")
            # 3. Check if the item exists and use its ID
            if matching_itemA:
                item_id = matching_itemA[0]
                self.canvas.move(item_id, 0, -60)
                self.canvas.itemconfig(item_id, tags=f"Split{i-1}")
            # 3. Check if the item exists and use its ID
            if matching_itemB:
                item_id = matching_itemB[0]
                self.canvas.move(item_id, 0, -60)
                self.canvas.itemconfig(item_id, tags=f"Name{i-1}")
            if matching_itemC:
                item_id = matching_itemC[0]
                self.canvas.move(item_id, 0, -60)
                self.canvas.itemconfig(item_id, tags=f"Best{i-1}")
            if matching_itemD:
                item_id = matching_itemD[0]
                self.canvas.move(item_id, 0, -60)
                self.canvas.itemconfig(item_id, tags=f"Category{i-1}")
        self.seg_count-=1

    def apply_changes_to_splits(self):
        try:
            canvas = self.canvas
            parent = self.parent
            parent.seg_count = self.seg_count
            parent.seg_names = [
             canvas.nametowidget(canvas.itemcget(canvas.find_withtag(f"Name{i+1}")[0],"window")).get() for i in range(parent.seg_count)
         ]
            parent.seg_order: List[List[Any]] = segment_order(parent.seg_names)
            parent.seg_count: int = len(parent.seg_names)

            
            best_segs = [[
            None if e == "" else float(e) for e in canvas.nametowidget(
            canvas.itemcget(canvas.find_withtag(f"Best{i+1}")[0],"window")
            ).get().split("|")
            ] for i in range(parent.seg_count)]



            seg_categories = [canvas.nametowidget(
            canvas.itemcget(canvas.find_withtag(f"Category{i+1}")[0],"window")
            ).get().split(" | ") for i in range(parent.seg_count)]
            
            seg_layers = [
                sorted([e for e in parent.seg_order if e[1][1]==i], key=lambda m: m[0][0]) for i in range(parent.seg_count)
                ]            
            for seg_layer,best_seg in zip(seg_layers,best_segs):
                for i,layer in enumerate(seg_layer):
                    time = el_by_ind(best_seg,i)
                    di = layer[0]
                    while len( parent.best_segs) <= di[0]:
                         parent.best_segs.append([])
                    while len(parent.best_segs[di[0]]) <= di[1]:
                         parent.best_segs[di[0]].append(None)    
                    parent.best_segs[di[0]][di[1]] = None if time is None or time < -0.5 else time


            for seg_layer,seg_category in zip(seg_layers,seg_categories):
                for i,layer in enumerate(seg_layer):
                    categories = el_by_ind(seg_category,i)
                    di = layer[0]
                    while len( parent.seg_categories) <= di[0]:
                         parent.seg_categories.append([])
                    while len(parent.seg_categories[di[0]]) <= di[1]:
                         parent.seg_categories[di[0]].append(None)
                    parent.seg_categories[di[0]][di[1]] = categories

            #try:
#                parent.best_segs: List[List[float]] =  b64_unlock(canvas.nametowidget(canvas.itemcget(canvas.find_withtag(f"BestSegs")[0],"window")).get())             
            #except:
            #    parent_best_segs = []

            pass1 = [canvas.nametowidget(canvas.itemcget(canvas.find_withtag(f"Split{i+1}")[0],"window")).get() for i in range(parent.seg_count)]
            parent.split_times: List[float] = [
             None if e == "" else float(e) for e in pass1
             ]

            parent.seg_info_cache: dict = get_seg_list_info(    parent.seg_order, curseg=0)
            self.root.destroy()
        except Exception as e:
            parent.log(e,type="ERROR")

    def setup_description_window(self):
        self.root.title("Beschreibung")
        self.root.geometry("500x300")
        self.root.grid_rowconfigure(0,weight=1)
        self.root.grid_columnconfigure(0,weight=1)
        root = self.root
        description = self.parent.description
        canvas = tk.Canvas(root, width=500, height=300, scrollregion=(0,0,1000000,1000000))
        scrollbarY = tk.Scrollbar(root, orient="vertical",command=canvas.yview)
        scrollbarX = tk.Scrollbar(root, orient="horizontal",command=canvas.xview)
        canvas.configure(yscrollcommand=scrollbarY.set,xscrollcommand=scrollbarX.set)
        canvas.grid(row=0,column=0,sticky="nsew")
        scrollbarY.grid(row=0,column=1,sticky="ns")
        scrollbarX.grid(row=1,column=0,sticky="ew")
        
        frame = tk.Frame(canvas)
        canvas.create_window((0,0),window=frame,anchor="nw")

        frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        for i,line in enumerate("\n".join(description).split("\n")):
            canvas.create_text(10,20+i*20, font=("Consolas",10), text=line, fill="white", anchor="w")

    def clear_logs(self):
        self.parent.clear_logs()
        self.root.destroy()

    def do_popup(self,event):
        if not self.parent.main_timer_running(): 
            try:
                self.menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.menu.grab_release()

    def setup_log_history_window_original(self):
        self.root.title("Protokolle")
        self.root.geometry("500x300")
        self.root.grid_rowconfigure(0,weight=1)
        self.root.grid_columnconfigure(0,weight=1)
        log_type_colors = {
            "FATAL": "red",
            "ERROR": "pink",
            "WARN": "yellow",
            "INFO": "lime",
            "DEBUG": "blue",
            "TRACE": "cyan"
        }
        root = self.root
        logs = self.parent.logs
        canvas = tk.Canvas(root, width=500, height=300, scrollregion=(0,0,1000000,1000000))
        scrollbarY = tk.Scrollbar(root, orient="vertical",command=canvas.yview)
        scrollbarX = tk.Scrollbar(root, orient="horizontal",command=canvas.xview)
        canvas.configure(yscrollcommand=scrollbarY.set,xscrollcommand=scrollbarX.set)
        canvas.grid(row=0,column=0,sticky="nsew")
        scrollbarY.grid(row=0,column=1,sticky="ns")
        scrollbarX.grid(row=1,column=0,sticky="ew")
        
        frame = tk.Frame(canvas)
        canvas.create_window((0,0),window=frame,anchor="nw")

        frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        for i,log in enumerate(logs):
            canvas.create_text(10,20+i*20, font=("Consolas",10), text=log[1], fill=log_type_colors.get(log[0]) or "white", anchor="w")

        self.menu = tk.Menu(self.root,tearoff=0)
        self.root.bind("<Button-3>", self.do_popup)
        self.menu.add_command(label = "Alle Protokolle löschen", command=self.clear_logs)





class MainWindow:
    TIMER_SPEED = 1
    SEG_ROW_COUNT = 11
    
    def __init__(self,parent = None) -> None:

        self.parent = None
        self.children = []
        # control
        self.curseg: int = 0
        self.attempts: int = 0
        self.seg_names: List[str] = ["NEU"]
        self.seg_categories: List[List[Any]] = []
        self.seg_order: List[List[Any]] = segment_order(self.seg_names)
        self.seg_count: int = len(self.seg_names)

        self.best_segs: List[List[float]] = []
        self.split_times: List[float] = []
        self.latest_splits: List[float] = []

        self.seg_info_cache: dict = get_seg_list_info(
            self.seg_order, curseg=self.curseg + 1
        )
        

        self.game_name: str = "Name des Spiels"
        self.run_category: str = "Kategorie des Durchlaufs"

        # timing
        self.main_timer: float = 0.0
        self.start: Optional[float] = None
        self.seg_timer: float = 0.0
        self.stop: Optional[float] = None
        self.time_limit: Optional[float] = None

        # description

        self.description = ["Hier können sie eure Bescreibung geben."]

        # logs

        self.log_count: int = 0
        self.cur_log_page = None
        self.log_pages = []
        self.logs = []

        # tkinter
        self.root = tk.Tk()
        self.menu = tk.Menu(self.root,tearoff=0)
        self.root.bind("<Button-3>", self.do_popup)


        settings_menu = tk.Menu(self.menu,tearoff=0)
        settings_menu.add_command(
            label="Name des Spiels ändern", command=lambda: self.configure_setting("GAME NAME"))
        settings_menu.add_command(
            label="Kategorie des Durchlaufs ändern", command=lambda: self.configure_setting("RUN CATEGORY"))
        settings_menu.add_command(
            label="Anzahl der Versuche ändern", command=lambda: self.configure_setting("ATTEMPTS"))
        settings_menu.add_command(
            label="Zeitlimit setzen", command=lambda: self.configure_setting("TIME LIMIT"))
        settings_menu.add_command(
            label="Segmente bearbeiten", command=lambda: self.create_child(type="EDIT SPLITS"))

        self.control_menu = tk.Menu(self.menu,tearoff=0)
        self.control_menu.add_command(
            label="Starten", command=self._start_or_split
            )
        self.control_menu.add_command(
            label="Pausieren", command=self._pause_main_timer, state="disabled"
            )
        self.control_menu.add_command(
            label="Aufteilen rckg.", command=self._desplit, state="disabled"
            )
        self.control_menu.add_separator()
        self.control_menu.add_command(
            label="Zurücksetzen", command=self._reset_run, state="disabled"
            )
        self.analyzer_menu = tk.Menu(self.menu,tearoff=0)
        self.analyzer_menu.add_command(
            label="Datenanalyze über Segmente", command=lambda: self.create_child(type="ANALYZER")
            )
        self.analyzer_menu.add_separator()
        self.analyzer_menu.add_command(
            label="Nachdurchlauf-Analyze",command=lambda: self.create_child(
                type="POST-RUN ANALYZER"
                                      )
            )

        self.menu.add_cascade(label = "Einstellungen", menu=settings_menu)
        self.menu.add_cascade(label = "Kontrolle", menu=self.control_menu)

        self.menu.add_command(label = "Beschreibung", command=self.create_child)

        self.menu.add_cascade(label = "Datenanalyze", menu=self.analyzer_menu)
        
        self.menu.add_command(label = "Protokolle (Original)", command=lambda: self.create_child(type="LOGS ORG"))
        self.menu.add_command(label = "Datei herunterladen", command=self.download_data)
        self.menu.add_command(label = "Datei importieren", command=self.import_data_by_file)



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

    def configure_setting(self,configuration):
        match configuration:
            case "GAME NAME":
                new_val = tk.simpledialog.askstring('Name ändern', 'Was soll der "Name des Spiels" werden?', initialvalue=self.game_name)
                if new_val is None: return False
                self.game_name = new_val
                self.game_name_label.configure(text=self.game_name)
                return True
            case "RUN CATEGORY":
                new_val = tk.simpledialog.askstring('Name ändern', 'Was soll die "Kategorie des Durchlaufs" werden?', initialvalue=self.run_category)
                if new_val is None: return False
                self.run_category = new_val
                self.run_category_label.configure(text=self.run_category)
                return True
            case "ATTEMPTS":
                new_val = tk.simpledialog.askinteger('Zahl ändern', 'Was soll die Anzahl der Versuche werden', initialvalue=self.attempts, minvalue=0)
                if new_val is None: return False
                self.attempts = new_val
                self.attempt_count_label.configure(text=f"Anzahl der Versuche: {self.attempts}")
                return True
            case "TIME LIMIT":
                new_val = tk.simpledialog.askinteger('Zahl ändern', 'Auf wie lang soll der Zeitlimit gestellt werden (in Sek.)?', initialvalue=self.time_limit or 0)

                if new_val is None: return False
                self.time_limit = None if new_val < 10 else new_val
                
                if self.time_limit is None:
                    tk.messagebox.showwarning(
                    "Kein Zeitlimit gesetzt",
                    "Sie haben versucht den Zeitlimit zu kurz zu setzen [erwartet: min. 10 Sek.], also es wurde in diesem Fall keins gesetzt."
                    )
                    self.time_limit_label.place_forget()
                else:
                    self.time_limit_label.place(relx=0.5, rely=0.96, anchor="center")
                return True
            case _:
                self.log("UNGULTIGE OPTION", type="ERROR")



    def create_child(self, **kwargs):
            child = ChildWindow(self, **kwargs)
            self.children.append(child)
        

    def do_popup(self,event):
        if not self.main_timer_running(): 
            try:
                self.menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.menu.grab_release()

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


        self.note_book.add(self.main_timer_tab, text="Haupt-Tab")
        #self.note_book.add(self.description_tab, text="Beschreibung")
        self.note_book.add(self.settings_tab, text="Einstellungen")
        #self.note_book.add(self.logs_tab, text="Protokolle")
        #self.setup_description_tab()
        #self.setup_logs_tab()


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
            keyboard.add_hotkey("x", lambda: self.read_instruction("START"))
            keyboard.add_hotkey("shift + q", lambda: self.read_instruction("PAUSE"))
            keyboard.add_hotkey("g", lambda: self.read_instruction("SPLIT"))
            keyboard.add_hotkey("shift + g", lambda: self.read_instruction("DESPLIT"))
            keyboard.add_hotkey("ctrl + shift + q", lambda: self.read_instruction("RESET"))
            keyboard.add_hotkey("u", lambda: self.read_instruction("JUMP"))

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

        tk.Label(self.settings_tab,text="Name des Spiels",font=("Consolas",10)).place(relx=0,y=20)
        self.game_name_entry = tk.Entry(
            self.settings_tab,font=("Consolas", 10),width=50
        )
        tk.Label(self.settings_tab,text="Durchlaufkategorie",font=("Consolas",10)).place(relx=0,y=50)
        self.run_category_name_entry = tk.Entry(
            self.settings_tab,font=("Consolas", 10),width=50
        )
        tk.Label(self.settings_tab,text="Anzahl der Versuche",font=("Consolas",10)).place(relx=0,y=80)
        self.attempt_count_entry = tk.Entry(
            self.settings_tab,font=("Consolas", 10),width=50
        )
        tk.Label(self.settings_tab,text="Zeitlimit",font=("Consolas",10)).place(relx=0,y=110)
        self.time_limit_entry = tk.Entry(
            self.settings_tab,font=("Consolas", 10),width=50
        )

        self.commit_name_settings_btn = tk.Button(
            self.settings_tab,text="Namenseinstellungen übernehmen",font=("Consolas", 10),command=self.commit_name_settings
        )

        #everything else
        
        self.game_name_label = tk.Label(self.main_timer_tab, text="Name des Spiels", font=("Consolas", 12))
        self.run_category_label = tk.Label(self.main_timer_tab,text="Kategorie des Durchlaufs", font=("Consolas", 8))
        self.attempt_count_label = tk.Label(self.main_timer_tab, font=("Consolas", 8)) 
        self.time_limit_label = tk.Label(self.main_timer_tab,font=("Consolas", 8)) 

        self.main_timer_label = tk.Label(self.main_timer_tab,font=("Consolas", 25))
        self.seg_timer_label = tk.Label(self.main_timer_tab,font=("Consolas", 15))
        self.best_seg_labels = [tk.Label(self.main_timer_tab,font=("Consolas", 8)) for _ in range(3)]
        self.pb_seg_labels = [tk.Label(self.main_timer_tab,font=("Consolas", 8)) for _ in range(3)]
        self.bpt_label = tk.Label(self.main_timer_tab,font=("Consolas", 8))

        self.seg_backframes = [tk.Frame(self.main_timer_tab) for _ in range(11)]
        self.left_segment_labels = [tk.Label(self.main_timer_tab,font=("Consolas", 10)) for _ in range(MainWindow.SEG_ROW_COUNT)]
        self.middle_segment_labels = [tk.Label(self.main_timer_tab,font=("Consolas", 10)) for _ in range(MainWindow.SEG_ROW_COUNT)]
        self.right_segment_labels = [tk.Label(self.main_timer_tab,font=("Consolas", 10)) for _ in range(MainWindow.SEG_ROW_COUNT)]


    def commit_name_settings(self) -> None:
        try:
            if not (self.start is None and self.stop is None):
                raise Exception(f"Erwartete Werte von (self.start,self.stop): (None,None). Istwerte: ({self.start},{self.stop})")
            self.game_name = self.game_name_entry.get()
            self.run_category = self.run_category_name_entry.get()
            att = self.attempt_count_entry.get()
            self.attempts = 0 if att == "" else int(att)
            if self.attempts < 10:
                self.log(f"Es wurde versucht, die Anzahl von Versuche als eine negative Zahl zu setzen, also es wurde stattdessen auf null gesetzt.",type="WARN")

            tl = self.time_limit_entry.get()
            self.time_limit = None if tl == "" else int(tl)
            if self.time_limit is not None and self.time_limit < 10:
                message = "Es wurde versucht, ein zu kurzes Zeitlimit festzulegen"
                if self.time_limit < 0:
                    message = "Es wurde versucht, ein negatives Zeitlimit festzulegen"
                self.time_limit = 10 
                self.log(f"{message}, also es wurde stattdessen auf 10 Sekunden festgelegt.",type="WARN")

            
            self.game_name_label.configure(text=self.game_name)
            self.run_category_label.configure(text=self.run_category)
            self.attempt_count_label.configure(text=f"Anzahl der Versuche: {self.attempts}")

            if self.time_limit is not None:
                self.time_limit_label.place(relx=0.5, rely=0.96, anchor="center")
            else:
                self.time_limit_label.place_forget()

            self.log("Nameneinsellungen erfolgreich übernommen.",type="INFO")
        except Exception as e:
            self.log(f"Fehler beim Übernehmen von Nameneinstellungen. → {e}",type="ERROR")

    def setup_labels(self) -> None:

        # settings
        #self.export_btn.place(relx=0.35,y=20,anchor="n")
        #self.import_btn.place(relx=0.65,y=20,anchor="n")
        #self.download_btn.place(relx=0.35,y=20,anchor="n")
        #self.import_file_btn.place(relx=0.65,y=20,anchor="n")
        #self.clear_logs_btn.place(relx=0.5,y=60,anchor="center")
        #self.export_text.place(relx=0,rely=0.3,width=400,height=200)
        self.game_name_entry.place(relx=0.3, y=20)
        self.run_category_name_entry.place(relx=0.3, y=50)
        self.attempt_count_entry.place(relx=0.3, y=80)
        self.time_limit_entry.place(relx=0.3, y=110)
        self.commit_name_settings_btn.place(relx=0.5, y=150,anchor="n")
        
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
        self.attempt_count_label.place(relx=0.5, y=60, anchor="center")

        self.attempt_count_label.configure(text=f"Anzahl der Versuche: {self.attempts}")

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
                return True
            except Exception as e:
                self.log(f"Der Versuch, eine Datei herunterzuladen, ist aufgrund des folgenden Fehlers fehlgeschlagen: {e}", type="ERROR"  )
                return False
        self.log(f"Der Versuch, eine Datei herunterzuladen, wurde abgebrochen.", type="WARN"  )
        return False

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
            "Versuche": self.attempts,
            "Zeitlimit": self.time_limit,
            "Segmentkategorien": self.seg_categories
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
            self.attempts: int = kwargs.get("Versuche") or 0
            self.seg_names: List[str] = list(kwargs.get("Segmentnamen"))
            self.seg_order: List[List[Any]] = segment_order(self.seg_names)
            self.seg_count: int = len(self.seg_names)
            self.seg_categories: List[List[Any]] = kwargs.get("Segmentkategorien") or []
            
            self.best_segs: List[List[float]] = kwargs.get("Beste Segmente") or []
            self.split_times: List[float] = kwargs.get("Zwischenzeiten") or []
            self.latest_splits: List[float] = kwargs.get("Aktuelle Zwischenzeiten") or []


            self.curseg: int = len(self.latest_splits)

            self.seg_info_cache: dict = get_seg_list_info(
                self.seg_order, curseg=self.curseg
            )

            self.game_name: str = kwargs.get("Spielname") or ""
            self.run_category: str = kwargs.get("Durchlaufkategorie") or ""

            # timing
            self.main_timer: float = kwargs.get("Stoppuhr") or 0.0
            self.time_limit: Optional[float] =kwargs.get("Zeitlimit")
            self.start: Optional[float] = None
            self.seg_timer: float = 0.0
            self.stop: Optional[float] = None

            # description

            self.description = kwargs.get("Beschreibung") or ["Hier können sie eure bescreibung eingeben."]

            if type(self.description) is not list:
                self.description = [f"Der Datentyp aus Ihrer Beschreibung ist ungültig.\n → Erwartet: „{list}“, erhalten: „{type(self.description)}“"]
                self.log("Fehler beim Importieren einer Beschreibung!",type="INFO")

            #self.description_pagebook.destroy()
            #self.setup_description_tab()
            self.log("Erfolgreich importiert!",type="INFO")

            self.game_name_entry.delete(0,tk.END)
            self.game_name_entry.insert(0,self.game_name)

            self.run_category_name_entry.delete(0,tk.END)
            self.run_category_name_entry.insert(0,self.run_category)

            self.attempt_count_entry.delete(0,tk.END)
            self.attempt_count_entry.insert(0,self.attempts)

            self.time_limit_entry.delete(0,tk.END)
            if self.time_limit is not None:
                self.time_limit_entry.insert(0,self.time_limit)



            self.game_name_label.configure(text=self.game_name)
            self.run_category_label.configure(text=self.run_category)            
            self.attempt_count_label.configure(text=f"Anzahl der Versuche: {self.attempts}")

            if self.time_limit is not None:
                self.time_limit_label.place(relx=0.5, rely=0.96, anchor="center")
            else:
                self.time_limit_label.place_forget()
  
        except Exception as e:
            self.log(f"Fehler beim der : {e}",type="ERROR")

    def log(self,message,**kwargs):
        _type = kwargs.get("type")
        final_message = f"{datetime.now()} | {_type} | {message}"
        print(final_message)
        self.logs.append((_type,final_message))
        self.log_count+=1
        
    def clear_logs(self):
        #self.logs_pagebook.destroy()
        self.log_count=0
        self.logs = []
        self.cur_log_page = None
        self.log_pages = []
        #self.setup_logs_tab()
        

    def read_instruction(self, cmd: str) -> None:
        cur_tab = self.note_book.index("current")
        if cur_tab != 0: return False
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

    def _start_or_split(self) -> None:
        if not self.main_timer_running():
            self._start_main_timer()
        else:
            self._split()

    def _start_main_timer(self) -> None:
        self.control_menu.entryconfigure(0, label="Aufteilten")
        self.control_menu.entryconfigure(1, state="normal")
        self.control_menu.entryconfigure(4, state="normal")
        if self.start is None:
            self.attempts+=1
            self.attempt_count_label.configure(text=f"Anzahl der Versuche: {self.attempts}")
        if not self.main_timer_running() and len(self.latest_splits) != self.seg_count:
            self.log(f"Haupttimer gestartet.",type="TRACE")
            self.stop = None
            self.start = time.time() - self.main_timer/MainWindow.TIMER_SPEED
            self.bpt_label.place(relx=0.5, rely=0.92, anchor="center")
            self.bpt_label.configure(text=f"Bestmögliche Zeit: {formatA(self.get_bpt())}")


    def _pause_main_timer(self) -> None:
        self.control_menu.entryconfigure(0, label="Fortsetzen")
        self.control_menu.entryconfigure(1, state="disabled")
        if self.main_timer_running():
            self.stop = time.time()
            if len(self.latest_splits) == self.seg_count:
                self.log(
                    f"🏁 Durchlauf bei {formatA(self.main_timer)} beendet.",type="INFO"
                )
            else:
                self.log(
                    f"Haupttimer {formatA(self.main_timer)} angehalten.",type="TRACE"
                )
            self.bpt_label.place_forget()


    def _reset_run(self) -> bool | None:
        ask_a,ask_b = None,None
        if len(self.latest_splits) == self.seg_count and (
            el_by_ind(self.split_times,-1) is None or len(self.latest_splits) > len(self.split_times) or (self.latest_splits[-1] < self.split_times[-1])
            ):
            ask_a = tk.messagebox.askyesno(
                "Neue Bestzeit erzielt!",
                "Hey! Du hast deine Bestzeit für den gesamten Durchlauf übertroffen ... möchtest du sie aktualisieren?"
                )
        seg_repr = seg_list_repr(
        self.seg_info_cache["list"],
        compare_to=self.split_times,
        split_times=self.latest_splits,
        best_segs=self.best_segs,
        )
        faster_than_best = [
            (s["depth_ind"],s["latest"]
             ) for s in seg_repr if (
                 s["latest"] is not None and (True if s["best"] is None else s["latest"] < s["best"])
                 )]
            
        if len(faster_than_best)!=0:
            ask_b = tk.messagebox.askyesno(
                "Neue Bestzeit erzielt!",
                "Hey! Du hast einige deiner besten Segmente übertroffen ... möchtest du sie aktualisieren?"
                )

        if ask_a:
            self.split_times = self.latest_splits
            self.log("Zwischenzeiten für den gesamten Durchlauf gespeichert.", type="INFO")
        if ask_b:
            for (depth,ind),latest in faster_than_best:
                while depth >= len(self.best_segs):
                    self.best_segs.append([])
                while ind >= len(self.best_segs[depth]):
                    self.best_segs[depth].append([])
                self.best_segs[depth][ind]=latest
            self.log("Beste Segmente gespeichert.", type="INFO")
            
            

        self.log(f"Durchlauf zurückgesetzt!",type="TRACE")
        self.start = None
        self.stop = None
        self.main_timer = 0.0
        self.latest_splits = []
        self.seg_info_cache = get_seg_list_info(self.seg_order, curseg=len(self.latest_splits))
        self.bpt_label.configure(text="")
        self.curseg = 0
        self.control_menu.entryconfigure(0, label="Starten", state="normal")
        self.control_menu.entryconfigure(1, state="disabled")
        self.control_menu.entryconfigure(2, state="disabled")
        self.control_menu.entryconfigure(4, state="disabled")


    def _split(self) -> bool:
        if not self.main_timer_running():
            return False
        self.control_menu.entryconfigure(2, state="normal")
        if len(self.latest_splits)+1 == self.seg_count:
            self._pause_main_timer()
            self.control_menu.entryconfigure(0, state="disabled")
            self.control_menu.entryconfigure(1, state="disabled")
            log1 = f"Bei {formatA(self.main_timer)} den Durchlauf beendet!"
        else:
            log1 = f"Bei {formatA(self.main_timer)} in das {len(self.latest_splits) + 2}. Gesamtsegment aufgeteilt."

        self.latest_splits.append(self.main_timer)

        seg_repr = seg_list_repr(
        self.seg_info_cache["final_list"],
        compare_to=self.split_times,
        split_times=self.latest_splits,
        best_segs=self.best_segs,
        )

        seg_cursors = self.get_curseg_cursors() #[ #next(#(e for e in seg_repr if e["range"][1] == self.curseg and e["depth_ind"][0] == i), #None,#) #for i in range(len(self.best_seg_labels)) #]

        for seg in seg_cursors:
            d = seg["depth_ind"]
            if seg["best"] is not None and (seg["latest"] is not None and seg["latest"] < seg["best"]):
                self.log(
                 f"Neue Bestzeit auf dem {d[1]+1}. Segment v. Tiefe {d[0]} mit einer Zeit von {seg['latest']:08.2f} erzielt. Name: {seg['text'][0]}",type="INFO"
                )
        self.log(log1,type="INFO")
        self.bpt_label.configure(text=f"Bestmögliche Zeit: {formatA(self.get_bpt())}")
        self.seg_info_cache = get_seg_list_info(self.seg_order, curseg=len(self.latest_splits))
        return True

    def _desplit(self) -> bool:
        if not self.latest_splits:
            return False
        self.control_menu.entryconfigure(0, state="normal")
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
        if not self.latest_splits:
            self.control_menu.entryconfigure(2, state="disabled")
        return True

    # -------------------------
    # Get Best Possible Time
    # -------------------------

    def get_curseg_cursors(self):
        seg_repr = seg_list_repr(
            self.seg_info_cache["final_list"],
            compare_to=self.split_times,
            split_times=self.latest_splits,
            best_segs=self.best_segs,
        )
        curseg_cursors = []
        for i in range(100):
            cursor = next(
                (e for e in seg_repr if e["range"][1] >= self.curseg and e["depth_ind"][0] == i), None
            )
            if cursor is None:
                break
            curseg_cursors.append(cursor)
        return curseg_cursors

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
        self.main_timer = MainWindow.TIMER_SPEED*((self.stop or now) - self.start) if self.start else self.main_timer
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
            main_slower_than_pb = False

        
        if self.main_timer_running():
            if curseg < len(split_times) and split_times[curseg] and split_times[curseg] < self.main_timer:
                right_fg = "red" if main_slower_than_pb else "#FF8080"
            else:
                right_fg = "#80FF80" if main_slower_than_pb else "green"

        if len(self.latest_splits) == self.seg_count:
            right_fg = "red" if split_times and split_times[-1] and self.main_timer > split_times[-1] and len(self.latest_splits) <= len(split_times) else "blue"

        self.main_timer_label.configure(text=formatA(self.main_timer), fg=right_fg)
        self.seg_timer_label.configure(text=formatA(self.seg_timer))
        if self.time_limit is not None:
            self.time_limit_label.configure(text=f"Zeitlimit: {formatB(max(0,self.time_limit-self.main_timer))}")
            if self.time_limit < self.main_timer:
                self._pause_main_timer()
                tk.messagebox.showwarning(
                    "ZEIT ABGELAUFEN!",
                    "Der Durchlauf dauerte in diesem Versuch leider zu lange...\nVersuche mal beim nächsten Mal den Durchlauf schneller zu machen."
                )
                self.log("Erfolgloser Versuch, das Zeitlimit zu unterbieten.", type="INFO")
                self._reset_run()

        # best / pb labels
        curseg_cursors = self.get_curseg_cursors()                

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
            bbb = curseg_cursors
            mid_fg = not (seg_in_cursors and len(bbb) != 1 and seg_r != bbb[-1] )
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

    def close(self):
        last = None
        streak = 0
        cap = 5
        while streak < cap+1:
            mess1 = "Möchten Sie Daten in einer Datei herunterladen, bevor Sie diese App beenden?"
            mess2 = "" if last is None else f"\nWählen sie {'Ja' if last else 'Nein'} noch weitere {cap+1-streak}-mal in Folge um die Antwort zu bestätigen."
            la = tk.messagebox.askyesnocancel(
                "Beenden", f"{mess1}{mess2}", icon='warning')
            if la is None:
                self.log("Beenden der App abgebrochen.", type="TRACE")
                return False
            if la == last:
                streak+=1
            else:
                last=la
                streak=1
        if la and not self.download_data():
            return False
        self.root.destroy()

    # -------------------------
    # Run
    # -------------------------

    def run(self) -> None:
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.mainloop()


# =========================
# App startup
# =========================

if __name__ == "__main__":
    app = MainWindow()
    app.run()