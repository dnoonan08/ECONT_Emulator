import pandas as pd
import numpy as np
from Utils.encode import encode

MAX_EPORTTX=13

def splitToWords(row, N=16,totalWords=26):
    fullData = row['FullDataString']
    
    words = [int(fullData[i*N:(i+1)*N],2) for i in range(int(len(fullData)/N))]
        
    if len(words)<totalWords:
        words += [row['IdleWord']]*(totalWords-len(words))

    return words

Threshold_WordsPerNTCQ = {8  : 8 ,
                          9  : 8 ,
                          10 : 9 ,
                          11 : 9 ,
                          12 : 10,
                          13 : 10,
                          14 : 11,
                          15 : 11,
                          16 : 11,
                          17 : 12,
                          18 : 12,
                          19 : 13,
                          20 : 13,
                          21 : 14,
                          22 : 14,
                          23 : 15,
                          24 : 15,
                          25 : 15,
                          26 : 16,
                          27 : 16,
                          28 : 17,
                          29 : 17,
                          30 : 18,
                          31 : 18,
                          32 : 18,
                          33 : 19,
                          34 : 19,
                          35 : 20,
                          36 : 20,
                          37 : 21,
                          38 : 21,
                          39 : 21,
                          40 : 22,
                          41 : 22,
                          42 : 23,
                          43 : 23,
                          44 : 24,
                          45 : 24,
                          46 : 25,
                          47 : 25,
                          48 : 25,
                      }
                          
def formatThresholdOutput(row,TxSynchWord=0, Use_Sum=False, debug=False):

    SUM_FULL =row['SUM']
    SUM_NOT_TRANSMITTED =row['SUM_NOT_TRANSMITTED']
    CHARGEQ = row[[f'CHARGEQ_{i}' for i in range(48)]].values

    ADD_MAP  = row[[f'ADDRMAP_{i}' for i in range(48)]]
            
    NTCQ=sum(ADD_MAP)

    # CHARGEQ=CHARGEQ[:NTCQ]      ## remove zeros

    bx_cnt = row['BX_CNT']
    header =  format(bx_cnt, '#0%ib'%(7))[2:]
    
    dataType = ''
    if NTCQ==0: 
        dataType='000'
    elif NTCQ<8:
        dataType='010'
    else:
        dataType='100'

    if Use_Sum:
        modSumData = format(SUM_FULL, '#010b')[2:]
    else:
        modSumData = format(SUM_NOT_TRANSMITTED, '#010b')[2:]

    extraBit=''
    if NTCQ==0:
        nChannelData=''
        AddressMapData=''
        ChargeData=''
    elif NTCQ<8:
        nChannelData=format(NTCQ, '#0%ib'%(3+2))[2:]
        # print (ADD_MAP)        
        # bitmap = np.array([int(x) for x in format(ADD_MAP, '#0%ib'%(48+2))[2:]][::-1])
        channelNumbers = np.arange(48)[ADD_MAP==1]
        channelNumbersBin = [format(x,'#0%ib'%(6+2))[2:] for x in channelNumbers]
        AddressMapData = ''
        for x in channelNumbersBin: AddressMapData += x
        
        ChargeData = ''
        for x in CHARGEQ[:NTCQ]:
            ChargeData += format(x, '#0%ib'%(9))[2:]
    else:
        nChannelData=''
        AddressMapData=''.join([str(i) for i in ADD_MAP])
        ChargeData = ''
        for x in CHARGEQ:
            ChargeData += format(x, '#0%ib'%(9))[2:]

    formattedData = header + dataType + modSumData + extraBit + nChannelData + AddressMapData + ChargeData


    #Pads with beginning of next ChargeQ value, instead of 0's
    if NTCQ>=8:
        formattedData = formattedData[0:16*Threshold_WordsPerNTCQ[NTCQ]]

    if len(formattedData)%16==0:
        nPadBits=0
        paddedData = formattedData
    else:
        nPadBits = 16 - (len(formattedData)%16)
        paddedData = formattedData + '0'*nPadBits

    if not debug:
        return paddedData
    else:
        return [header, dataType , modSumData, extraBit ,nChannelData , len(AddressMapData) , len(ChargeData)]

