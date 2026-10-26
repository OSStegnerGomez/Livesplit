from random import random
import time
import os
from copy import deepcopy
from segments_3 import RawSTSegment
from segment_list import *
from helpers import *
import sys
import keyboard
from PyQt6.QtWidgets import (QApplication, QLabel, QMainWindow, QGridLayout, QWidget,QTableWidget, QTableWidgetItem, QMessageBox)
from PyQt6.QtGui import (QColor, QBrush, QPixmap, QFont, QShortcut, QKeySequence)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer, QSize
                
class GlobalHotkeyManager(QObject):
    # Signal to safely communicate from the background OS hook to the Qt GUI thread
    hotkey_triggered = pyqtSignal()

    def __init__(self, hotkey_str="ctrl+shift+a"):
        super().__init__()
        self.hotkey_str = hotkey_str
        self.is_active = False

    def enable_shortcut(self):
        """Starts listening to the system-wide shortcut if not already active."""
        if not self.is_active:
            # keyboard.add_hotkey links the key combo directly to our function
            keyboard.add_hotkey(self.hotkey_str, self.hotkey_triggered.emit)
            self.is_active = True
            
            

    def disable_shortcut(self):
        """Stops listening to the system-wide shortcut."""
        if self.is_active:
            # Removes all hooks associated with this specific key combination
            keyboard.remove_hotkey(self.hotkey_str)
            self.is_active = False

