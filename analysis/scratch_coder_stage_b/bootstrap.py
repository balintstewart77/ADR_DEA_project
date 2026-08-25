from math import ceil
from random import Random
import numpy as np
from analysis.validation.bootstrap import percentile
from .config import SEED
def samples(n,attempts,seed=SEED):
 r=Random(seed);return [np.fromiter((r.randrange(n) for _ in range(n)),dtype=np.int32,count=n) for _ in range(attempts)]
def interval(values,attempts):
 v=[float(x) for x in values if x is not None];ok=len(v)>=ceil(.9*attempts);return {'lower':percentile(v,.025) if ok else None,'upper':percentile(v,.975) if ok else None,'valid':len(v),'invalid':attempts-len(v),'reported':ok}
