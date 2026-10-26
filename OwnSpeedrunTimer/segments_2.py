import time
import os
from copy import deepcopy


class RawSTSegment:
    def __init__(self, name=None, **kwargs):
        self.name = name or "Segment Name"
        self.cur_subseg = kwargs.get("cur_subseg") or 0
        self.clears = kwargs.get("clears") or 0
        self.best_time = kwargs.get("best_time") or None
        self.latest_time = kwargs.get("latest_time") or 0
        self.subsegs: List[Any] = kwargs.get("subsegs") or []
        self.categories =kwargs.get("categories") or []
        self.atts = kwargs.get("atts") or 0
        self.has_started = False
        
    is_leaf = lambda self: len(self.subsegs) == 0
        
    def __repr__(self):
        condition=lambda *args: args[0].cur_subseg == args[1] or (args[0].cur_subseg==len(args[0].subsegs) and args[1] == args[0].cur_subseg-1)
        return self.repr(expand_subseg_if=condition)
        
    def repr(self,**kwargs):
        a = kwargs.get("expand_subseg_if")
        expand_subseg_if = (lambda *args: True) if a is None else a
        a = kwargs.get("expand")
        expand = True if a is None else a
        repr_text = f"RawSTSegment('{self.name}'"
        if self.cur_subseg != 0:
            repr_text+=f",cur_subseg={self.cur_subseg}"
        #if len(self.categories) != 0:
        #    categories = ",".join(self.categories)
        #    repr_text+=f",categories=[{categories}]"
        if self.best_time is not None:
            repr_text+=f",best_time={self.best_time}"
        if self.latest_time != 0:
            repr_text+=f",latest_time={self.latest_time}"
        #if self.total_time != 0:
        #    repr_text+=f",total_time={self.total_time}"
        if self.clears != 0:
            repr_text+=f",clears={self.clears}"
        if self.atts != 0:
            repr_text+=f",atts={self.atts}"
        repr_text+=")"
        
        if expand:
            if self.subsegs:
                repr_text+="\n l"
            for i,subseg in enumerate(self.subsegs):
                cur_subseg = self.cur_subseg
                repr_text += f"""\n  {"L" if cur_subseg == i else "-"} {
                subseg.repr(expand=expand_subseg_if(self,i),expand_subseg_if = expand_subseg_if)
                }"""
            if self.subsegs:
                repr_text+="\n /"
        return repr_text
        

    is_finished = lambda self: self.cur_subseg == max(len(self.subsegs),1)
    
    def start(self):
        if self.has_started:
            return False
        self.has_started = True
        self.atts+=1
        if self.subsegs:
            self.subsegs[0].start()
        return True
               
    def reset(self,**kwargs):
        if not self.has_started: return False
        
        rec_best_time = kwargs.get("rec_best_time",True)
        
        if kwargs.get("undo_attempt"):
            self.attempts-=1
        
        if rec_best_time:
            if self.best_time is None or self.best_time > self.latest_time and self.is_finished():
                self.best_time =self.latest_time
            
        self.has_started=False
        self.latest_time=0
        self.cur_subseg=0   
        for subseg in self.subsegs[::-1]:
            subseg.reset()
    
    def is_at_start(self):
        seg = self
        while not seg.is_leaf():
            if seg.cur_subseg != 0:
                return False
            seg = seg.subsegs[0]
        return seg.cur_subseg==0
    
    def split(self,delta_time):
        if not self.has_started: return "NOT STARTED"
        self.latest_time += delta_time
        if self.is_finished():
            return "ALREADY FINISHED"
        if self.is_leaf():
            self.latest_time = delta_time
            self.clears+=1
            self.cur_subseg+=1
            return True
        subseg = self.subsegs[self.cur_subseg]
        response = subseg.split(delta_time)
        if response is True:
            self.cur_subseg+=1
        is_finished = self.is_finished()
        if is_finished:
            self.clears+=1
        else:
            self.subsegs[self.cur_subseg].start()

        return is_finished

    def undo_split(self):
        if not self.has_started: return "NOT STARTED"
        if self.is_at_start(): return None
        def gaga(subseg):
            delta = subseg.undo_split()
            self.latest_time-=delta
            return delta
        def gugu():
            self.cur_subseg-=1
            subseg = self.subsegs[self.cur_subseg]
            if not subseg.is_leaf():
                return gaga(subseg)
            delta_time = subseg.latest_time
            self.latest_time-=delta_time
            
            subseg.latest_time=0
            subseg.cur_subseg=0
            
            return delta_time
        if self.is_finished():
            return gugu() 
        subseg = self.subsegs[self.cur_subseg]
        return gugu() if subseg.is_at_start() else gaga(subseg)#
        
    def insert_subsegs(self,**kwargs):
        index = kwargs.get("index")
        segs = kwargs.get("segs")
        if type(segs) is RawSTSegment: segs = [segs]
        
        for seg in segs:
            if index is None:
                self.subsegs.append(seg,1)
            else:
                self.subsegs.insert(index,seg)
                


