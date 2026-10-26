import os
import time
from segments_2 import RawSTSegment, full_run

class STSegmentList:
    def __init__(self, **kwargs):
        self.name: str = kwargs.get("name")
        self.current_segment: int = 0
        self.segments: List[RawSTSegment] = kwargs.get("segments")
        self.has_started = False
        self.latest_time: int = 0
        self.best_time: int|None = None
        self.attempts: int = 0
        self.clears: int = 0
        
    def __repr__(self):
        condition1=lambda *args: args[0].current_segment == args[1] or (args[0].current_segment==len(args[0].segments) and args[1] == args[0].current_segment-1)
        return self.repr(expand_seg_if=condition1)
    
    def repr(self,**kwargs):
        a = kwargs.get("expand_seg_if",lambda *args: True)
        expand_seg_if = (lambda *args: True) if a is None else a
        condition2=lambda *args: args[0].cur_subseg == args[1] or (args[0].cur_subseg==len(args[0].subsegs) and args[1] == args[0].cur_subseg-1)
        
        final = "STSegmentList(segments=[\n"
        
        for i,seg in enumerate(self.segments):
            final += seg.repr(expand=expand_seg_if(self,i),expand_subseg_if=condition2 )+ ",\n"
        final+=f"]"
        
        if self.latest_time:
            final+=f",latest_time={self.latest_time}"
        if self.clears:
            final+=f",clears={self.clears}"            
        if self.attempts:
            final+=f",attempts={self.attempts}"   
        
        final+=")"
        
        return final
    
    def start(self):
        if self.has_started: return False
        self.attempts+=1
        self.has_started = True
        if self.segments:
            self.segments[0].start()
        return True
            
    def reset(self):
        if not self.has_started: return False
        
        self.latest_time=0
        self.current_segment=0
        self.has_started=False
        
        for seg in self.segments[::-1]:
            seg.reset()
    
    def split(self, delta_time):
        if not self.has_started: return "NOT STARTED"
        self.latest_time += delta_time
        if self.is_finished():
            return "ALREADY FINISHED"
        if len(self.segments)==0:
            self.latest_time = delta_time
            self.clears+=1
            self.current_segment+=1
            return True
        segment = self.segments[self.current_segment]
        response = segment.split(delta_time)
        if response is True:
            self.current_segment+=1
        is_finished = self.is_finished()
        if is_finished:
            self.clears+=1
        else:
            self.segments[self.current_segment].start()
        return is_finished
        
    is_finished = lambda self: self.current_segment == max(len(self.segments),1)
    
        

full_game = STSegmentList(name="Die klassische Sonic-Spiele Quadrologie",segments=full_run())
full_game.start()
#print(full_game)


while not full_game.is_finished():
    full_game.split(100)
os.system("cls")
print(full_game)
time.sleep(2)

full_game.reset()
full_game.start()

for i in range(30):
    full_game.split(120)
    
full_game.reset()
full_game.start()
os.system("cls")

for i in range(64):
    full_game.split(100)
#os.system("cls")
print(full_game)