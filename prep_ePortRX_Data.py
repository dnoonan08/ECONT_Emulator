import argparse
import pandas as pd
import numpy as np

import warnings

allowedFastCommands = ['ocr','bcr']

def convertToBin(val, nBits=32):
    return format(val, f'#0{nBits+2}b')[2:]
    
def convertToHex(val, nBits=8, fromBin=False):
    if fromBin:
        return format(int(val,2), f'#0{nBits+2}x')
    else:
        return format(val, f'#0{nBits+2}x')
    
def parseConfig(configName):
    offsetChanges = []
    fastCommands = []

    with open(configName,'r') as configFile:
        for i, line in enumerate(configFile):
            #remove newline character
            line = line.replace('\n','')

            #allow # as a comment
            if '#' in line:
                line = line.split('#')[0]
            if len(line)==0: continue

            #remove leading or trailing spaces            
            while line[-1]==' ': 
                line = line[:-1]
            while line[0]==' ': 
                line = line[1:]

            values = line.split(' ')

            if values[2].lower()=='offset':
                if not len(values)==5:
                    print('-'*20)
                    print(f'  Unable to parse config file line {i}, "{line}"')
                    print(f'  Five values expected but only {len(values)} found')
                    print('  Expected: GodOrbit GodBucket OFFSET ePortNumber NewOffset')
                    continue
                offsetChanges.append([int(values[0]),int(values[1]),int(values[3]),int(values[4])])
            if values[2].lower() in allowedFastCommands:
                fastCommands.append([values[3].lower(),int(values[0]),int(values[1])])

    return offsetChanges, fastCommands

                                

def produceEportRX_input(inputFile, outputName='ECON_T_ePortRX.txt', configFile=None, N=-1, toHex=False, toBin=False, toInt=False):

    eportRXData = pd.read_csv(inputFile)

    if N==-1:
        N = len(eportRXData)
    elif N > len(eportRXData):
        print(f'More BX requested than in the input file, using only {len(eportRXData)} BX from input')
        N = len(eportRXData)

    eportRXData = eportRXData[:N]

    header = np.zeros(N,dtype=int) + 10
    header[(np.arange(N) % 3564)==0] = 9

    dataCols = [f'DATA_{i}' for i in range(12)]
    synchCols = [f'SYNCH_{i}' for i in range(12)]
    orbitCols = [f'ORBIT_{i}' for i in range(12)]

    eportRXData.columns = dataCols

    eportRXData = eportRXData.assign(**{c:2**31 for c in synchCols})
    eportRXData = eportRXData.assign(**{c:2**32-1 for c in orbitCols})

    eportRXData.loc[header==9,orbitCols] = 0

    for c in dataCols:
        eportRXData[c] = eportRXData[c] + (header<<28)

    eportRXData['godOrbitNumber'] = (np.arange(N)/3564).astype(int)
    eportRXData['godBucketNumber'] = np.arange(N)%3564

    eportRXData['CHANGE_OFFSET'] = -1
    eportRXData['OFFSET'] = 0

    cols = ['godOrbitNumber','godBucketNumber','CHANGE_OFFSET','OFFSET']
    for i in range(12):
        cols.append(dataCols[i])
        cols.append(synchCols[i])
        cols.append(orbitCols[i])
    eportRXData = eportRXData[cols]
    
    
    ### STARTING POINT OF CHANGING THE INPUTS
    ### SHOULD A "GOOD" VERSION BE DUMPED FOR AND OUTPUT VALUE

    #convert data columns to binary
    for c in dataCols:
        eportRXData[c] = eportRXData[c].apply(bin).str[2:]

    # assume the starting point of all offsets is 128 (is there something better?)
    offsets = [128]*12

    ## load a config file with the requested changes:
    offsetChanges = []
    fastCommands = []

    if not configFile is None:
        offsetChanges, fastCommands = parseConfig(configFile)

    offsetChanges.sort()
    
    for c in offsetChanges:
        _orbit = c[0]
        _bucket = c[1]
        _eport = c[2]
        _newVal = c[3]
        
        _globalBX = _orbit* 3564 + _bucket

        if _globalBX >= len(eportRXData):
            warnings.warn(f'Bucket to change ({_orbit},{_bucket}) is beyond the size of the test ({len(eportRXData)}), ignoring this change')
            continue
        if not eportRXData.loc[_globalBX,'CHANGE_OFFSET'] == -1:
            warnings.warn(f'Already changing on eport ({eportRXData.loc[_globalBX,"CHANGE_OFFSET"]}) in this bucket ({_orbit},{_bucket}), ignoring change to eport {_eport}')
            continue
        _column = f'DATA_{_eport}'
        
        startingData = ''.join(eportRXData.loc[_globalBX:,_column].tolist())

        relativeChange = _newVal - offsets[_eport]

        if relativeChange>0:
            newData = '0'*abs(relativeChange) +  startingData[:-1*relativeChange]
        elif relativeChange<0:
            newData = startingData[abs(relativeChange):] + '0'*abs(relativeChange)
        else:
            newData = startingData

        newData = [newData[i*32:(i+1)*32] for i in range(int(len(newData)/32))]

        eportRXData.loc[_globalBX:,_column] = newData
        eportRXData.loc[_globalBX,'CHANGE_OFFSET'] = _eport
        eportRXData.loc[_globalBX,'OFFSET'] = _newVal

        
    eportRXData.set_index(['godOrbitNumber','godBucketNumber'],inplace=True)



    if toInt:
        for c in dataCols:
            eportRXData[c] = eportRXData[c].apply(int,args=[2])
    elif toHex:
        for c in dataCols:
            eportRXData[c] = eportRXData[c].apply(convertToHex, args=[8,True])
        for c in synchCols:
            eportRXData[c] = eportRXData[c].apply(convertToHex)
        for c in orbitCols:
            eportRXData[c] = eportRXData[c].apply(convertToHex)
    elif toBin:
        for c in synchCols:
            eportRXData[c] = eportRXData[c].apply(convertToBin)
        for c in orbitCols:
            eportRXData[c] = eportRXData[c].apply(convertToBin)
    else:
        for c in synchCols:
            eportRXData[c] = eportRXData[c].apply(convertToHex)
        for c in orbitCols:
            eportRXData[c] = eportRXData[c].apply(convertToHex)
        
    eportRXData.to_csv(outputName)

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i',"--inputFile", default = 'Example_ePortRX_Data.csv',dest="inputFile", help="input file name of ePort RX data")
    parser.add_argument('-o',"--output", default = "ECON_T_ePortRX.txt",dest="outputName", help="file name for output")
    parser.add_argument('-c','--config', default = None, dest='configFile', help='configuration file from which to read the changes')
    parser.add_argument('-N', type=int, default = -1,dest="N", help="Number of BX to use, -1 is all in input")
    parser.add_argument('--hex',dest='toHex',default = False,action="store_true", help="save all values as hex")
    parser.add_argument('--bin',dest='toBin',default = False,action="store_true", help="save all values as bin")
    parser.add_argument('--int',dest='toInt',default = False,action="store_true", help="save all values as int")

    args = parser.parse_args()

    produceEportRX_input(**vars(args))

