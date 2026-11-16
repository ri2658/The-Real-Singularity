import glob
import numpy as np

for path in sorted(glob.glob("data/reference/*.npz")):
    ref = np.load(path)
    print(path)
    for k in ref.files:
        v = ref[k]
        # arrays: show shape; single numbers (like nu): show the value
        print("   ", k, v.shape, v.dtype, v if v.size == 1 else "")