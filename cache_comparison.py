import numpy as np
import json

class Cache():
    '''''
    Cache class that takes constructor parameters to set cache size, associativity, replacement policy and write policy.

    '''''
    def __init__(self, cache_size, associtativity, replacement_policy, write_policy):
        '''''
        Constructor for Cache class.
        '''''
        self.cache_rows = int(cache_size/associtativity)
        self.associtativity = associtativity

        self.cache = np.zeros((self.cache_rows, self.associtativity), dtype=np.int64)
        self.tags = np.zeros((self.cache_rows, self.associtativity), dtype=np.int32)
        self.dirty = np.zeros((self.cache_rows, self.associtativity), dtype=np.int8)


        if replacement_policy == 0:
            self.replacement_policy = self.least_recently_used
        else:
            self.replacement_policy = self.fifo

        if write_policy == 0:
            self.write_policy = self.write_through
        else:
            self.write_policy = self.write_back

    def hex_to_binary(self, hex_value):
        return str(bin(int(hex_value, 16)))[2:]

    def cache_read(self):
        return 0

    def cache_write(self):
        return 0

    def least_recently_used(self):
        return 0

    def fifo(self):
        return 0

    def write_back(self):
        return 0

    def write_through(self):
        return 0

    def report_outcome(self):
        return 0


def run_tests():
    return 0

def execute_trace(cache, trace_file):
    f = open(trace_file, 'r')

    for line in f:
        if line[0] == 'W':
            cache.cache_write(line[4:])
        else:
            cache.cache_read(line[4:])


if __name__ == "__main__":
