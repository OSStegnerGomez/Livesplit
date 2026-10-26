import time
import os
from copy import deepcopy


class RawSTSegment:
    def __init__(self, name=None, **kwargs) -> None:
        self.name = name or ""
        self.clears = kwargs.get("clears") or 0
        self.best_time = kwargs.get("best_time")
        self.latest_time = kwargs.get("latest_time")
        self.icon = kwargs.get("icon")
        self.segs: List[Any] = kwargs.get("segs") or []
        self.categories = kwargs.get("categories") or []
        self.fails = kwargs.get("fails") or 0
        self.leaf_idx_range = None
        self.depth = None
        
    is_leaf = lambda self: len(self.segs) == 0
    clear_rate = lambda s: f"{s.clears}/{s.clears+s.fails}"

    
    def insert_seg(self,subseg,index=None):
        if index is None:
            self.segs.append(subseg)
        else:
            self.segs.insert(index, subseg)
    
    def insert_segs(self,**kwargs) -> None:
        index = kwargs.get("index")
        subsegs = kwargs.get("segs")
        if type(subsegs) is RawSTSegment:
            subsegs = [subsegs]
            
        if index is None:
            for seg in subsegs:
                self.segs.append(seg)
        else:
            for seg in subsegs[::-1]:
                self.segs.insert(index,seg)
    
    def remove_seg(self,index=None) -> RawSTSegment:
        if index is None:
            return self.segs.pop()
        else:
            return self.segs.pop(index)
            
    def repr(self,**kwargs):
        
        str_blocks = [f'RawSTSegment("{self.name}"']
        #if self.leaf_idx_range:
        #    str_blocks.append(f"leaf_idx_range={self.leaf_idx_range}")
        if self.depth is not None:
            str_blocks.append(f"\ndepth={self.depth}")
        if self.latest_time:
            str_blocks.append(f"\nlatest_time={self.latest_time}")
        if self.fails:
            str_blocks.append(f"\nfails={self.fails}")  
        if self.clears:
            str_blocks.append(f"\nclears={self.clears}")            
            
        show_segs = kwargs.get("show_segs",True)
        if self.segs and show_segs:
            str_block = "\nsegs=[\n"
            str_block+=",\n".join([seg.repr(**kwargs) for seg in self.segs])
            
            str_block += "\n]"
            str_blocks.append(str_block)
            
        final = ",".join(str_blocks)+")"
        return final
            
        
        
        #final = f'RawSTSegment("{self.name}"'
        #if self.leaf_idx_range:
        #    final += f",leaf_idx_range={self.leaf_idx_range}"
        #if self.depth is not None:
        #    final += f",depth={self.depth}"
        #show_segs = kwargs.get("show_segs",True)
        #if self.segs and show_segs:
        #    final += f', segs=[\n{"".join([e.repr() for e in self.segs])}]'
        #
        #final += '),'
        #final = final[:-1]
        #return final
        
    def __repr__(self):
        return self.repr()
        
    def count_leaves(self):
       if self.is_leaf():
           return 1
       leafs = 0
       for seg in self.segs:
           leafs+=seg.count_leaves()
       return leafs
       
    def truncate(self):
        self.segs = []
        
            

get_acts = lambda x: [RawSTSegment(f"Act {i+1}") for i in range(x)]

full_run = RawSTSegment("Sonic: Klassische Quadrologie")

games = [
RawSTSegment("Sonic 1 (GBA-Umsetzung)"),
RawSTSegment("Sonic 2 (DS-Klassiksammlung)"),
RawSTSegment("Sonic 3 und Knuckles (DS-Klassiksammlung)")
]
zone_a1 = RawSTSegment("Zone A1: 00.08 Turnhalle (Normal)")