class SpeedrunTimerApp(QMainWindow):
    def __init__(self):        
        super().__init__() 
        self.resize(400,600)
        self.setWindowTitle("Custom Speedun App")
        self.label_relxy_mapping_list = []
        
        self.hotkeys_to_manage = [
        GlobalHotkeyManager("shift+g"),
        GlobalHotkeyManager("shift+h"),
        GlobalHotkeyManager("x"),
        GlobalHotkeyManager("w"),
        GlobalHotkeyManager("shift+q"),
        GlobalHotkeyManager("ctrl+shift+r"),
        ]
        
        self.cur_seg_idx = -1
        self.latest_split_time = 0
        self.latest_split_times=[]
        self.comp_list = [[]]
        self.comp_idx = 0
        
        self.timer_started_at = None 
        self.timer_stopped_at = None
        
        self.current_time = 0
        self.seg_time = 0
        #self.is_behind_comp = False
        #self.is_slower_than_comp = False
        
        self.segment_list = None
        self.flattened_seg_list = None
        self.total_segs = None
        self.font = QFont("Consolas", 25, 700, False)
        
        self.game_name = "Game Name"
        self.run_category = "Run Category"
        
        
        self.setup_window()
        
        self.setup_hotkeys()
        self.setup_intervals()
        
        self.load_segment_list(STSegmentList(segs=[RawSTSegment("New")]))
        
        
    def setup_intervals(self):
        self.ms_timer = QTimer(self)
        self.ms_timer.setInterval(10)
        self.ms_timer.timeout.connect(self.update_loop)
        
        self.ms_timer.start()
        
        self.update_pos = QTimer(self)
        self.update_pos.setInterval(10)
        self.update_pos.timeout.connect(self.repos)
        
        self.update_pos.start()
     
    has_started_timer = lambda self: self.cur_seg_idx!=-1
     
    def timer_is_running(self):
        return self.timer_started_at is not None and self.timer_stopped_at is None
    
    def add_label_to_relxy_mapping_list(self,label,relx,rely):
        self.label_relxy_mapping_list.append((label,relx,rely))
    
    def load_segment_list(self,seg_list: STSegmentList):
        self.segment_list = seg_list
        self.total_segs = self.segment_list.count_leaves()
        self.segment_list.def_idx_ranges_and_depths()
        self.flattened_seg_list = deepcopy(seg_list.flatten())
        
        self.game_name = self.segment_list.name
        self.run_category = el_by_idx(self.segment_list.categories,0) or ""
        
        self.game_name_label.setText(self.game_name)
        self.run_category_label.setText(self.run_category)
        
        for seg in self.flattened_seg_list:
            seg.truncate()
            
    def get_seglist_view(self,current_segment):
        flat_l = self.flattened_seg_list
        segs = [e for e in flat_l if e.depth==1]
        current_depth=1
        segs_to_show_before_last = 10
        
        current_segment=max(0,min(current_segment,flat_l[-1].leaf_idx_range[-1]))
        
        idx=0
        while idx < len(segs):
            seg = segs[idx]
            if current_segment in seg.leaf_idx_range:
                current_depth+=1
                subsegs = [
                e for e in flat_l if e.depth==current_depth and all(n in seg.leaf_idx_range for n in e.leaf_idx_range)
                ]
                if not subsegs: break
                for subseg in subsegs[::-1]:
                    segs.insert(idx+1,subseg)
            idx+=1
            
        miji = [current_segment in  e.leaf_idx_range for e in segs]
        highlight = [i for i, _ in enumerate(miji) if _]
        
        if not highlight: return None
        
        last_seg = segs.pop()
        
        segs_to_remove = highlight[-1]-segs_to_show_before_last+min(1+2,len(segs)-highlight[-1])
        segs_removed = 0

        idx = 0
        while segs_to_remove > segs_removed:
            if idx not in highlight:
                segs.pop(idx-segs_removed)
                segs_removed+=1
            idx+=1
                
        segs = segs[0:  segs_to_show_before_last]
        segs.append(last_seg)
            
        return segs

       
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.repos()
        
    def repos(self):
        # Keep relx=0.5, rely=0.5 centered
        for label,relx,rely in self.label_relxy_mapping_list:
            x = int( self.width() * relx  - label.width() * relx )
            y = int( self.height() * rely - label.height() * rely )
            label.move(x, y)
            label.adjustSize()
    
    def setup_window(self):
        
        self.game_name_label = QLabel(self.game_name, self)
        self.run_category_label = QLabel(self.run_category, self)
        self.timer_label = QLabel("00000.00", self)
        self.seg_timer_label = QLabel("00000.00", self)
        self.seg_attempts_label = QLabel("", self)
        
        self.add_label_to_relxy_mapping_list(self.game_name_label,0.5,0.03)
        self.add_label_to_relxy_mapping_list(self.run_category_label,0.5,0.06)
        self.add_label_to_relxy_mapping_list(self.timer_label,0.5,0.8)
        self.add_label_to_relxy_mapping_list(self.seg_timer_label,0.5,0.83)
        self.add_label_to_relxy_mapping_list(self.seg_attempts_label,0.5,0.9)
    
        self.game_name_label.setFont( QFont("Consolas", 10, 700, False))  
        self.run_category_label.setFont( QFont("Consolas", 8, 700, False))          
        self.timer_label.setFont( QFont("Consolas", 25, 700, False))
        self.seg_timer_label.setFont( QFont("Consolas", 15, 700, False))
        self.seg_attempts_label.setFont( QFont("Consolas", 10, 700, False))
        
        self.table = QTableWidget(self)

        self.table.setColumnCount(3)
        self.table.setColumnWidth(0, 270)
        self.table.setColumnWidth(1, 60)
        self.table.setColumnWidth(2, 60)

        #self.table.setHorizontalHeaderLabels(employees[0].keys())
        self.table.setRowCount(11)

        # Hide column numbers/letters (horizontal enumeration)
        self.table.setHorizontalHeaderLabels(("Name des Segment", "Delta", "Zeit"))
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers) 
        self.table.setWordWrap(False)
        self.table.setTextElideMode(Qt.TextElideMode.ElideRight)
        
        self.table.verticalHeader().setVisible(False)
        self.table.move(0,60)
    
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        #label = QLabel(self)
        #pixmap = QPixmap("C:\SonicOnGBA\Sonic1GBA\GreenHillZone.jpeg")
        #label.setPixmap(pixmap)
        #self.setCentralWidget(label)
        #self.resize(pixmap.width(), pixmap.height())
        #label.move(200,0)
     
    def setup_hotkeys(self):
        
        hotkeys = self.hotkeys_to_manage
        
        for h in hotkeys:
            h.enable_shortcut()
        
        hotkeys[0].hotkey_triggered.connect(self.split_seg)
        hotkeys[1].hotkey_triggered.connect(self.undo_split_seg)   
        hotkeys[2].hotkey_triggered.connect(self.start_timer)
        hotkeys[3].hotkey_triggered.connect(self.stop_timer)  
        hotkeys[5].hotkey_triggered.connect(self.reset_run)         
    
    def start_timer(self,*args):
        
        if self.cur_seg_idx == self.segment_list.count_leaves():
            return False
        
        timer_is_running = self.timer_is_running()
        
        if not timer_is_running:
            self.timer_started_at = time.perf_counter()-self.current_time
            self.timer_stopped_at = None
            
        if self.cur_seg_idx != -1:
            return "ALREADY STARTED"
        self.split_seg("FROM START")
            
    def stop_timer(self):
        timer_is_running = self.timer_is_running()
        
        if timer_is_running:
            self.timer_stopped_at = time.perf_counter()
      
    def split_seg(self, *args):
        
        if self.cur_seg_idx == -1 and not "FROM START" in args:
            return False
        
        cond1 = lambda: len(self.latest_split_times) == self.segment_list.count_leaves()
        if cond1() or not self.timer_is_running():
            return False
            
        self.cur_seg_idx+=1
            
        lt = self.latest_split_times
        
        if self.cur_seg_idx!=0:
            delta = self.current_time-self.latest_split_time
            lt.append(self.current_time)
        
        for seg in self.flattened_seg_list:
            idxr = seg.leaf_idx_range
            if idxr[0]==self.cur_seg_idx:
                seg.atts+=1
            if idxr[-1]!=self.cur_seg_idx-1:
                continue
            seg.latest_time = lt[idxr[-1]]-(lt[idxr[0]-1] if idxr[0] else 0)
            seg.latest_split_time = lt[idxr[-1]]
            seg.clears+=1
        
        if cond1():
            self.stop_timer()
        else:
            self.latest_split_time = self.current_time
        
        
    def undo_split_seg(self):
        
        if self.cur_seg_idx <= 0:
            return False
        self.cur_seg_idx-=1
        
        if self.cur_seg_idx == self.segment_list.count_leaves()-1:
            self.start_timer()
        
        lst = self.latest_split_times
        
        delta1 = lst.pop()
        delta2 = 0 if not lst else lst[-1]
        self.latest_split_time =delta2
        
        for seg in self.flattened_seg_list:
            if seg.leaf_idx_range[0]==self.cur_seg_idx+1:
                seg.atts-=1
            if seg.leaf_idx_range[-1]!=self.cur_seg_idx:
                continue
            seg.latest_time = None
            seg.latest_split_time = None
            seg.clears-=1
        
        return True
        
    def reset_run(self):
        
        self.stop_timer()
        
        #self.ask_run_best_update()
        
        self.cur_seg_idx=-1
        self.current_time=0
        self.latest_split_time = 0
        self.latest_split_times=[]
        
        for seg in self.flattened_seg_list:
            seg.latest_split_time=None
            self.latest_time = None
            
    def ask_run_best_update(self):
        dialog = QMessageBox()
        dialog.setWindowTitle("Neue Bestzeit erreicht!")
        dialog.setText("Möchtest du einen neuen Vergleich auf Basis deiner aktuellsten Zwischenzeiten erstellen?")
        dialog.setIcon(QMessageBox.Icon.Information)
        
        dialog.setStandardButtons(
        QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
        )
        
        clicked_btn = dialog.exec()
        
        if clicked_btn == QMessageBox.StandardButton.Ok:
            given_comp = self.comp_list[0]
            given_comp = self.latest_split_times
            
            def walk_segs(seg):
                for sseg in seg.segs:
                    walk_segs(sseg)
                print("DINO", seg)
                    
            walk_segs(self.segment_list)
        else:
            print("UPDATE CANCELED")
            
    def is_x_comp(self,x):
        given_comp = self.comp_list[self.comp_idx]
        aa = max(0,self.cur_seg_idx)
        
        match x:
            case "behind": return safe_comp(el_by_idx(given_comp,aa),"<",self.current_time)
            case "slower": return safe_comp(safe_sub(el_by_idx(given_comp,aa),el_by_idx(given_comp,aa-1) if aa != 0 else 0),"<",self.seg_time)
            
    def update_loop(self):
        if self.timer_is_running():
            self.current_time=( self.timer_stopped_at or time.perf_counter() )-self.timer_started_at
        self.seg_time = self.current_time-self.latest_split_time

        main_timer_line = format_number(self.current_time,decimal_places=2)
        seg_timer_line = format_number(self.seg_time,decimal_places=2)
                
        style_col = "white"
        if self.cur_seg_idx == self.segment_list.count_leaves():
            style_col = "red" if self.is_x_comp("behind") else "blue"
        
        if self.timer_is_running():
            mapping = ["green","#80FF80","#FF8080","red"]
            style_col = mapping[self.is_x_comp("slower")+self.is_x_comp("behind")*2]
                
        self.timer_label.setStyleSheet(f"color: {style_col};")
        self.timer_label.setText(main_timer_line)
        self.seg_timer_label.setText(seg_timer_line)
        self.update_table_view()        
     
    def update_table_view(self):
        
        #print_lines = random()<0.001
        
        def colour_row(row_idx,col_idx, color):
            item = self.table.item(row_idx, col_idx)
            if item: item.setBackground(color)
        
        font =  QFont("Consolas", 7, 700, False)
        crunched = self.get_seglist_view(self.cur_seg_idx)
        
        row_count = self.table.rowCount()
        col_count = self.table.columnCount()
            
        for i in range(row_count):
            for j in range(col_count):
                colour_row(i,j,QColor("gray"))
            
        if crunched is None: return None
       
        given_comp = self.comp_list[self.comp_idx]

        for i in range(row_count):
            try:
                e = crunched[i]
            except IndexError:
                items = [QTableWidgetItem("") for _ in range(3)]
                for j in range( col_count):
                    item = items[j]
                    item.setFont(font)
                    self.table.setItem(i, j, item)
                    colour_row(i,j,QColor("#000000"))
                continue
                
            idxr = e.leaf_idx_range
            is_highlighted = self.cur_seg_idx in idxr
            is_leaf = idxr[0]==idxr[-1]
            
            delta_format = None
            
            time_by_comp = el_by_idx(given_comp,idxr[-1])
            start_by_comp = el_by_idx(given_comp,idxr[0]-1) if idxr[0] else 0
            start_by_cur_splits = el_by_idx(self.latest_split_times,idxr[0]-1) if idxr[0] else 0 
            
            seg_time_by_comp = safe_sub(time_by_comp,start_by_comp)
            
            reveal_delta_earlyA = is_highlighted and (self.is_x_comp("behind") or self.is_x_comp("slower"))
            
            nnn = safe_sub(self.current_time,start_by_cur_splits)
            
            formatA = lambda: format_number(
            safe_sub(
            self.current_time if reveal_delta_earlyA else e.latest_split_time,
            time_by_comp),
            opt_plus=True,left_pad_digits=1,decimal_places=2
            )
            formatB = lambda: format_number(nnn,decimal_places=2)
            
            cur_seg_delta = formatA() if (
                is_leaf or not is_highlighted
                ) else formatB()
            
            delta_timeC = (e.latest_split_time or time_by_comp) if (is_leaf or not is_highlighted) else seg_time_by_comp
            reveal_delta_earlyB = not is_leaf and is_highlighted and safe_comp(nnn,">",delta_timeC)
            
            super_seg_time = format_number(
            delta_timeC,decimal_places=2
            ) if not reveal_delta_earlyB else format_number(
            nnn-delta_timeC,decimal_places=2,left_pad_digits=1,opt_plus=True
            )
            
            
            itemA = QTableWidgetItem(e.name )
            itemA.setFont(font)
            self.table.setItem(i, 0, itemA)
            
            itemB = QTableWidgetItem(cur_seg_delta)
            itemB.setFont(font)
            miau = get_delta_color(best=e.best_time,
            split=time_by_comp,
            latest=e.latest_split_time)
            
            itemB.setForeground(QBrush(QColor(miau)))
            
            self.table.setItem(i, 1, itemB)
            
            itemC = QTableWidgetItem(super_seg_time)
            itemC.setFont(font)
            itemC.setForeground(QBrush(QColor("red" if reveal_delta_earlyB else "white")))
            self.table.setItem(i, 2, itemC)
            
            for column_index in range( col_count):
                    colour_row(i,column_index,QColor("#000080" if is_highlighted else "#202020"))
            
        
        self.table.adjustSize()
        self.table.resize(450, 360)
        
