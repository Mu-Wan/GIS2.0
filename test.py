import numpy as np


def run_main(d, k, v):
    d[k] = v


if __name__ == "__main__":
    arr = [(1, 2, 3, 4, 5),
           (11, 12, 13, 14, 15),
           (21, 22, 23, 24, 25),
           (31, 32, 33, 34, 35)]
    arr = np.array(arr)
    print(np.max(arr[:, 2]))