def formatTruncatedOutput(row):

    header =  format(row['BX_CNT'], '#0%ib'%(7))[2:]

    dataType_Truncated = '110'

    SUM_FULL =row['SUM']
    modSumFull = format(SUM_FULL, '#0%ib'%(10))[2:]

    formattedData_Truncated = header + dataType_Truncated + modSumFull

    return int(formattedData_Truncated,2)


def Format_Threshold_Sum(df_Threshold_Sum, df_BX_CNT, TxSyncWord, Use_Sum):

    df_in = pd.merge(df_Threshold_Sum, df_BX_CNT, left_index=True, right_index=True)

    df_Format = pd.DataFrame(df_in.apply(formatThresholdOutput, Use_Sum=Use_Sum, axis=1).values,columns=['FullDataString'],index=df_in.index)

    df_Format['FRAMEQ_NUMW'] = (df_Format['FullDataString'] .str.len()/16).astype(int)

    df_Format['IdleWord'] = (df_BX_CNT.BX_CNT.values<<11) + TxSyncWord

    frameQ_headers = [f'FRAMEQ_{i}' for i in range(MAX_EPORTTX*2)]

    df_Format[frameQ_headers]= pd.DataFrame(df_Format.apply(splitToWords,axis=1).tolist(),columns=frameQ_headers,index=df_Format.index)

    df_Format['FRAMEQ_Truncated_0'] = df_in.apply(formatTruncatedOutput,axis=1)
    df_Format['FRAMEQ_Truncated_1'] = df_Format.IdleWord

    return df_Format[frameQ_headers+['FRAMEQ_NUMW','FRAMEQ_Truncated_0','FRAMEQ_Truncated_1','IdleWord']]


def formatBestChoiceOutput(row, nTC = 1, Use_Sum=False, debug=False):

    nExp = 4
    nMant = 3
    roundBits = False
    nDropBit = 0 

    ADD_MAP = list(row[[f'BC_TC_MAP_{i}' for i in range(48)]])
    CHARGEQ = list(row[[f'BC_CHARGE_{i}' for i in range(48)]])

    SUM = encode(sum(CHARGEQ[:]),0,5,3,asInt=True)
    SUM_NOT_TRANSMITTED = encode(sum(CHARGEQ[nTC:]),0,5,3,asInt=True)

    sel_q = CHARGEQ[:nTC]
    sel_add = ADD_MAP[:nTC]

    BITMAP = np.zeros(48, dtype=np.int32)
    CHARGEQ = np.zeros(48, dtype=np.int32)

    BITMAP[sel_add] = 1
    CHARGEQ[sel_add] = sel_q 

    CHARGEQ=CHARGEQ[CHARGEQ>0]      ## remove zeros

    bx_cnt = row['BX_CNT']
    header =  format(bx_cnt, '#0%ib'%(7))[2:]
    header = header[1:]

    if Use_Sum:
        modSumData = format(SUM, '#010b')[2:]
    else:
        modSumData = format(SUM_NOT_TRANSMITTED, '#010b')[2:]

    if nTC<8:
        nChannelData=format(nTC, '#0%ib'%(3+2))[2:]
        
#        bitmap = np.array([int(x) for x in format(ADD_MAP, '#0%ib'%(48+2))[2:]][::-1])
        channelNumbers = np.arange(48)[BITMAP==1]
        channelNumbersBin = [format(x,'#0%ib'%(6+2))[2:] for x in channelNumbers]

        AddressMapData = ''
        for x in channelNumbersBin: AddressMapData += x

        ChargeData = ''
        for x in CHARGEQ:
            ChargeData += encode(x,nDropBit,nExp,nMant,roundBits)
        
    else:
        nChannelData=''
        AddressMapData=''.join([str(i) for i in BITMAP])
        ChargeData = ''
        for x in CHARGEQ:
            ChargeData += encode(x,nDropBit,nExp,nMant,roundBits)

    formattedData = header + modSumData + AddressMapData + ChargeData

    if len(formattedData)%16==0:
        nPadBits=0
        paddedData = formattedData
    else:
        nPadBits = 16 - (len(formattedData)%16)
        paddedData = formattedData + '0'*nPadBits

        
    if not debug:
        return paddedData
    else:
        return [header, modSumData , AddressMapData , ChargeData]

from Utils.linkAllocation import tcPerLink