class SpeedrunTimerApp_v2(QMainWindow):
    def __init__(s):
        super().__init__()
        s.setWindowTitle("Custom Speedun App")
        s.run = None
        s.load_run()
        s.label_relxy_mapping_list = []
        s.hotkeys = [
        GlobalHotkeyManager("shift+g"),
        GlobalHotkeyManager("shift+h"),
        GlobalHotkeyManager("x"),
        GlobalHotkeyManager("w"),
        GlobalHotkeyManager("shift+q"),
        GlobalHotkeyManager("ctrl+shift+r"),
        ]
        for e in s.hotkeys:
            e.enable_shortcut()
   
        s.setup_intervals()
        s.setup_widgets()
        s.setup_hotkeys()
        s.setFixedSize(400,800)
        
    def load_run(s,seg_list=None,name="PB"):
        if not seg_list:
            seg_list=STSegmentList(segs=[RawSTSegment("New")])
        s.run = STRun(name,seg_list=seg_list)
        
    def resizeEvent(s,e):
        super().resizeEvent(e)
        s.repos()
     
    def repos(s):
        for label, relx, rely in s.label_relxy_mapping_list:
            label.adjustSize()
            w = s.width()
            h = s.height()
            x = int( w * relx  - label.width() * relx )
            y = int( h * rely - label.height() * rely )
            label.move(x, y)
            
    def setup_intervals(s):
        s.ms_timer = QTimer(s)
        s.ms_timer.setInterval(10)
        s.ms_timer.timeout.connect(s.update_loop)
        
        s.ms_timer.start()
        
    def setup_hotkeys(s):
        s.hotkeys[0].hotkey_triggered.connect(s.run.split)
        s.hotkeys[1].hotkey_triggered.connect(s.run.undo_split)
        s.hotkeys[2].hotkey_triggered.connect(s.run.start)
        s.hotkeys[3].hotkey_triggered.connect(s.run.split)
        s.hotkeys[5].hotkey_triggered.connect(s.run.reset)
        
    def update_loop(s):
        s.timer_label.setText(
        format_number(s.run.current_time(),decimal_places=2)
        )
        
        s.seg_timer_label.setText(
        format_number(s.run.segment_time_by_split_times(),decimal_places=2)
        )
        s.update_table_view()
        
    def setup_widgets(s):
        s.timer_label = QLabel("00000.00",s)
        s.timer_label.setFont(QFont("Consolas",25,700, False))
        
        s.seg_timer_label = QLabel("00000.00",s)
        s.seg_timer_label.setFont(QFont("Consolas",15,700, False))
        
        
        s.seg_list_table = QTableWidget(s)
        
        s.label_relxy_mapping_list.append((s.timer_label,0.5,0.8))
        s.label_relxy_mapping_list.append((s.seg_timer_label,0.5,0.825))
        
        
        s.seg_list_table.setColumnCount(4)
        s.seg_list_table.setColumnWidth(0, 50)
        s.seg_list_table.setColumnWidth(1, 250)
        s.seg_list_table.setColumnWidth(2, 50)
        s.seg_list_table.setColumnWidth(3, 50)

        #self.table.setHorizontalHeaderLabels(employees[0].keys())
        s.seg_list_table.setRowCount(11)

        # Hide column numbers/letters (horizontal enumeration)
        s.seg_list_table.setHorizontalHeaderLabels(("Icon","Name des Segment", "Delta", "Zeit"))
        s.seg_list_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers) 
        s.seg_list_table.setWordWrap(False)
        s.seg_list_table.setTextElideMode(Qt.TextElideMode.ElideRight)
        
        s.seg_list_table.verticalHeader().setVisible(False)
        s.seg_list_table.move(0,60)
    
        s.seg_list_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        s.seg_list_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        s.seg_list_table.setFixedSize(400,400)
        s.seg_list_table.adjustSize()
        
    def update_table_view(s):
        
        row_count = s.seg_list_table.rowCount()
        column_count = s.seg_list_table.columnCount()
        crunch_flag, seg_view = s.run.repr_as_crunched_table_view(0,row_count)
        
        def colour_row(row_idx,col_idx, color):
            item = s.seg_list_table.item(row_idx, col_idx)
            if item:
                item.setBackground(QBrush(QColor(color)))
        
        for i, seg in enumerate(seg_view):
            highl,name,clear_rate = seg[0:3]
            split = format_number(seg[3] or seg[4], decimal_places=2) or "-"
 
            itemA = QTableWidgetItem("")
            itemA.setFont(QFont("Consolas",6,700,False))
 
            itemB = QTableWidgetItem(name)
            itemB.setFont(QFont("Consolas",6,700,False))
            
            itemC = QTableWidgetItem("")
            itemC.setFont(QFont("Consolas",6,700,False))
            
            itemD = QTableWidgetItem(f"{split}")
            itemD.setFont(QFont("Consolas",6,700,False))
            
            s.seg_list_table.setItem(i, 0, itemA)
            s.seg_list_table.setItem(i, 1, itemB)
            s.seg_list_table.setItem(i, 2, itemC)
            s.seg_list_table.setItem(i, 3, itemD)
            
            true_highl = s.run.has_started and not s.run.is_finished() and highl
            
            bg = "blue" if true_highl else "#404040"
            
            colour_row(i,0,bg)
            colour_row(i,1,bg)
            colour_row(i,2,bg)
            colour_row(i,3,bg)
        
        

