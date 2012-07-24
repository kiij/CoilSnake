import EbModule
from EbTablesModule import EbTable
from modules.Progress import updateProgress

import yaml
from re import sub

class MapMusicModule(EbModule.EbModule):
    _ASMPTR = 0x6939
    _name = "Map Music"
    def __init__(self):
        self._ptrTbl = EbTable("OVERWORLD_EVENT_MUSIC_PTR_TABLE")
        self._entries = []
    def readFromRom(self, rom):
        self._ptrTbl.readFromRom(rom,
                EbModule.toRegAddr(rom.readMulti(self._ASMPTR, 3)))
        updateProgress(25)
        for i in range(self._ptrTbl.height()):
            loc = 0xf0000 | self._ptrTbl[i,0].val()
            entry = [ ]
            flag = 1
            while flag != 0:
                flag = rom.readMulti(loc, 2)
                music = rom[loc+2]
                entry.append((flag, music))
                loc += 4
            self._entries.append(entry)
        updateProgress(25)
    def writeToRom(self, rom):
        self._ptrTbl.clear(165)
        writeLoc = 0xf58ef
        writeRangeEnd = 0xf61e6 # TODO Can re-use bank space from doors
        i=0
        for entry in self._entries:
            entryLen = len(entry)*4
            if writeLoc+entryLen > writeRangeEnd:
                raise RuntimeException("Not enough room for map music")
            self._ptrTbl[i,0].setVal(writeLoc & 0xffff)
            i += 1

            for (flag, music) in entry:
                rom.writeMulti(writeLoc, flag, 2)
                rom[writeLoc+2] = music
                rom[writeLoc+3] = 0
                writeLoc += 4
        updateProgress(25)
        rom.writeMulti(self._ASMPTR,
                EbModule.toSnesAddr(self._ptrTbl.writeToFree(rom)), 3)
        if writeLoc < writeRangeEnd:
            rom.addFreeRanges([(writeLoc, writeRangeEnd)])
        updateProgress(25)
    def writeToProject(self, resourceOpener):
        out = dict()
        i = 0
        for entry in self._entries:
            outEntry = []
            for (flag, music) in entry:
                outEntry.append({
                    "Event Flag": flag,
                    "Music": music })
            out[i] = outEntry
            i += 1
        updateProgress(25)
        with resourceOpener("map_music", "yml") as f:
            s = yaml.dump(out, default_flow_style=False,
                    Dumper=yaml.CSafeDumper)
            s = sub("Event Flag: (\d+)",
                    lambda i: "Event Flag: " + hex(int(i.group(0)[12:])), s)
            f.write(s)
        updateProgress(25)
    def readFromProject(self, resourceOpener):
        with resourceOpener("map_music", "yml") as f:
            input = yaml.load(f, Loader=yaml.CSafeLoader)
            for i in input:
                entry = []
                for subEntry in input[i]:
                    entry.append((subEntry["Event Flag"],
                        subEntry["Music"]))
                self._entries.append(entry)
        updateProgress(50)
