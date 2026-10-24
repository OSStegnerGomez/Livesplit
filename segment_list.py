import time
import os
from copy import deepcopy
from segments_3 import RawSTSegment, games_list
from helpers import el_by_idx, safe_sub
import random

class STRunSegTableItem:
    def __init__(s,name,**kwargs):
        s.name=name
        s.clear_rate = kwargs.get("clear_rate")
        s.split_time = kwargs.get("split_time")
        s.comp_time = kwargs.get("comp_time")
        
    def __repr__(s):
        return s.repr()
    
    def repr(s):
        return f'''
STRunSegTableItem(
"{s.name}",
clear_rate={s.clear_rate},
split_time={s.split_time},
comp_time={s.comp_time}
)'''

class STSegmentList(RawSTSegment):
    
    def repr(self):
        final = f'STSegmentList("{self.name}"'
        if self.segs:
            final += f',segs=[\n{",".join([e.repr() for e in self.segs])}]'
        final += ')\n'
        return final
        
    def __repr__(self):
        return self.repr()
        
    def def_idx_ranges_and_depths(self):
        current_path = [self]
        current_idx_path = []
        current_seg = self
        all_leaf_segs = []
        current_seg_idx = 0
        ending_idx = 0
        start_idxs = []
        seg_depth = 0
            
        cheese = lambda: current_seg.is_leaf() or current_seg_idx == len(current_seg.segs)
        i = 0
        while i < 1000000:
            while not cheese():                
                current_seg = current_seg.segs[current_seg_idx]
                current_path.append(current_seg)
                current_idx_path.append(current_seg_idx)
                seg_depth+=1
                start_idxs.append(i)
                current_seg_idx=0
            while cheese():
                if not start_idxs: return None
                start_idx = start_idxs.pop()
                current_seg.leaf_idx_range = range(start_idx,i+1)
                current_seg.depth = seg_depth
                current_path.pop()
                current_seg = current_path[-1]
                current_seg_idx = current_idx_path.pop()+1
                seg_depth-=1
            i+=1
            
    def flatten(self):
        
        def cheese(seg):
            final = [seg]
            if seg.is_leaf(): return [seg]
            for subseg in seg.segs:
                final.extend(cheese(subseg))
            return final
        final = []
        for seg in self.segs:
            final.extend(cheese(seg))
        return final
            

class STSegmentList_v2(RawSTSegment):
    
    def __init__(s,se=[]): s.segs = se or []
        
    insert_seg = RawSTSegment.insert_seg
    insert_segs = RawSTSegment.insert_segs
    remove_seg = RawSTSegment.remove_seg
    count_leaves = RawSTSegment.count_leaves
    
    def repr(self):
        final = f'STSegmentList_v2('
        if self.segs:
            final += f'[\n{",".join([e.repr() for e in self.segs])}]'
        final += ')\n'
        return final
        
    def __repr__(self):
        return self.repr()
        
    def def_idx_ranges_and_depths(self):
        current_path = [self]
        current_idx_path = []
        current_seg = self
        all_leaf_segs = []
        current_seg_idx = 0
        ending_idx = 0
        start_idxs = []
        seg_depth = 0
        leave_count = self.count_leaves()
            
        cheese = lambda: current_seg.is_leaf() or current_seg_idx == len(current_seg.segs)
        i = 0
        for i in range(leave_count):
            while not cheese():                
                current_seg = current_seg.segs[current_seg_idx]
                current_path.append(current_seg)
                current_idx_path.append(current_seg_idx)
                seg_depth+=1
                start_idxs.append(i)
                current_seg_idx=0
            while cheese():
                if not start_idxs: return None
                start_idx = start_idxs.pop()
                current_seg.leaf_idx_range = range(start_idx,i+1)
                current_seg.depth = seg_depth
                current_path.pop()
                current_seg = current_path[-1]
                current_seg_idx = current_idx_path.pop()+1
                seg_depth-=1
            
            
    def flatten(self):      
        def cheese(seg):
            final = [seg]
            if seg.is_leaf(): return [seg]
            for subseg in seg.segs:
                final.extend(cheese(subseg))
            return final
        final = []
        for seg in self.segs:
            final.extend(cheese(seg))
        return final