def start_app():
    app = QApplication(sys.argv)
    
    app.setStyleSheet(
    """
    QWidget {
        background-color: black;    /* Dark slate blue for all windows */
    }
    """
    )
    
    window = SpeedrunTimerApp_v2()
    window.show()
    
    tetr_list = get_tetralogy_seg_list()
    seg = tetr_list.segs[0]
#    sseg = seg.segs[4]
    seg_list = STSegmentList(seg.name,segs=seg.segs,categories=[
    "[Tag 00187] Bestes Ende"
 #   "aus Sonic 1 Herraus.: The Room Vandalizer (GBA-Umsetzung)"
    ])
    
 #   window.load_segment_list(seg_list)
 #   window.comp_list[0] =  [38.164276361465454, 58.76179838180542, 102.92615365982056, 131.24601888656616, 196.0238161087036, 281.304071187973, 302.4567995071411, 400.07933378219604, 430.61845326423645, 547.349109172821, 628.8509771823883, 660.946875333786, 721.8188676834106, 738.2839586734772, 865.281051158905, 923.3461754322052, 956.4401891231537, 1059.9861664772034, 1113.446364402771, 1164.5501618385315, 1244.4075546264648, 1307.7907528877258, 1377.9361238479614, 1413.6173641681671, 1515.9013953208923]
    sys.exit(app.exec())
    
