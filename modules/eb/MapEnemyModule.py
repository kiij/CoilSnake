import EbModule
from EbTablesModule import EbTable
from modules.Progress import updateProgress

import yaml
from re import sub

class MapEnemyModule(EbModule.EbModule):
    _name = "Map Enemies"
    def __init__(self):
        self._mapGroupPtrTbl = EbTable("ENEMY_PLACEMENT_GROUPS_PTR_TABLE")
        self._mapEnemyTbl = EbTable("ENEMY_PLACEMENT_DATA")
    def freeRanges(self):
        return [(0x10BBAC, 0x10C6AC)] # Groups data
    def readFromRom(self, rom):
        self._mapEnemyTbl.readFromRom(rom)
        updateProgress(2.5)
        self._mapGroupPtrTbl.readFromRom(rom)
        updateProgress(2.5)

        # Read the groups
        pct = 45.0/(self._mapGroupPtrTbl.height())
        self._mapGroups = []
        for i in range(self._mapGroupPtrTbl.height()):
            loc = EbModule.toRegAddr(self._mapGroupPtrTbl[i,0].val())
            flag = rom.readMulti(loc, 2)
            rate1 = rom[loc+2]
            rate2 = rom[loc+3]
            loc += 4

            # Read the enemies/probabilities
            group1 = [ ]
            if rate1 > 0:
                sum = 0
                while sum < 8:
                    prob = rom[loc]
                    enemy = rom.readMulti(loc+1, 2)
                    sum += prob
                    loc += 3
                    group1.append((prob, enemy))
            group2 = [ ]
            if rate2 > 0:
                sum = 0
                while sum < 8:
                    prob = rom[loc]
                    enemy = rom.readMulti(loc+1, 2)
                    sum += prob
                    loc += 3
                    group2.append((prob, enemy))

            # Add to the list
            self._mapGroups.append((flag, rate1, rate2, group1, group2))
            updateProgress(pct)
    def writeToRom(self, rom):
        self._mapEnemyTbl.writeToRom(rom)
        updateProgress(2.5)
        self._mapGroupPtrTbl.clear(len(self._mapGroups))
        updateProgress(2.5)

        pct = 42.5/len(self._mapGroups)
        i = 0
        for (flag, rate1, rate2, subg1, subg2) in self._mapGroups:
            size = 4
            if rate1 > 0:
                size += len(subg1) * 3
            if rate2 > 0:
                size += len(subg2) * 3
            loc = rom.getFreeLoc(size)
            self._mapGroupPtrTbl[i,0].setVal(EbModule.toSnesAddr(loc))

            rom.writeMulti(loc, flag, 2)
            rom[loc+2] = rate1
            rom[loc+3] = rate2
            loc += 4
            for prob, egroup in subg1:
                rom[loc] = prob
                rom.writeMulti(loc+1, egroup, 2)
                loc += 3
            for prob, egroup in subg2:
                rom[loc] = prob
                rom.writeMulti(loc+1, egroup, 2)
                loc += 3
            i += 1
            updateProgress(pct)
        self._mapGroupPtrTbl.writeToRom(rom)
        updateProgress(2.5)
                
    def writeToProject(self, resourceOpener):
        self._mapEnemyTbl.writeToProject(resourceOpener)
        updateProgress(2.5)

        # Write the groups
        pct=42.5/len(self._mapGroups)
        out = dict()
        i=0
        for (flag, rate1, rate2, group1, group2) in self._mapGroups:
            # Generate first enemy/prob list
            g1out = dict()
            j=0
            for prob, enemy in group1:
                g1out[j] = { "Enemy Group": enemy,
                        "Probability": prob }
                j += 1
            g2out = dict()
            j=0
            for prob, enemy in group2:
                g2out[j] = { "Enemy Group": enemy,
                        "Probability": prob }
                j += 1
            out[i] = {
                    "Event Flag": flag,
                    "Sub-Group 1 Rate": rate1,
                    "Sub-Group 1": g1out,
                    "Sub-Group 2 Rate": rate2,
                    "Sub-Group 2": g2out }
            i += 1
            updateProgress(pct)
        s = yaml.dump(out, Dumper=yaml.CSafeDumper)
        updateProgress(2.5)
        s = sub("Event Flag: (\d+)",
                lambda i: "Event Flag: " + hex(int(i.group(0)[12:])), s)
        with resourceOpener("map_enemy_groups", "yml") as f:
            f.write(s)
        updateProgress(2.5)
    def readFromProject(self, resourceOpener):
        self._mapEnemyTbl.readFromProject(resourceOpener)
        updateProgress(5)

        pct = 40.0/203
        self._mapGroups = [ ]
        with resourceOpener("map_enemy_groups", "yml") as f:
            input = yaml.load(f, Loader=yaml.CSafeLoader)
            updateProgress(5)
            for gid in input:
                group = input[gid]
                flag = group["Event Flag"]
                rate1 = group["Sub-Group 1 Rate"]
                rate2 = group["Sub-Group 2 Rate"]

                subg1 = [ ]
                if rate1 > 0:
                    for eid in group["Sub-Group 1"]:
                        entry = group["Sub-Group 1"][eid]
                        subg1.append((entry["Probability"], entry["Enemy Group"]))
                subg2 = [ ]
                if rate2 > 0:
                    for eid in group["Sub-Group 2"]:
                        entry = group["Sub-Group 2"][eid]
                        subg2.append((entry["Probability"], entry["Enemy Group"]))
                self._mapGroups.append(
                        (flag, rate1, rate2, subg1, subg2))
                updateProgress(pct)