sseg1_1 = RawSTSegment("Station 1: Schwerer Anfang!")
#sseg1_2 = RawSTSegment("Spezial 1: Es geht schnell weg.")
sseg1_3 = RawSTSegment("Station 2: Bitte dort Glas zerbrechen.")
#sseg1_4 = RawSTSegment("Spezial 2")
sseg1_5 = RawSTSegment("Station 3: Verfehle keine Treffer")

seg1 = RawSTSegment("Zone 1: ♀ 00.08 Turnhalle (Normal)",subsegs=[sseg1_1,sseg1_3,sseg1_5])

sseg2_1 = RawSTSegment("Kochnische 1: Zyklen!")
#sseg2_2 = RawSTSegment("Spezial 3: SPRING!")
sseg2_3 = RawSTSegment("Kochnische 2: Bitte verliere nicht alle Ringe!")
#sseg2_4 = RawSTSegment("Spezial 4")
sseg2_5 = RawSTSegment("Kochnische 3: Versteckter Zeitgewinn")

seg2 = RawSTSegment("Zone 2: ♂ 00.25 Hauptkochbereich",subsegs=[sseg2_1,sseg2_3,sseg2_5])

sseg3_1 = RawSTSegment("Hüpfburg 1: Mehr Zyklen")
#sseg3_2 = RawSTSegment("Spezial 5")
sseg3_3 = RawSTSegment("Hüpfburg 2: Etwas Heiklig")
#sseg3_4 = RawSTSegment("Spezial 6: SPRING!!")
sseg3_5 = RawSTSegment("Hüpfburg 3: Heikliges Timing")

seg3 = RawSTSegment("Zone 3: ♀ 00.08 Turnhalle (Hüpfburgen)",subsegs=[sseg3_1,sseg3_3,sseg3_5])

sseg4_1 = RawSTSegment("Waschbecken 1: Wasserphysik!")
sseg4_2 = RawSTSegment("Waschbecken 2: Nützlicher Sprungfeder")
sseg4_3 = RawSTSegment("Waschbecken 3: Über die Wand -> Parkourzeit")

seg4 = RawSTSegment("Zone 4: ♂ 00.11 Turnhalle-Umkleideraum",subsegs=[sseg4_1,sseg4_2,sseg4_3])

sseg5_1 = RawSTSegment("Da schauen sie ein guten Film!")
sseg5_2 = RawSTSegment("Sie schauen 'Golden' an.")
sseg5_3 = RawSTSegment("Der Film heißt KPop-Demon Hunters")

seg5 = RawSTSegment("Zone 5: ♂ 10.05 Gemüt. Gymnastikraum",subsegs=[sseg5_1,sseg5_2,sseg5_3])

sseg6_1 = RawSTSegment("Raummitte: Da wird auch Film geschaut!")
sseg6_2 = RawSTSegment("Kochnische (U-Teil): Da wird gekocht!")
sseg6_3 = RawSTSegment("Waschbekcen: So hygenisch schlau!")
sseg6_4 = RawSTSegment("[Zone 7] Kochnische (O-Teil): HEIKLIGER KAMPF!")

seg6 = RawSTSegment("Zone 6: ♀ 10.28 Gemüt. Klassenraum",subsegs=[sseg6_1,sseg6_2,sseg6_3,sseg6_4])

seg7 = RawSTSegment("Kochnische (O-Teil) (Zone 7): HEIKLIGER KAMPF!")

game1 = RawSTSegment("Sonic 1 (GBA-Umsetzung): Gutes Ende",subsegs=[seg1,seg2,seg3,seg4,seg5,seg6])

sseg1_1 = RawSTSegment("Akt 1: Mach in seine Inneren weiterhin Glas kaputt.")
sseg1_2 = RawSTSegment("Akt 2: Mehr Glass kaputt machen!")
seg1 = RawSTSegment("Zone 1: ♀ 00.08 Turnhalle (Abschiedsfeier)", subsegs=[sseg1_1,sseg1_2])

sseg2_1 = RawSTSegment("Akt 1")
sseg2_2 = RawSTSegment("Akt 2")
seg2 = RawSTSegment("Zone 2: ♀ 10.04 Chemie-Klassenraum", subsegs=[sseg2_1,sseg2_2])

sseg3_1 = RawSTSegment("Akt 1")
sseg3_2 = RawSTSegment("Akt 2")
seg3 = RawSTSegment("Zone 3: ♂ 00.21 Pflege-WC", subsegs=[sseg3_1,sseg3_2])

sseg4_1 = RawSTSegment("Akt 1")
sseg4_2 = RawSTSegment("Akt 2")
seg4 = RawSTSegment("Zone 4: ♀ 00.28 Mehrzwechraum (Casino)", subsegs=[sseg4_1,sseg4_2])

sseg5_1 = RawSTSegment("Akt 1")
sseg5_2 = RawSTSegment("Akt 2")
seg5 = RawSTSegment("Zone 5: ♀ 10.22 Lehrküche", subsegs=[sseg5_1,sseg5_2])