def Format_BestChoice(df_BestChoice, EPORTTX_NUMEN, df_BX_CNT, TxSyncWord, Use_Sum):
    df_in = pd.merge(df_BestChoice, df_BX_CNT, left_index=True, right_index=True)

    df_Format = pd.DataFrame(df_in.apply(formatBestChoiceOutput, nTC=tcPerLink[EPORTTX_NUMEN], Use_Sum=Use_Sum, axis=1).values,columns=['FullDataString'],index=df_in.index)

    df_Format['FRAMEQ_NUMW'] = (df_Format['FullDataString'] .str.len()/16).astype(int)

    df_Format['IdleWord'] = (df_BX_CNT.BX_CNT.values<<11) + TxSyncWord

    frameQ_headers = [f'FRAMEQ_{i}' for i in range(MAX_EPORTTX*2)]

    df_Format[frameQ_headers]= pd.DataFrame(df_Format.apply(splitToWords,axis=1).tolist(),columns=frameQ_headers,index=df_Format.index)

    df_Format['FRAMEQ_Truncated_0'] = 0
    df_Format['FRAMEQ_Truncated_1'] = 0

    return df_Format[frameQ_headers+['FRAMEQ_NUMW','FRAMEQ_Truncated_0','FRAMEQ_Truncated_1','IdleWord']]




def formatSTC_4_9(row, nSTC, debug=False):
    colsSUM=[f'XTC4_9_SUM_{i}' for i in range(12)]
    colsIDX=[f'MAX4_ADDR_{i}' for i in range(12)]

    SumData = row[colsSUM].values
    IdxData = row[colsIDX].values

    nBitsData = 9
    nBitsAddr = 2 

    #only a 4 bit header for STC
    bx_cnt = row['BX_CNT']
    header =  format(bx_cnt, '#0%ib'%(7))[2:]
    header = header[0] + header[2:]
    
    STC_Data = ""
    for i in range(nSTC):
        idxBits = format(IdxData[i], '#0%ib'%(nBitsAddr+2))[2:]
        STC_Data += idxBits

    for i in range(nSTC):
        dataBits = format(SumData[i], '#0%ib'%(nBitsData+2))[2:]
        STC_Data += dataBits
        
    formattedData = header + STC_Data

    if len(formattedData)%32==0:
        nPadBits=0
        paddedData = formattedData
    else:
        nPadBits = 32 - (len(formattedData)%32)
        paddedData = formattedData + '0'*nPadBits

    return paddedData


def formatSTC_16_9(row, nSTC, debug=False):
    
    colsSUM=[f'XTC16_9_SUM_{i}' for i in range(3)]
    colsIDX=[f'MAX16_ADDR_{i}' for i in range(3)]

    SumData = row[colsSUM].values
    IdxData = row[colsIDX].values

    nBitsAddr = 4 
    nBitsData = 9

    #only a 4 bit header for STC
    bx_cnt = row['BX_CNT']
    header =  format(bx_cnt, '#0%ib'%(7))[2:]
    header = header[0] + header[2:]
    
    STC_Data = ""
    for i in range(nSTC):
        idxBits = format(IdxData[i], '#0%ib'%(nBitsAddr+2))[2:]
        STC_Data += idxBits

    for i in range(nSTC):
        dataBits = format(SumData[i], '#0%ib'%(nBitsData+2))[2:]
        STC_Data += dataBits
        
    formattedData = header + STC_Data

    if len(formattedData)%32==0:
        nPadBits=0
        paddedData = formattedData
    else:
        nPadBits = 32 - (len(formattedData)%32)
        paddedData = formattedData + '0'*nPadBits

    return paddedData

def formatSTC_4_7(row, nSTC, debug=False):
    
    colsSUM=[f'XTC4_7_SUM_{i}' for i in range(12)]
    colsIDX=[f'MAX4_ADDR_{i}' for i in range(12)]

    SumData = row[colsSUM].values
    IdxData = row[colsIDX].values

    nBitsAddr = 2
    nBitsData = 7

    #only a 4 bit header for STC
    bx_cnt = row['BX_CNT']
    header =  format(bx_cnt, '#0%ib'%(7))[2:]
    header = header[0] + header[2:]
    
    STC_Data = ""
    for i in range(nSTC):
        idxBits = format(IdxData[i], '#0%ib'%(nBitsAddr+2))[2:]
        STC_Data += idxBits

    for i in range(nSTC):
        dataBits = format(SumData[i], '#0%ib'%(nBitsData+2))[2:]
        STC_Data += dataBits
        
    formattedData = header + STC_Data

    if len(formattedData)%32==0:
        nPadBits=0
        paddedData = formattedData
    else:
        nPadBits = 32 - (len(formattedData)%32)
        paddedData = formattedData + '0'*nPadBits

    return paddedData


