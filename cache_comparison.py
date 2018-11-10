import numpy as np
import json
import argparse
from queue import Queue
import math
import time
from tqdm import tqdm
import mmap
import operator

DEBUG = 0

def get_num_lines(file_path):
    fp = open(file_path, "r+")
    buf = mmap.mmap(fp.fileno(), 0)
    lines = 0
    while buf.readline():
        lines += 1
    return lines

class Cache():
    """
    Cache class that takes constructor parameters to set cache size, associativity, replacement policy and write policy.

    """
    def __init__(self, cache_size, associativity, replacement_policy, write_policy):
        """
        Constructor for Cache class.
        """
        self.cache_rows = int(cache_size/(64 * associativity))
        self.associativity = associativity

        self.offset = 6
        self.set_bits = int(math.ceil(math.log2(self.cache_rows)))

        self.dirty = np.zeros((self.cache_rows, self.associativity), dtype=np.int8)
        self.vacant = np.zeros((self.cache_rows, self.associativity), dtype=np.int8)
        self.tags = np.zeros((self.cache_rows, self.associativity), dtype=np.int64)
        self.replacement = [Queue() for x in range(self.cache_rows)]

        #1 for FIFO, 0 for LRU
        if replacement_policy == 1:
            self.replacement_policy = replacement_policy 
            self.replacement = [Queue() for x in range(self.cache_rows)]            
        else:
            self.replacement_policy = replacement_policy
            LRUs = []
            for i in range(self.cache_rows):
                temp = {}
                for i in range(self.associativity):
                    temp[i] = 0
                LRUs.append(temp)
            self.replacement = [LRUs[x] for x in range(self.cache_rows)] 

        # 0 is WT, 1 is WB     
        self.write_policy = write_policy

        self.hits = 0

        self.misses = 0

        self.reads = 0

        self.writes = 0
        

    def hex_to_binary(self, hex_value):
        temp = ""
        for i in range(17-len(hex_value)):
            temp += "0"
        hex_value = temp + hex_value
        return str(bin(int(hex_value, 16)))

    def hex_to_int(self, hex_value):
        return int(hex_value, 16)

    def get_set_tag(self, address):
        set_bits = (address/64) % self.cache_rows
        tag = address/64
        return int(tag), int(set_bits)

    def breakdown_address(self, address):
        address = address[0:-self.offset]
        set_bits = address[-self.set_bits:]
        tag = address[0:-self.set_bits]
        tag = int(tag, 2)
        set_bits = int(set_bits, 2)

        return tag, set_bits

    def cache_read(self, address):
        address = self.hex_to_binary(address)
        tag, set_bits = self.breakdown_address(address)
        if DEBUG:
            print("Tag: {}  Set: {}".format(tag, set_bits))

        if tag in self.tags[set_bits]: # Already in Cache
            self.hits += 1
            if DEBUG:
                print("Read - Hit")
            if self.replacement_policy == 0:
                index = list(self.tags[set_bits]).index(tag)
                for key in self.replacement[set_bits]:
                    if (self.vacant[set_bits][key] == 1):
                        self.replacement[set_bits][key] += 1
                self.replacement[set_bits][index] = 1


        elif (0 in self.vacant[set_bits]): # Not in Cache, but space
            self.reads += 1
            self.misses += 1
            if DEBUG:
                print("Read - Miss")
            if self.replacement_policy == 1:
                index = list(self.vacant[set_bits]).index(0)
                self.replacement[set_bits].put(index)
                self.vacant[set_bits][index] = 1
                self.tags[set_bits][index] = tag
            else:
                index = list(self.vacant[set_bits]).index(0)
                self.vacant[set_bits][index] = 1
                for key in self.replacement[set_bits]:
                    if self.vacant[set_bits][key] == 1:
                        self.replacement[set_bits][key] += 1 
                self.tags[set_bits][index] = tag
                self.replacement[set_bits][index] = 1
            

        else: # Not in Cache, Need to Replace
            self.reads += 1
            self.misses += 1
            if DEBUG:
                print("Read - Miss")
            if self.replacement_policy == 1:
                index = self.replacement[set_bits].get()
                self.tags[set_bits][index] = tag
                self.replacement[set_bits].put(index)
                if self.dirty[set_bits][index] == 1 and self.write_policy == 1:
                    self.writes += 1
            else:
                index = max(self.replacement[set_bits].items(), key=operator.itemgetter(1))[0]
                for key in self.replacement[set_bits]:
                    self.replacement[set_bits][key] += 1
                self.tags[set_bits][index] = tag
                self.replacement[set_bits][index] = 1
                if self.dirty[set_bits][index] == 1 and self.write_policy == 1:
                    self.writes += 1
            self.dirty[set_bits][index] = 0

        
        if (DEBUG):
            print("Index {}".format(index))
            if self.replacement_policy == 1:
                print("Replacement: {}".format(list(self.replacement[set_bits].queue)))
            else:
                print("Replacement: {}".format([self.replacement[set_bits][i] for i in self.replacement[set_bits]]))
            print("Vacant: {}".format(self.vacant[set_bits]))
            print()   

    def cache_write(self, address):
        address = self.hex_to_binary(address)
        tag, set_bits = self.breakdown_address(address)
        if DEBUG:
            print("Tag: {}  Set: {}".format(tag, set_bits))

        if tag in self.tags[set_bits]: # Already in Cache
            self.hits += 1
            if self.write_policy == 0:
                self.writes += 1
            if DEBUG:
                print("Write - Hit")
            if self.replacement_policy == 0:
                index = list(self.tags[set_bits]).index(tag)
                for key in self.replacement[set_bits]:
                    if (self.vacant[set_bits][key] == 1):
                        self.replacement[set_bits][key] += 1
                self.replacement[set_bits][index] = 1
                self.dirty[set_bits][index] = 1


        elif 0 in self.vacant[set_bits]: # Not in Cache, but space
            self.misses += 1
            self.reads += 1
            if DEBUG:
                print("Write - Miss")
            if self.replacement_policy == 1:
                index = list(self.vacant[set_bits]).index(0)
                self.replacement[set_bits].put(index)
                self.vacant[set_bits][index] = 1
                self.tags[set_bits][index] = tag
            else:
                index = list(self.vacant[set_bits]).index(0)
                self.vacant[set_bits][index] = 1
                for key in self.replacement[set_bits]:
                    if self.vacant[set_bits][key] == 1:
                        self.replacement[set_bits][key] += 1 
                self.tags[set_bits][index] = tag
                self.replacement[set_bits][index] = 1

            if self.write_policy == 0:
                self.writes += 1

        else: # Not in Cache, Need to Replace
            self.misses += 1
            self.reads += 1
            if DEBUG:
                print("Write - Miss")
            if self.replacement_policy == 1:
                index = self.replacement[set_bits].get()
                self.tags[set_bits][index] = tag
                self.replacement[set_bits].put(index)
            else:
                index = max(self.replacement[set_bits].items(), key=operator.itemgetter(1))[0]
                for key in self.replacement[set_bits]:
                    self.replacement[set_bits][key] += 1
                self.tags[set_bits][index] = tag
                self.replacement[set_bits][index] = 1

            if self.write_policy == 0 or (self.write_policy == 1 and self.dirty[set_bits][index] == 1):
                self.writes += 1
                self.dirty[set_bits][index] = 0

        if (DEBUG):#0 in self.vacant[set_bits]):
            print("Index {}".format(index))
            if self.replacement_policy == 1:
                print("Replacement: {}".format(list(self.replacement[set_bits].queue)))
            else:
                print("Replacement: {}".format([self.replacement[set_bits][i] for i in self.replacement[set_bits]]))
            print("Vacant: {}".format(self.vacant[set_bits]))
            print()    