sseg6_1 = RawSTSegment("Akt 1")
sseg6_2 = RawSTSegment("Akt 2")
seg6 = RawSTSegment("Zone 6: ♂ 01.13 Kellerraum", subsegs=[sseg6_1,sseg6_2])

sseg7_1 = RawSTSegment("Akt 1")
sseg7_2 = RawSTSegment("Akt 2")
seg7 = RawSTSegment("Zone 7: ♂ 01.15 Werkraum", subsegs=[sseg7_1,sseg7_2])

sseg8_1 = RawSTSegment("Akt 1")
sseg8_2 = RawSTSegment("Akt 2")
sseg8_3 = RawSTSegment("Akt 3")
seg8 = RawSTSegment("Zone 8: ♂ 10.09 Technickraum", subsegs=[sseg8_1,sseg8_2,sseg8_3])

sseg9_1 = RawSTSegment("⚲ Zone 9: 10.02 Flur -> 00.16 Flur")
sseg9_2 = RawSTSegment("♂ Zone 10: 00.07 Serverraum (unten)")
sseg9_3 = RawSTSegment("♂ Zone 11: 00.07 Serverraum (oben)")

game2 = RawSTSegment("Sonic 2 (DS-Klassiksammlung)", subsegs=[seg1,seg2,seg3,seg4,seg5,seg6,seg7,seg8,sseg9_1,sseg9_2,sseg9_3])

sseg1_1 = RawSTSegment("Akt 1")
sseg1_2 = RawSTSegment("Akt 2")
seg1 = RawSTSegment("Zone 1: ♀ 00.08 Turnhalle (Veränderlich)", subsegs=[sseg1_1,sseg1_2])

sseg2_1 = RawSTSegment("Akt 1")
sseg2_2 = RawSTSegment("Akt 2")
seg2 = RawSTSegment("Zone 2: ♂ 00.11 Umkleideraum (v. 2)", subsegs=[sseg2_1,sseg2_2])

sseg3_1 = RawSTSegment("Akt 1")
sseg3_2 = RawSTSegment("Akt 2")
seg3 = RawSTSegment("Zone 3: ♀ 00.36 Kunst-Klassenraum", subsegs=[sseg3_1,sseg3_2])

sseg4_1 = RawSTSegment("Akt 1")
sseg4_2 = RawSTSegment("Akt 2")
seg4 = RawSTSegment("Zone 4: ♀ 00.28 Mehrzwechraum (Karneval)", subsegs=[sseg4_1,sseg4_2])

sseg5_1 = RawSTSegment("Akt 1")
sseg5_2 = RawSTSegment("Akt 2")
seg5 = RawSTSegment("Zone 5: ♂ 10.05 Gymnastikraum (v. 2)", subsegs=[sseg5_1,sseg5_2])

sseg6_1 = RawSTSegment("Akt 1")
sseg6_2 = RawSTSegment("Akt 2")
seg6 = RawSTSegment("Zone 6: ♂ 10.09 Technickraum (v. 2)", subsegs=[sseg6_1,sseg6_2])

sseg7_1 = RawSTSegment("Akt 1")
sseg7_2 = RawSTSegment("Akt 2")
seg7 = RawSTSegment("Zone 1: ♀ 10.28 Gemüt. Klassenraum (v. 2)", subsegs=[sseg7_1,sseg7_2])

sseg8_1 = RawSTSegment("Akt 1")
sseg8_2 = RawSTSegment("Akt 2")
seg8 = RawSTSegment("Zone 2: ♂ 00.03 Lehrerzimmer", subsegs=[sseg8_1,sseg8_2])

sseg9_1 = RawSTSegment("Akt 1")
sseg9_2 = RawSTSegment("Akt 2")
seg9 = RawSTSegment("Zone 3: ♂ 01.13 Kellerraum (v. 2)", subsegs=[sseg9_1,sseg9_2])

sseg10_1 = RawSTSegment("Akt 1")
sseg10_2 = RawSTSegment("Akt 2")
seg10 = RawSTSegment("Zone 4: ♀ 01.15 Werkraum (v. 2)", subsegs=[sseg10_1,sseg10_2])

sseg11_1 = RawSTSegment("Zone 5: ♀ 10.24 Leseclubraum (unten)")
sseg11_2 = RawSTSegment("Zone 6: ♀ 10.24 Leseclubraum (oben)")

sseg12_1 = RawSTSegment("Akt 1")
sseg12_2 = RawSTSegment("Akt 2")
seg12 = RawSTSegment("Zone 7: ♂ 00.07 Serverraum (v. 2)", subsegs=[sseg12_1,sseg12_2])

seg13 = RawSTSegment("Zone 8: Sternwarte in der ♀ 00.08 Turnhalle")

game3 = RawSTSegment("Sonic 3 (DS-Klassiksammlung)", subsegs=[seg1,seg2,seg3,seg4,seg5,seg6])

game4 = RawSTSegment("Sonic und Knuckles (DS-Klassiksammlung", subsegs=[seg7,seg8,seg9,seg10,sseg11_1,sseg11_2,seg12,seg13])

def full_run(): return [game1,game2,game3,game4]
