import keyboard
from datetime import datetime
import time

def flatten_list(x):
    return [n for ns in x for n in ns]

def formatA(x: int) -> str:
    if x < 0: return f"-{formatA(-x)}"
    return f"{x:.02f}".zfill(8)

def formatB(x: int) -> str:
    if x < 0: return f"-{formatB(-x)}"
    return f"{int(x)}".zfill(5)

def ordinal_num(n: int) -> str:
    """Convert an integer into its ordinal representation (e.g. 1 -> '1st')"""
    if 11 <= (n % 100) <= 13:
        suffix = 'th'
    else:
        suffix = ['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]
    return f"{n}{suffix}"



"""
[22:17:04] Started main timer.
[22:17:43] Splitted into the 2nd segment at 00039.12.
[22:18:03] Splitted into the 3rd segment at 00059.29.
[22:18:48] Splitted into the 4th segment at 00103.81.
[22:19:16] Splitted into the 5th segment at 00131.97.
[22:20:20] Splitted into the 6th segment at 00196.55.
[22:21:48] Splitted into the 7th segment at 00283.79.
[22:22:10] Splitted into the 8th segment at 00305.83.
[22:24:01] Splitted into the 9th segment at 00417.40.
[22:24:30] Splitted into the 10th segment at 00445.75.
[22:26:40] Splitted into the 11th segment at 00575.63.
[22:27:56] Splitted into the 12th segment at 00652.36.
[22:28:35] Splitted into the 13th segment at 00690.70.
[22:29:40] Splitted into the 14th segment at 00755.91.
[22:29:56] Splitted into the 15th segment at 00772.18.
[22:32:08] Splitted into the 16th segment at 00903.74.
[22:33:12] Splitted into the 17th segment at 00968.23.
[22:33:52] Splitted into the 18th segment at 01007.81.
[22:35:54] Splitted into the 19th segment at 01130.12.
[22:36:47] Splitted into the 20th segment at 01182.87.
[22:37:39] Splitted into the 21st segment at 01235.31.
[22:39:02] Splitted into the 22nd segment at 01317.89.
[22:40:04] Splitted into the 23rd segment at 01380.03.
[22:41:13] Splitted into the 24th segment at 01448.97.
[22:41:53] Splitted into the 25th segment at 01489.01.
[22:43:27] 🏁 Finised the run at 01583.29.
"""

segments = [
            {
                "name": "--Akt 1",
                "SPLIT": 39.12,
                "BEST": 38.29
                },
            {
                "name": "--Spezial 1",
                "SPLIT": 59.29,
                "BEST": 18.6
                },
            {
                "name": "--Akt 2",
                "SPLIT": 103.81,
                "BEST": 43
                },
            {
                "name": "--Spezial 2",
                "SPLIT": 131.97,
                "BEST": 26
                },
            {
                "name": "-♀🏀00.08 *RESET-*Sporthalle [Normal]|Akt 3",
                "SPLIT": 196.55,
                "BEST": 63.14
                },
            
            {
                "name": "--Akt 1: EIN ZYKLUS!",
                "SPLIT": 283.79,
                "BEST": 86.89
                },
            {
                "name": "--Spezial 3: SPRING!",
                "SPLIT": 305.83,
                "BEST": 18.9,
                },
            {
                "name": "--Akt 2: Bitte nicht alle Ringe verlieren.",
                "SPLIT": 417.40,
                "BEST": 102.19
                },
            {
                "name": "--Spezial 4",
                "SPLIT": 445.75,
                "BEST": 28.25
                },
            {
                "name": "-♂🍳00.25 Hauptküche der Schule|Akt 3",
                "SPLIT": 575.63,
                "BEST": 117.56
                },
            
            {
                "name": "--Akt 1: NOCH EIN ZYKLUS!",
                "SPLIT": 652.36,
                "BEST": 76.73
                },
            {
                "name": "--Spezial 5",
                "SPLIT": 690.70,
                "BEST": 38.34
                },
            {
                "name": "--Akt 2: ETWAS HEIKLIG!",
                "SPLIT": 755.91,
                "BEST": 63.31
                },
            {
                "name": "--Spezial 6: SPRING!!",
                "SPLIT": 772.18,
                "BEST": 15
                },
            {
                "name": "-♀🏰00.08 Sporthalle [Akt=Hüpfburg]|Akt 3: HEIKLIG AM ANFANG!",
                "SPLIT": 903.74,
                "BEST": 134.86
                },
            
            {
                "name": "--Akt 1: Wasserphysik!",
                "SPLIT": 968.23,
                "BEST": 60.33
                },
            {
                "name": "--Akt 2: Nützlicher Sprungfeder!",
                "SPLIT": 1007.81,
                "BEST": 33.5
                },
            {
                "name": "-♂🚿00.11 Umkleideraum [Akt=Waschbecken]|Akt 3: PARKOURZEIT!",
                "SPLIT": 1130.12,
                "BEST": 112.12
                },

            {
                "name": "--Akt 1: Sie schauen da ein guten Film",
                "SPLIT": 1182.87,
                "BEST": 52.75
                },
            {
                "name": "--Akt 2: Sie schauen sich gerade „Golden“ an.",
                "SPLIT": 1235.31,
                "BEST": 49.08
                },
            {
                "name": "-♂🎬10.05 Gymnastikraum [Kinoraum]|Akt 3: Dieser Film: KPop Demon Hunters",
                "SPLIT": 1317.89,
                "BEST": 82.58
                },

            {
                "name": "--📍Akt 1: Raummitte",
                "SPLIT": 1380.03,
                "BEST": 62.14
                },
            {
                "name": "--🍳Akt 2: Kochnische(↓), Da wird gekocht!",
                "SPLIT": 1448.97,
                "BEST": 64.30
                },
            {
                "name": "--🚰Akt 3: Waschbecken 4, Das ist schlau!",
                "SPLIT": 1489.01,
                "BEST": 39.49
                },
            {
                "name": "Sonic 1 GBA|♀🎒10.28 Klassenraum [Sehusaschule]|🍽Akt 4: Kochnische(↑), WIEDER HEIKLIG",
                "SPLIT": 1583.29,
                "BEST": 80
                }
            ]
            
            
def segment_order(segments):
    final = []
    segs = [[0, 0, i, seg["name"],seg["SPLIT"],seg["BEST"]] for i,seg in enumerate(segments)]
    latest = [0 for _ in range(10)]
    while segs:
        i = 0
        while i < len(segs):
            if segs[i][3][0]=="-":
                segs[i][0]+=1
                segs[i][3] = segs[i][3][1:]
                i+=1
            else:
                vert_bar = segs[i][3].find("|")
                if vert_bar != -1:
                    seg_copy = segs[i][:]
                    seg_copy[3] = segs[i][3][:vert_bar]
                    seg_copy[1] = latest[seg_copy[0]]
                    final.append(seg_copy)
                    latest[seg_copy[0]] = seg_copy[2]+1
                    segs[i][3]=  segs[i][3][vert_bar+1:]
                    segs[i][0]+=1
                    break
                else:
                    popp = segs.pop(i)
                    popp[1]=popp[2]
                    final.append(popp)
    return final
    
final = segment_order(segments)

def seg_list_repr(_list,split_times=[]):
        info = []
        for seg in _list:
            left, middle, right=seg[3], None, seg[4]
            if len(split_times)> seg[2]:
                right=split_times[seg[2]]
                middle = split_times[seg[2]]-seg[4]
            info.append((seg[0],seg[1],seg[2],left,middle,right))
        return info

def get_seg_list_info(seg_list,split_times = []):
    curseg = len(split_times)
    info = {"list":seg_list}
    if curseg is None:
        info["final_list"] = info["list"]
        return info
    elif curseg >= max([e[2] for e in seg_list]):
        curseg = max([e[2] for e in seg_list])-1
    curdepth = 0
    info = {}
    seg_chain = []
    while True:
        bucket = [e for e in final if e[0]==curdepth]
        espege = next((e for e in bucket if e[2]>=curseg),None)
        if not espege: break
        else: seg_chain.append(espege)
        curdepth+=1
    seg_blocks = [[e for e in final if e[0]==0]]
    for seg in seg_chain[:-1]:
     seg_blocks.append([e for e in final if e[0]==seg[0]+1 and e[1] >= seg[1] and e[1] <= seg[2]])
    final_block_stack = []
    last_choosen = []
    next_choosen_ind = 0
    for i,block in enumerate(seg_blocks):   
        for seg in block:
            if seg[2] >= curseg:
                final_block_stack[next_choosen_ind:next_choosen_ind] = block
                last_choosen=block
                next_choosen_ind=final_block_stack.index(seg_chain[i])+1
                break
    info["chain"] = [e[3] for e in seg_chain]
    info["final_list"] = final_block_stack
    info["curseg_cursor"] = final_block_stack.index(seg_chain[-1])
    info["list_repr"] = seg_list_repr(final_block_stack,split_times)
    return info

import tkinter as tk
#import time
from datetime import datetime
class App:
    def __init__(self,name="NEW",segments=[]):

        #control
        self.curseg = 0
        self.segments = segments
        self.seg_order = segment_order(segments)
        self.seg_count = len(segments)
        self.split_times = []
        self.seg_info_cache = get_seg_list_info(self.seg_order,self.split_times)


        # timing
        self.main_timer = 0
        self.start = None
        self.seg_timer = 0
        self.stop = None

        # tkinter
        self.w = tk.Tk()
        self.name=name
        self.setup_window()
        self.setup_labels()
        self.setup_hotkeys()
        self.update_loop()
        
    def run(self):
        self.w.mainloop()

    def setup_window(self):
        self.w.title(self.name)
        self.w.configure(bg="black")
        self.w.geometry("400x400")
        self.w.option_add("*Background", "black")
        self.w.option_add("*Foreground", "white")
        self.w.resizable(False, False)

    
    def setup_labels(self):
        #place timers
        self.main_timer_label = tk.Label(font=("Consolas",25))
        self.seg_timer_label = tk.Label(font=("Consolas",15))
        self.best_seg_label = tk.Label(font=("Consolas",10))
        self.pb_seg_label = tk.Label(font=("Consolas",10))
        self.main_timer_label.place(relx=0.5, rely=0.82,anchor="center")
        self.seg_timer_label.place(relx=0.5, rely=0.9,anchor="center")
        self.best_seg_label.place(relx=0, rely=0.84)
        self.pb_seg_label.place(relx=0, rely=0.9)
        
        #define
        self.seg_backframes = [tk.Frame() for _ in range(11)]
        self.game_name_label = tk.Label(font=("Consolas",15))
        self.left_segment_labels = [tk.Label(font=("Consolas",10) ) for _ in range(11)]
        self.right_segment_labels = [tk.Label(font=("Consolas",10) ) for _ in range(11)]

        #place
        [frame.place(relwidth=1, height=21, y=i*21+80) for  i, frame in enumerate(self.seg_backframes)]
        [label.place(relx=0, y=i*21+90,anchor="w") for i,label in enumerate(self.left_segment_labels)]
        [label.place(relx=1, y=i*21+90,anchor="e") for i,label in enumerate(self.right_segment_labels)]
   


    def setup_hotkeys(self):
        keyboard.add_hotkey('z', lambda: self.read_instruction("START"))
        keyboard.add_hotkey('x', lambda: self.read_instruction("HELLO!"))
        keyboard.add_hotkey('shift + q', lambda: self.read_instruction("PAUSE"))
        keyboard.add_hotkey('s', lambda: self.read_instruction("SPLIT"))
        keyboard.add_hotkey('shift + s', lambda: self.read_instruction("DESPLIT"))
        keyboard.add_hotkey('ctrl + shift + q', lambda: self.read_instruction("RESET"))

    def read_instruction(self, cmd):
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

    def _start_main_timer(self):
        if not self.main_timer_running() and len(self.split_times)!=self.seg_count:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Started main timer.")
            self.stop = None
            self.start = time.time() - self.main_timer

    def _pause_main_timer(self):
        if self.main_timer_running():
            self.stop = time.time()
            if len(self.split_times)==self.seg_count:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🏁 Finised the run at {formatA(self.main_timer)}.")
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Paused at {formatA(self.main_timer)}.")

    def _reset_run(self):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Reset run.")
        self.start = None
        self.stop = None
        self.main_timer = 0.0
        self.split_times = []
        self.seg_info_cache = get_seg_list_info(self.seg_order,self.split_times)


    def _split(self):
        if not self.main_timer_running():
            return False


        self.split_times.append(self.main_timer)
        self.seg_info_cache = get_seg_list_info(self.seg_order,self.split_times)
        if len(self.split_times)==self.seg_count:
            self._pause_main_timer()
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Splitted into the {ordinal_num(len(self.split_times)+1)} segment at {formatA(self.main_timer)}.")


    def _desplit(self):
        if not self.split_times:
           return False
        
        if self.main_timer_running():
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Desplited back into the {ordinal_num(len(self.split_times))} segment.")
            self.split_times.pop()
            self.seg_info_cache = get_seg_list_info(self.seg_order,self.split_times)
        elif len(self.split_times)==self.seg_count:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Desplited back into the {ordinal_num(len(self.split_times))} segment.")
            self.split_times.pop()
            self.seg_info_cache = get_seg_list_info(self.seg_order,self.split_times)
            self._start_main_timer()

    def main_timer_running(self):
        return self.start is not None and self.stop is None

    def update_loop(self):
        import time

        if self. main_timer_running():
            self.curseg = len(self.split_times)

        self.main_timer = ((self.stop or time.time())-self.start) if self.start else self.main_timer
        self.seg_timer  = self.segments[self.curseg]['SPLIT']-(
            self.segments[self.curseg-1]['SPLIT'] if self.curseg else 0
            )
        
        self.main_timer_label.configure(text=f"{formatA(self.main_timer)}")
        self.best_seg_label.configure(text=f"BEST: {self.segments[self.curseg]['BEST']:.2f}" if self.main_timer_running() else   "")
        self.pb_seg_label.configure(text="  PB: {}".format( f"{self.seg_timer:.2f}"  ) if self.main_timer_running() else "")
        
        
        seg_timer = self.main_timer - (0 if not self.split_times else self.split_times[-1])
        self.seg_timer_label.configure(text=f"{formatA(seg_timer)}")
        
        seg_info = self.seg_info_cache
        
        _repr = seg_info["list_repr"]

        timer_running = self.main_timer_running()
        split_time_of_curseg = self.segments[min(self.seg_count-1,self.curseg)]["SPLIT"]
        if not timer_running:
            fg="white"
        elif split_time_of_curseg < self.main_timer:
            fg="red"
        else:
            fg="green"

        if len(self.split_times) == self.seg_count:
            fg = "red" if self.segments[-1]["SPLIT"] < self.main_timer else "blue"
                
        
        self.main_timer_label.configure(fg=fg)
        for i,(left,right,bgframe) in enumerate(
            zip(self.left_segment_labels,self.right_segment_labels,self.seg_backframes)
            ):
            if i >= len(_repr):
                left.configure(text="")
                right.configure(text="")
                continue
            if self.curseg in range(_repr[i][1],_repr[i][2]+1) and timer_running:
                bg = "#000080" if _repr[i][0]%2 else "#000060"
            else:
                bg = "black" if i % 2 else "#202020"
            left.configure(bg=bg)
            right.configure(bg=bg)
            bgframe.configure(bg=bg)
            time = ''
            if _repr[i][4] is None:
                right.configure(fg="white")
            else:             
                time = f"{_repr[i][4]:+.1f}"
                if _repr[i][4] > 0:
                    right.configure(fg="red")
                else:
                    right.configure(fg="green")
            
            text=f"{time}   {formatB(_repr[i][5])}"
            left.configure(text=f"{' '*_repr[i][0]}{_repr[i][3]}")
            right.configure(text=text)

        self.w.after(20, self.update_loop)
            

app = App("Custom Livesplit v 2.0",segments)
app.run()