def formatCTC_4_7(row, nSTC, debug=False):
    
    colsSUM=[f'XTC4_7_SUM_{i}' for i in range(12)]

    SumData = row[colsSUM].values

    nBitsAddr = 0
    nBitsData = 7 

    #only a 4 bit header for STC
    bx_cnt = row['BX_CNT']
    header =  format(bx_cnt, '#0%ib'%(7))[2:]
    header = header[0] + header[2:]
    
    STC_Data = ""
    for i in range(nSTC):
        dataBits = format(SumData[i], '#0%ib'%(nBitsData+2))[2:]
        STC_Data += dataBits
        
    formattedData = header + STC_Data

    if len(formattedData)%32==0:
        nPadBits=0
        paddedData = formattedData
    else:
        nPadBits = 32 - (len(formattedData)%32)
        paddedData = formattedData + '0'*nPadBits

    return paddedData



def Format_SuperTriggerCell(df_SuperTriggerCell, STC_TYPE, EPORTTX_NUMEN, df_BX_CNT, TxSyncWord):
    df_in = pd.merge(df_SuperTriggerCell, df_BX_CNT, left_index=True, right_index=True)

    if STC_TYPE==0: #STC4_9
        nSTC = 12 if EPORTTX_NUMEN>=5 else 11 if EPORTTX_NUMEN==4 else 8 if EPORTTX_NUMEN==3 else 5 if EPORTTX_NUMEN==2 else 2 
        df_Format = pd.DataFrame(df_in.apply(formatSTC_4_9, nSTC=nSTC, axis=1).values,columns=['FullDataString'],index=df_in.index)
        if EPORTTX_NUMEN>5:
            df_Format['FullDataString'] = ''
    elif STC_TYPE==1: #STC16_9
        nSTC = 3 if EPORTTX_NUMEN>=2 else 2
        df_Format = pd.DataFrame(df_in.apply(formatSTC_16_9, nSTC=nSTC, axis=1).values,columns=['FullDataString'],index=df_in.index)
        if EPORTTX_NUMEN>2:
            df_Format['FullDataString'] = ''
    elif STC_TYPE==2: #CTC4_7
        nSTC = 12 if EPORTTX_NUMEN>=3 else 8 if EPORTTX_NUMEN==2 else 4
        df_Format = pd.DataFrame(df_in.apply(formatCTC_4_7, nSTC=nSTC, axis=1).values,columns=['FullDataString'],index=df_in.index)
        if EPORTTX_NUMEN>3:
            df_Format['FullDataString'] = ''
    elif STC_TYPE==3: #STC4_7
        nSTC = 12 if EPORTTX_NUMEN>=4 else 10 if EPORTTX_NUMEN==3 else 6 if EPORTTX_NUMEN==2 else 3
        df_Format = pd.DataFrame(df_in.apply(formatSTC_4_7, nSTC=nSTC, axis=1).values,columns=['FullDataString'],index=df_in.index)
        if EPORTTX_NUMEN>4:
            df_Format['FullDataString'] = ''
        
    df_Format['FRAMEQ_NUMW'] = (df_Format['FullDataString'] .str.len()/16).astype(int)

    df_Format.loc[df_Format.FRAMEQ_NUMW==0,'FRAMEQ_NUMW']=2
        
    df_Format['IdleWord'] = 0 #(df_BX_CNT.BX_CNT.values<<11) + TxSyncWord

    frameQ_headers = [f'FRAMEQ_{i}' for i in range(MAX_EPORTTX*2)]

    df_Format[frameQ_headers]= pd.DataFrame(df_Format.apply(splitToWords,axis=1).tolist(),columns=frameQ_headers,index=df_Format.index)

    df_Format['FRAMEQ_Truncated_0'] = 0
    df_Format['FRAMEQ_Truncated_1'] = 0

    return df_Format[frameQ_headers+['FRAMEQ_NUMW','FRAMEQ_Truncated_0','FRAMEQ_Truncated_1','IdleWord']]


