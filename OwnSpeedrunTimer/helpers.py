
def safe_sub(a,b):
    try:
        return a-b
    except Exception:
        return None
        
def safe_add(a,b):
    try:
        return a+b
    except Exception:
        return None
        
def safe_comp(a,b,c):
    try:
        match b:
            case ">": return a>c
            case "<": return a<c
            case "==": return a==c
            case ">=": return a>=c     
            case "<=": return a<=c              
    except Exception:
        return False

def get_delta_color(**kwargs):
    best_time = kwargs.get("best")
    split_time = kwargs.get("split")
    latest_time = kwargs.get("latest")
    mapping = kwargs.get("mapping", [
    "white","gold","green","#80FF80","red","#FF8080"
    ])
    
    if (best_time is None and split_time is None):
        return mapping[0]
        
    if safe_comp(latest_time,"<=",best_time):
        return mapping[1]
     
    if safe_comp(latest_time,">",split_time):
        return mapping[4]
        
    if safe_comp(latest_time,"<",split_time):
        return mapping[2]
        
    return mapping[0]
    
        

def el_by_idx(lst, idx, default=None):
    try:
        return lst[idx]
    except Exception:
        return default

def format_number(number,**kwargs):
    
    decimal_places = kwargs.get("decimal_places",0)
    left_pad_digits = kwargs.get("left_pad_digits",5)
    opt_plus = kwargs.get("opt_plus",False)
    show_otherwise_as = kwargs.get("show_otherwise_as","")
    
    if number is None:
        return show_otherwise_as
        
    if type(number) not in (int,float):
        return number
    
    if not decimal_places:
        return f"{round(number)}".zfill(left_pad_digits)
        
    return f"{number:{"+" if opt_plus else ""}.{decimal_places}f}".zfill(left_pad_digits+1+decimal_places)
    
    
    
    