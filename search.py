#!/usr/bin/env python

import sys
import zlib
from re import finditer

import redis
import msgpack

r = redis.Redis()
sequences = msgpack.loads(r.get("seq_dict"))

def _contains(str1, str2, distance_min=None, distance_max=None):
    """ Check if search strings exist in DB separated by distance. """

    matches = {}

    str1 = str1.upper()
    str2 = str2.upper()
    str1l = len(str1)

    # Set the defaults
    if distance_min is None:
        distance_min = 0

    if distance_max is None:
        distance_max = distance_min

    for seq in sequences:
        if str1 in seq and str2 in seq:
            s1idx = [m.start() for m in finditer('(?=%s)' % str1, seq)]
            if str1 == str2:
                s2idx = s1idx
            else:
                s2idx = [m.start() for m in finditer('(?=%s)' % str2, seq)]

            for idx in s1idx:
                for diter in range(distance_min + str1l + idx, distance_max + 1 + str1l + idx):
                    if diter in s2idx:
                        for pdb in set(sequences[seq]):
                            try:
                                matches[pdb].add((idx, diter - str1l - idx))
                            except KeyError:
                                matches[pdb] = set([(idx, diter- str1l - idx)])

    clean_res = []

    for pdb in sorted(matches.keys()):
        clean_res.append((pdb, sorted(matches[pdb])))

    return clean_res

def _fake_redis(pdbs):
    """ Debug method to use FS rather than Redis."""

    for pdb in pdbs:
        try:
            yield open("/zfs/mmtfs/%s" % pdb,"r").read()
        except IOError:
            yield None

def get_coords(str1, str2, distance_min, distance_max=None):
    """ Returns a list of mmtf objects for PDB IDs that have str1 separated
    from str2 by distance_min, or if distance_max is provided, that have str1
    separated from str2 by any distance in the range
    [distance_min - distance_max]."""

    pdbs = _contains(str1, str2, distance_min, distance_max)

    pure_ids = [x[0] for x in pdbs]

    try:
        mmtfs = r.mget(pure_ids)
    except Exception:
        mmtfs = _fake_redis(pure_ids)

    for x,pdb in enumerate(mmtfs):

        if not pdb:
            raise ValueError("Could not find PDB %s in Redis!" % pdbs[x])

        yield [pdbs[x], _extract_coords(pdb, pure_ids[x])]

def _extract_coords(data, pdb):
    """ Turns the compressed msgpack data into something useful. """

    try:
        return msgpack.loads(data)
    except Exception:
        print ("Error: %s" % pdb)

if __name__ == "__main__":
    list(get_mmtfs("AAA", "AAA", 6))

#https://stackoverflow.com/questions/30057240/whats-the-fastest-way-to-save-load-a-large-list-in-python-2-7
#https://docs.scipy.org/doc/numpy/reference/generated/numpy.array.html