start_app()

"""

Diese Umsetzung ist unfassbarer dreister Müll!

Bei dem ganzen anderen Schieß, den diese Umsetzung zu bieten hat, war ich überrascht, dass dieser Aspekt nicht zu den schlechtesten Elemente gehört.

Im Grunde hat man die Präsentation ein wenig angepasst, sie aber auch Lama gestaltet.

Dann Sonic's Momentum, also wie er anläuft, wie er Speed aufnimmt und das den Sprung und alles andere beeinflusst: schnarschich und falsch, Nein x5

Die Kollisionsabfrage grauenhaft.

Leck mich am Arsch! Bisschen was los: Slowdown!

Geschmeidig wird es, wenn ich es in Buttertunke und dann den Verantwortlichen in den auch geil, ein Item nutzlos gemacht.
Die Turbeschuhe, die scheinen gar nichts zu bringen, oder nur wenig. Wahrscheinlich, weil das Speil dann eine einzige Ruckelorgie wäre.

Die Special Stages sind komplett für ein pickeligen Arsch!

Ich konnte nicht glauben was ich da spiele.
Wie sehr konnte man dieses Spiel eigentlich verhunsten?

Ich wurde an Stellen getroffen, die für mich ansonsten furzeinfach sind.

Oft höre ich Leuten die mit Sonic nicht aufgewachsen sind und/oder es nicht mögen, wie unkontrolierbar das Spiel sind, dass die amdauernd in Gegner oder Fallenrennen, kein e Übersicht hat und was weiß ich mal für ein Bullshit!


"""

