import time
import os
from copy import deepcopy
from segments_3 import RawSTSegment, games_list
from helpers import el_by_idx, safe_sub
import random

class STComparison:
    def __init__(s,name,times,_type="Split"):
        s.name = name
        s.times = times
        s._type = _type

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
        s.comparisons = kwargs.get("comparisons",[])
        if not s.comparisons:
            s.comparisons.append(STComparison("PB",[]))
        
        s.seg_list = kwargs.get("seg_list",[])
        s.seg_list.def_idx_ranges_and_depths()
        s.seg_list_flat = s.seg_list.flatten()
        s.leave_count = s.seg_list.count_leaves()
        s.latest_split_times = []
        s.elapsed_time = 0
        
        s.timer_started_at = None 
        s.timer_stopped_at = None
        s.has_started = False
        
    
    is_finished = lambda s: len(s.latest_split_times) == s.leave_count
    timer_is_running = lambda s: s.has_started and (s.timer_stopped_at is None)
    
    clear_rate = lambda s: f"{s.clears}/{s.clears+s.fails}"
    
    def get_highlighted(s,c="end"):
        match c:
            case "end": return [e for e in s.seg_list_flat if e.leaf_idx_range[-1] == len(s.latest_split_times)]
            case "start": return [e for e in s.seg_list_flat if e.leaf_idx_range[0] == len(s.latest_split_times)]
            case "current": return [e for e in s.seg_list_flat if len(s.latest_split_times) in e.leaf_idx_range]
            case "prev": return [e for e in s.seg_list_flat if len(s.latest_split_times)-1 in e.leaf_idx_range]
    
    def current_time(s):
        return (s.timer_stopped_at or time.perf_counter())-(s.timer_started_at or time.perf_counter()) if s.has_started else 0

    def segment_time_by_split_times(s,idx1=None,idx2=None):
        if idx1 is None:
            idx1 = len(s.latest_split_times)-s.is_finished()
        if idx2 is None:
            idx2 = len(s.latest_split_times)-s.is_finished()
            
        if idx2 < idx1: idx1,idx2 = idx2,idx1

        cur_time = s.current_time()
        time2 = el_by_idx(s.latest_split_times,idx2,cur_time)
        time1 = el_by_idx(s.latest_split_times,idx1-1,cur_time) if idx1 != 0 else 0
        return safe_sub(time2,time1) or 0

    def check_for_pb(s):
        if len(s.latest_split_times) > len(s.comparisons[0].times):
            return True
        return False

    def reset(s):
        if not s.has_started:
            return False
        
        check = s.check_for_pb()
        if check:
            s.comparisons[0] = STComparison("PB",s.latest_split_times)
         
        s.has_started = False
        if not s.is_finished():
            s.fails+=1
        
        for seg in s.get_highlighted("current"):
            seg.fails+=1
        
        s.timer_started_at = None 
        s.timer_stopped_at = None
        s.elapsed_time=0
        s.latest_split_times = []
        return True
        
        def cheese(seg):
            for sseg in seg.segs:
                cheese(sseg)
            seg.latest_time = None
        for seg in s.seg_list.segs:
            cheese(seg)

    def start(s):
        s.has_started=True
        s.elapsed_time = s.current_time()
        if s.is_finished():
            return False
        
        s.timer_started_at = time.perf_counter()-s.elapsed_time
        s.timer_stopped_at = None
        
    def stop(s):
        if not s.has_started:
            return False
        timer_is_running = s.timer_is_running()
        if timer_is_running:
            s.timer_stopped_at = time.perf_counter()
            return True
        return False
            
    def restart(s):
        s.reset()
        s.start()
    
    def split(s):
        if s.is_finished() or not s.has_started:
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
        if not (s.has_started and prev_seg_idx >= 0):
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
        
    def repr_as_table_view(s,comp_idx,expand_only_highlighted=True):
        final=[]
        comp = s.comparisons[comp_idx]
        segs = s.seg_list
        highlighted = s.get_highlighted("current") or s.get_highlighted("prev")
        def cheese(seg):
            idxr = seg.leaf_idx_range
            a,b = idxr[0],idxr[-1]
            comp_time = el_by_idx(comp.times,b)
            split_time = el_by_idx(s.latest_split_times,b)
            
            name=" "*(seg.depth-1)+seg.name
            clear_rate = seg.clear_rate()
            highlight = (seg in highlighted)*1
            inner = [(highlight,name,clear_rate,split_time,comp_time,seg.icon)]
            if expand_only_highlighted or highlight:
                for sseg in seg.segs:
                    inner.extend(cheese(sseg))
            return inner
        for seg in segs.segs:
              final.extend(cheese(seg))
        return final
        
    def repr_as_crunched_table_view(s, comp_idx, no_of_segs, **kwargs):
        always_show_last_seg = True
        view = deepcopy(s.repr_as_table_view(comp_idx)) # ORIGINAL VIEW
        last_highlight_idx = len(view) - next(i for i, v in enumerate(view[::-1]) if v[0]) - 1
        last_seg = view.pop() #VIEW -> ORIGINAL WITHOUT LAST
        second_last_seg=None if not view else view[-1]
        segs_to_remove = last_highlight_idx-no_of_segs+1+min(1+2,len(view)-last_highlight_idx)
        segs_removed = 0
        idx = 0
        while segs_to_remove > segs_removed:
            if not view[idx][0]:
                view.pop(idx)
                segs_removed+=1
            else:
                idx+=1
            
        view = view[0:no_of_segs-1]
        view.append(last_seg)
        
        return (len(view) >= 2 and second_last_seg != view[-2],view)
        
    
    def __repr__(s):
        return s.repr()           
        
        
def get_tetralogy_seg_list():            
    tetralogy = STSegmentList("Klassiche Tetralogie von Sonic",categories=["Besten Enden"])
    tetralogy.insert_segs(segs=games_list())
    return tetralogy


#for seg in run.repr_as_table_view(comp=pb_comp):
   # print(seg)

    #tetralogy.def_idx_ranges_and_depths()
    #return tetralogy
    