zone_a1.insert_seg(RawSTSegment("Akt/Station 1: Was für ein schwerer Anfang!"))
zone_a1.insert_seg(RawSTSegment("Spezial 1: Triff die ersten 2 R-Symbole."))
zone_a1.insert_seg(RawSTSegment("Akt/Station 2: 21 Sek. oder Schneller"))
zone_a1.insert_seg(RawSTSegment("Spezial 2: Verfehle das Loch nicht."))
zone_a1.insert_seg(RawSTSegment("Akt/Station 3: Verfehle keine Treffer."))

zone_a2 = RawSTSegment("Zone A2: 00.25 Hauptkochbereich")

zone_a2.insert_seg(RawSTSegment("Akt/Kochnische 1: ZYKLEN!"))
zone_a2.insert_seg(RawSTSegment("Spezial 3: SPRING!"))
zone_a2.insert_seg(RawSTSegment("Akt/Kochnische 2: Bitte keine Ringe verlieren."))
zone_a2.insert_seg(RawSTSegment("Spezial 4: Drücken Sie R-Symbole 1- oder 3-mal."))
zone_a2.insert_seg(RawSTSegment("Akt/Kochnische 3: Versteckter Zeitgewinn."))


zone_a3 = RawSTSegment("Zone A3: 00.08 Turnhalle (Hüpfburgen)")

zone_a3.insert_seg(RawSTSegment("Akt/Hüpfburg 1: MEHR ZYKLEN!"))
zone_a3.insert_seg(RawSTSegment("Spezial 5: Das längste Spezial."))
zone_a3.insert_seg(RawSTSegment("Akt/Hüpfburg 2: Es ist etwas heiklig."))
zone_a3.insert_seg(RawSTSegment("Spezial 6: Das kürzeste Spezial."))
zone_a3.insert_seg(RawSTSegment("Akt/Hüpfburg 3: Es ist auch heiklig."))


zone_a4 = RawSTSegment("Zone A4: 00.11 Turnhalle-Umkleideraum")
zone_a4.insert_seg(RawSTSegment("Akt/Waschbecken 1: WASSERPHYSIK!"))
zone_a4.insert_seg(RawSTSegment("Akt/Waschbecken 2: Nützlicher Sprungfeder."))
zone_a4.insert_seg(RawSTSegment("Akt/Waschbecken 3: Über die Wand -> Parkour"))


zone_a5 = RawSTSegment("Zone A5: 10.05 Gemüt. Gymnastikraum")
zone_a5.insert_seg(RawSTSegment("Akt 1: Sie machen jetzt dort Yoga!"))
zone_a5.insert_seg(RawSTSegment("Akt 2: Jetzt machen sie dort TANZ-AG."))
zone_a5.insert_seg(RawSTSegment("Akt 3: Jetzt schauen sie dort KPop Demon Hunters!"))


zone_a6 = RawSTSegment("Zone A6: 10.28 Gemüt. Klassenraum")
zone_a6.insert_seg(RawSTSegment("Akt 1 [Raummitte]: Da wird Spider Man 2019 geschaut!"))
zone_a6.insert_seg(RawSTSegment("Akt 2 [Kü. (U-Teil)]: Da wird leckeres Essen gekocht!"))
zone_a6.insert_seg(RawSTSegment("Akt 3 [Waschbecken]: Das ist so hygenisch schlau!"))
zone_a6.insert_seg(RawSTSegment("Akt 4 [Kü. (O-Teil)]: DAS IST EIN HEIKLIGER KAMPF!"))