def execute_trace(cache, trace_file):
    f = open(trace_file, 'r')

    for line in tqdm(f, total=get_num_lines(trace_file)):
        if line[0] == 'W':
            cache.cache_write(line[4:])
        else:
            cache.cache_read(line[4:])
        
    return cache


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("cache_size", type=int,
                        help="the total size of the cache")
    parser.add_argument("associtativity", type=int,
                        help="the associativity of the cache")
    parser.add_argument("replacement_policy", type=int,
                        help="the replacement policy of the cache")
    parser.add_argument("write_policy", type=int,
                        help="the write policy of the cache")
    parser.add_argument("tracefile", type=str,
                        help="the trace file to run the cache on")
    args = parser.parse_args()

    cache = Cache(args.cache_size, args.associtativity, args.replacement_policy, args.write_policy)
    trace = args.tracefile

    results = execute_trace(cache, trace)

    print("Hit Ratio: {}, Writes: {}, Reads: {}".format((results.misses / (results.hits + results.misses)), results.writes, results.reads))



if __name__ == "__main__":
    main()
    #results = Cache(32768, 8, 0, 1)
    
    
    #results = execute_trace(results, 'XSBENCH.t')
    


    #print("Hit Ratio: {}, Writes: {}, Reads: {}, Total Lines: {}".format((results.misses / (results.hits + results.misses)), results.writes, results.reads, (results.hits + results.misses)))