def formatRepeaterOutput(row,debug=False):
    cols = [f'RPT_{i}' for i in range(48)]
    CHARGEQ = row[cols].values
    ChargeData = ''
    for x in CHARGEQ:
        ChargeData += format(x, '#0%ib'%(9))[2:]

    bx_cnt = row['BX_CNT']
    header =  format(bx_cnt, '#0%ib'%(7))[2:]

    formattedData = header + ChargeData

    if len(formattedData)%16==0:
        nPadBits=0
        paddedData = formattedData
    else:
        nPadBits = 16 - (len(formattedData)%16)
        paddedData = formattedData + '0'*nPadBits

    return paddedData

def Format_Repeater(df_Repeater, EPORTTX_NUMEN, df_BX_CNT, TxSyncWord):
    df_in = pd.merge(df_Repeater, df_BX_CNT, left_index=True, right_index=True)

    df_Format = pd.DataFrame(df_in.apply(formatRepeaterOutput, axis=1).values,columns=['FullDataString'],index=df_in.index)

    df_Format['FRAMEQ_NUMW'] = min(25, 2*EPORTTX_NUMEN)

    df_Format['IdleWord'] = 0 #(df_BX_CNT.BX_CNT.values<<11) + TxSyncWord

    frameQ_headers = [f'FRAMEQ_{i}' for i in range(MAX_EPORTTX*2)]

    df_Format[frameQ_headers]= pd.DataFrame(df_Format.apply(splitToWords,axis=1).tolist(),columns=frameQ_headers,index=df_Format.index)

    df_Format['FRAMEQ_Truncated_0'] = 0
    df_Format['FRAMEQ_Truncated_1'] = 0

    return df_Format[frameQ_headers+['FRAMEQ_NUMW','FRAMEQ_Truncated_0','FRAMEQ_Truncated_1','IdleWord']]



def binFormat(x,N):
    return format(x,f'#0{N+2}b')[2:]

binFormat=np.vectorize(binFormat)

def format_AutoencoderOutput(row, Eporttx_Numen):
    ae_Bits = np.array(list(''.join(row[[f'AE_BYTE{i}' for i in range(19,-1,-1)]].apply(binFormat,N=8))))[7:]
    ae_Mask = np.array(list(''.join(row[[f'MAE_BYTE{i}' for i in range(17,-1,-1)]].apply(binFormat,N=8))))=='1'

    modSum = ''.join(ae_Bits[-9:])
    ae_DataBits = ae_Bits[:-9]

    nBits = 16 + 32*(Eporttx_Numen-1)

    AE_Data = ''.join(ae_DataBits[ae_Mask])[-1*nBits:]

    if len(AE_Data) < nBits:
        AE_Data = '0'*(nBits-len(AE_Data)) + AE_Data

    bx_cnt = row['BX_CNT']
    header =  format(bx_cnt, '#0%ib'%(7))[2:]

    formattedData = header + modSum +'00' + AE_Data

    return formattedData

def Format_Autoencoder(df_Encoder, df_BX_CNT, Eporttx_Numen, TxSyncWord):
    df_in = pd.merge(df_Encoder, df_BX_CNT, left_index=True, right_index=True)

    df_Format = pd.DataFrame(df_in.apply(format_AutoencoderOutput, Eporttx_Numen=Eporttx_Numen, axis=1).values,columns=['FullDataString'],index=df_in.index)

    df_Format['FRAMEQ_NUMW'] = (df_Format['FullDataString'] .str.len()/16).astype(int)

    df_Format['IdleWord'] = 0 #(df_BX_CNT.BX_CNT.values<<11) + TxSyncWord

    frameQ_headers = [f'FRAMEQ_{i}' for i in range(MAX_EPORTTX*2)]

    df_Format[frameQ_headers]= pd.DataFrame(df_Format.apply(splitToWords,axis=1).tolist(),columns=frameQ_headers,index=df_Format.index)

    df_Format['FRAMEQ_Truncated_0'] = 0
    df_Format['FRAMEQ_Truncated_1'] = 0

    return df_Format[frameQ_headers+['FRAMEQ_NUMW','FRAMEQ_Truncated_0','FRAMEQ_Truncated_1','IdleWord']]
