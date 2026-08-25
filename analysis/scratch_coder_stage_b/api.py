from .support import build_stage_b_data
def run_stage_b_analysis(*args,**kwargs):
 from .run_stage_b import calculate
 return calculate(*args,**kwargs)