"""

Sonic 1:

(Ring,Check,Ring-Gläser,Schild,Unsichtbar,Turbo,1UP)
- Zone 1:
-- Act 1:	151	  2	  7	  1	  2	  0	  0
-- Act 2:	123	  1	  4	  3	  1	  1	  1
-- Act 3:	123	  4	 11	  3	  3	  1	  2
----------------------------------------
-- Gesamt: 	397	  7	 22	  7	  6	  2	  3
-- Glassachen: 22+7+6+2+3 = 40

- Zone 2:
-- Act 1	 62	  1	  7	  2	  0	  0	  1
-- Act 2	 55	  1	  6	  3	  1	  0	  1
-- Act 3	 72	  2	  3	  3	  0	  0	  1
----------------------------------------
-- Gesamt: 	189	  4	 16	  8	  1	  0	  3
-- Glassachen: 14+8+1+0+3 = 26


- Zone 3:
-- Act 1	167	  2	  2	  1	  1	  1	  1
-- Act 2	221	  1	  0	  1	  1	  0	  1
-- Act 3	164	  2	  3	  3	  3	  1	  1
----------------------------------------
-- Gesamt: 	552	  5	  5	  5	  5	  2	  3
-- Glassachen: 5+5+5+2+3 = 20

- Zone 4:
-- Act 1	 70	  1	  4	  1	  0   0	  0
-- Act 2	 57	  1	  6	  1	  2   0	  0
-- Act 3	 28	  2	 11	  3	  2	  0	  1
----------------------------------------
-- Gesamt: 	155	  4	 21	  5	  4	  0	  1
-- Glassachen: 21+5+4+0+1 = 31

- Zone 5:
-- Act 1	113	  0	 11	  0	  3	  0	  1
-- Act 2	179	  0	  6	  0	  1	  0	  1
-- Act 3	179	  1	  9	  2	  5	  0	  1
----------------------------------------
-- Gesamt: 	471	  1	 26	  2	  9	  0	  3
-- Glassachen: 15+8+17 = 40

- Zone 6:
-- Act 1	197	  2	 11	  4	  0	  0	  0
-- Act 2	153	  0	 10	  2	  1	  0	  2
-- Act 3	108	  2	  6	  0	  0	  0	  1
----------------------------------------
-- Gesamt: 	458	  4	 27	  6	  1	  0	  3
-- Glassachen: 27+6+1+0+3 = 37


Sonic 2:

- Zone 1:
-- Act 1:	226	  3	  7	  2	  2	  1	  1
-- Act 2:	222	  5	  6	  2	  1	  1	  2
----------------------------------------
-- Gesamt: 	448	  8	 13	  4	  3	  2	  3
-- Glassachen: 13+4+3+2+3 = 25


- Zone 2:
-- Act 1:	195	  3	 13	  3	  2	  0	  1
-- Act 2:	157	  5	 14	  1	  2	  0	  2
----------------------------------------
-- Gesamt: 	352	  8	 27	  4	  4	  0	  3
-- Glassachen: 13+4+3+2+3 = 25

- Zone 3:
-- Act 1:	176	  3	  7	  3	  1	  1	  1
-- Act 2:	213	  4	 12	  0	  3	  1	  2
----------------------------------------
-- Gesamt: 	389	  7	 19	  3	  4	  2	  3
-- Glassachen: 13+4+3+2+3 = 31

- Zone 4:
-- Act 1:	232	  2	  7	  1	  2	  2	  1
-- Act 2:	206	  2	  9	  2	  2	  2	  1
----------------------------------------
-- Gesamt: 	438	  4	 16	  3	  4	  4	  2
-- Glassachen: 16+3+4+4+2 = 29

- Zone 5:
-- Act 1:	146	  2	  4	  1	  3	  0	  0
-- Act :2	196	  4	  8	  2	  2	  0	  2
----------------------------------------
-- Gesamt: 	342	  6	 12	  3	  5	  0	  2
-- Glassachen: 12+3+5+0+2= 22

- Zone 6:
-- Act 1:	182	  3	  7	  3	  2	  0	  0
-- Act 2:	206	  4	  7	  2	  2	  1	  1
----------------------------------------
-- Gesamt: 	388	  7	 14	  5	  4	  1	  1
-- Glassachen: 14+5+4+1+1=25

- Zone 7:
-- Act 1:	207	  2	  5	  2	  2	  0	  1
-- Act 2:	166	  3	  8	  2	  4	  1	  1
----------------------------------------
-- Gesamt: 	373	  5	 13	  4	  6	  1	  2
-- Glassachen: 13+4+6+1+2 = 26

- Zone 8:
-- Act 1:	213	  5	  6	  3	  1   0	  0
-- Act 2:	189	  3	  7	  2	  3	  0	  1
-- Act 3:	153	  6	  7	  2	  1	  0	  1
----------------------------------------
-- Gesamt: 	555	 14	 20	  7	  5	  0	  2
-- Glassachen: 20+7+5+0+2 = 34

--Zone 9: 64 Ringe


- Zone 10: 
-- Act 1:   196	  3	  9	  2	  2	  2	  3
-- Glassachen: 9+2+2+2+3 = 18


Sonic 3: 

(Ringe,Check,Ring-Gläser,Feuer,Wasser,Elektro,Unsicht,Turbo,1UP,Robot,Riesenring)

Zone 1:

Act 1	173	2	7	3	3	1	5	1	2	0	2
Act 2	237	4	4	3	3	3	0	0	4	0	2
__________________________________________________
Gesamt: 410	6	11	6	6	4	5	1	6	0	4
Glassachen: 39

Zone 2:
Act 1	440	5	14	0	3	2	2	0	3	0	2
Act 2	259	5	8	0	3	0	4	0	4	1	2
__________________________________________________
Gesamt: 699	10	22	0   6	2	6	0	7	1	4
Glassachen: 44

Zone 3:
Act 1	506	3	13	4	1	7	1	1	3	0	8
Act 2	352	8	8	2	1	3	2	1	2	0	3
__________________________________________________
Gesamt: 858	11  21	6   2	10	3	2	5	0	11
Glassachen: 49

Zone 4:
Act 1	312	5	26	2	3	5	3	2	3	0	6
Act 2	261	5	27	2	3	3	4	0	6	0	5
__________________________________________________
Gesamt: 573	10  53	4   6	8	7	2	9	0	11
Glassachen: 89

Zone 5:
Act 1	172	4	5	0	0	3	1	0	0	0	2
Act 2	479	2	2	0	0	2	1	0	2	2	3
__________________________________________________
Gesamt: 651	6   7	0   0	5	2	0	2	2	5
Glassachen: 18


Zone 6 (S3):
Act 1	211	6	15	3	5	5	0	1	0	0	3
Act 2	287	6	15	4	4	0	1	0	1	3	5
__________________________________________________
Gesamt: 498	12  30	7   9	5	1	1	1	3	8
Glassachen: 57 

Zone 6 (S3&K):
Act 1	294	6	16	2	5	4	2	1	0	0	3
Act 2	409	6	16	5	5	0	2	0	1	0	5
__________________________________________________
Gesamt: 703	12  32	7   10	4	4	1	1	0	8
Glassachen: 59

"""