class STRun:
    def __init__(s,name,**kwargs):
        s.game_name = name
        s.fails = 0
        s.category = kwargs.get("category","")
        s.clears = kwargs.get("clears",0)
        s.seg_list = kwargs.get("seg_list",[])
        s.seg_list.def_idx_ranges_and_depths()
        s.seg_list_flat = s.seg_list.flatten()
        s.leave_count = s.seg_list.count_leaves()
        s.latest_split_times = []
        s.elapsed_time = 0
        
        s.timer_started_at = None 
        s.timer_stopped_at = None
        
    
    is_finished = lambda s: len(s.latest_split_times) == s.leave_count
    has_started = lambda s: s.timer_started_at is not None
    timer_is_running = lambda s: s.has_started() and (s.timer_stopped_at is None)
    
    clear_rate = lambda s: f"{s.clears}/{s.clears+s.fails}"
    
    def get_highlighted(s,c="end"):
        match c:
            case "end": return [e for e in s.seg_list_flat if e.leaf_idx_range[-1] == len(s.latest_split_times)]
            case "start": return [e for e in s.seg_list_flat if e.leaf_idx_range[0] == len(s.latest_split_times)]
            case "current": return [e for e in s.seg_list_flat if len(s.latest_split_times) in e.leaf_idx_range]
    
    def current_time(s):
        return (s.timer_stopped_at or time.perf_counter())-s.timer_started_at if s.has_started() else 0

    def segment_time_by_split_times(s,idx1=None,idx2=None):
        
        if idx1 is None:
            idx1 = len(s.split_times)
            
        if idx2 < idx1: idx1,idx2 = idx2,idx1
        
        if not idx:
            idx = len(s.latest_split_times)-1
        cur_time = s.current_time()
        time2 = el_by_idx(s.latest_split_times,idx2,cur_time)
        time1 = el_by_idx(s.latest_split_times,idx1-1,cur_time) if idx1 != 0 else 0
        return time2-time1

    def reset(s):
        if not s.is_finished():
            s.fails+=1
        
        for seg in s.get_highlighted("current"):
            seg.fails+=1
        
        s.timer_started_at = None 
        s.timer_stopped_at = None
        s.elapsed_time=0
        s.latest_split_times = []
        
        def cheese(seg):
            for sseg in seg.segs:
                cheese(sseg)
            seg.latest_time = None
        for seg in s.seg_list.segs:
            cheese(seg)

    def start(s):
        s.elapsed_time = s.current_time()
        if s.is_finished():
            return False
        
        #if not s.has_started():
        #    s.atts+=1
        #    for seg in s.get_highlighted("start"):
        #        seg.atts+=1
        
        s.timer_started_at = time.perf_counter()-s.elapsed_time
        s.timer_stopped_at = None
        
    def stop(s):
        timer_is_running = s.timer_is_running()
        if timer_is_running:
            s.timer_stopped_at = time.perf_counter()    
            
    def restart(s):
        s.reset()
        s.start()
    
    def split(s):
        if s.is_finished() or not s.has_started():
            return False
        cur_time = s.current_time()
        for seg in s.get_highlighted("end"):
            idxr = seg.leaf_idx_range
            a,b = idxr[0],idxr[-1]
            is_leaf = a==b
            
            seg_time = cur_time-(el_by_idx(s.latest_split_times,a-1) if a != 0 else 0)
            seg.latest_time=seg_time
            seg.clears+=1
        
        
        s.latest_split_times.append(cur_time)
        
        
        if s.is_finished():
            s.stop()
            s.clears+=1
        
        return True
        
    def undo_split(s):
        prev_seg_idx = len(s.latest_split_times)-1
        if not (s.has_started() and prev_seg_idx >= 0):
            return False
            
        was_finished = s.is_finished()
        s.latest_split_times.pop()
        if was_finished:
            s.start()
            s.clears-=1
            
        highlighted_prev = s.get_highlighted("end")
        for seg in highlighted_prev:
            seg.latest_time=None
            seg.clears -=1
        
        return True
    
    def repr(s,**kwargs):
        final = f'STRun("{s.game_name}"'
        elapsed_time = s.current_time()
        if s.category:
            final += f",\ncategory={s.category}"
        if elapsed_time:
            final += f",\nelapsed_time={elapsed_time}"
        if s.fails:
            final += f",\nfails={s.fails}"
        if s.clears:
            final += f",\nclears={s.clears}"
        if s.seg_list:
            final += f",\nseg_list_flat={s.seg_list}"
        final += ')\n'
        return final
        
    def repr_as_table(s,comp=[]):
        final=[]
        segs = s.seg_list
        def cheese(seg):
            idxr = seg.leaf_idx_range
            a,b = idxr[0],idxr[-1]
            comp_time = el_by_idx(comp,b)
            split_time = el_by_idx(s.latest_split_times,b)
            
            name=" "*(seg.depth-1)+seg.name
            clear_rate = seg.clear_rate()
            inner = [(name,clear_rate,split_time,comp_time)]
            for sseg in seg.segs:
                inner.extend(cheese(sseg))
            return inner
        for seg in segs.segs:
              final.extend(cheese(seg))
        return [STRunSegTableItem(
            e[0],clear_rate=e[1],split_time=e[2],comp_time=e[3]
            ) for e in final]
    
    def __repr__(s):
        return s.repr()           
        
        
def get_tetralogy_seg_list():            
    tetralogy = STSegmentList("Klassiche Tetralogie von Sonic",categories=["Besten Enden"])
    tetralogy.insert_segs(segs=games_list())
    return tetralogy
    
test_list = STSegmentList_v2()
test_list.insert_segs(segs=games_list())

run = STRun("Klassiche Tetralogie von Sonic",seg_list=test_list)

for i in range(1000):
    
    while random.random() < 0.90:
        run.split()
    run.restart()
    
time.sleep(1)
run.split()
time.sleep(0.5)
run.split()
time.sleep(0.1)
run.split()
time.sleep(0.2)
run.split()
time.sleep(0.05)
run.split()

    

for seg in run.repr_as_table([ 1,2,2.5,3,3.5 ]):
    print(seg)
    #tetralogy.def_idx_ranges_and_depths()
    #return tetralogy
    
