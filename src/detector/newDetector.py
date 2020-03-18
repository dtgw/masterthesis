#!/usr/bin/env python3

import sys
from newDie import DetectItEasy
from newPeframe import Peframe
from newManalyze import Manalyze

class Malware:
    def __init__(self, date, path):
        splited_path = path.split("/")
        self.date = date
        self.path = path


def main():
    date = sys.argv[1]
    path = sys.argv[2]
    malware = Malware(date, path)
    die = DetectItEasy(malware)
    peframe = Peframe(malware)
    manalyze = Manalyze(malware)
    print("die: {}".format(die.analyze()))
    print("peframe: {}".format(peframe.analyze()))
    print("manalyze: {}".format(manalyze.analyze()))

if __name__ == '__main__':
    main()