zone_b1 = RawSTSegment("Zone B1: 00.08 Turnhalle (Abschiedsfeier)")
zone_b1.insert_segs(segs=get_acts(2))
zone_b2 = RawSTSegment("Zone B2: 10.04 Klassenraum (Chemie)")
zone_b2.insert_segs(segs=get_acts(2))
zone_b3 = RawSTSegment("Zone B3: 00.21 Pflege-WC")
zone_b3.insert_segs(segs=get_acts(2))
zone_b4 = RawSTSegment("Zone B4: 00.28 Mehrzweckraum (Casino)")
zone_b4.insert_segs(segs=get_acts(2))
zone_b5 = RawSTSegment("Zone B5: 10.22 Lehrküche ")
zone_b5.insert_segs(segs=get_acts(2))
zone_b6 = RawSTSegment("Zone B6: 01.13 Kellerraum")
zone_b6.insert_segs(segs=get_acts(2))
zone_b7 = RawSTSegment("Zone B7: 01.15 Werkraum")
zone_b7.insert_segs(segs=get_acts(2))
zone_b8 = RawSTSegment("Zone B8: 10.09 Technickraum")
zone_b8.insert_segs(segs=get_acts(3))
zone_b9 = RawSTSegment("Zone B9: 10.02 Flur -> 00.16 Flur ")
zone_b10 = RawSTSegment("Zonen B10/B11: 00.07 Serverraum")
zone_b10_1 = RawSTSegment("Zone B10 (unten)")
zone_b10_2 = RawSTSegment("Zone B11 (oben)")
zone_b10.insert_segs(segs=[zone_b10_1,zone_b10_2])

zone_c1 = RawSTSegment("Zone C1: 00.08 Turnhalle (Veränderlich)")
zone_c1.insert_segs(segs=get_acts(2))
zone_c2 = RawSTSegment("Zone C2: 00.11 Turnhalle-Umkleideraum")
zone_c2.insert_segs(segs=get_acts(2))
zone_c3 = RawSTSegment("Zone C3: 00.32 Klassenraum (Kunst)")
zone_c3.insert_segs(segs=get_acts(2))
zone_c4 = RawSTSegment("Zone C4: 00.28 Mehrzweckraum (Karneval)")
zone_c4.insert_segs(segs=get_acts(2))
zone_c5 = RawSTSegment("Zone C5: 10.05 Gymnastikraum (v.2)")
zone_c5.insert_segs(segs=get_acts(2))
zone_c6 = RawSTSegment("Zone C6: 10.07 Klassenraum (Technick)")
zone_c6.insert_segs(segs=get_acts(2))

zone_d1 = RawSTSegment("Zone C7: 00.36 Klassenraum (Biologie)")
zone_d1.insert_segs(segs=get_acts(2))
zone_d2 = RawSTSegment("Zone C8: 00.03 Lehrerzimmer")
zone_d2.insert_segs(segs=get_acts(2))
zone_d3 = RawSTSegment("Zone C9: 01.13 Kellerraum (v. 2)")
zone_d3.insert_segs(segs=get_acts(2))
zone_d4 = RawSTSegment("Zone C10: 01.15 Werkraum (v. 2)")
zone_d4.insert_segs(segs=get_acts(2))
zone_d5 = RawSTSegment("Zonen C11/C12: 10.24 Leseclubraum")
zone_d5_1 = RawSTSegment("Zone C11 (unten)")
zone_d5_2 = RawSTSegment("Zone C12 (oben)")
zone_d5.insert_segs(segs=[zone_d5_1,zone_d5_2])
zone_d7 = RawSTSegment("Zone C13: 00.07 Serverraum (v. 2)")
zone_d7.insert_segs(segs=get_acts(2))
zone_d8 = RawSTSegment("Zone C14: 00.08 Turnhalle (Sternwarte)")

full_run.insert_segs(segs=games)

games[0].insert_segs(segs=[zone_a1,zone_a2,zone_a3,zone_a4,zone_a5,zone_a6])

games[1].insert_segs(segs=[
zone_b1,zone_b2,zone_b3,zone_b4,zone_b5,zone_b6,zone_b7,zone_b8,zone_b9,zone_b10
])

games[2].insert_segs(segs=[zone_c1,zone_c2,zone_c3,zone_c4,zone_c5,zone_c6,zone_d1,zone_d2,zone_d3,zone_d4,zone_d5,zone_d7,zone_d8])

#for i in range(2): full_run.remove_subseg(2)
                      
def games_list():
    return games