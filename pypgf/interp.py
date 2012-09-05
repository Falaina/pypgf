import numpy as np
from scipy.signal import decimate
l = range(128)
print l

def downsample(l, factor):
   chunks = len(l)/factor
   new_l = []

   for i in range(chunks):
      idx = i * factor
      new_l.append(sum(l[idx:idx+factor])/factor)

   return new_l

print downsample(l, 32)
