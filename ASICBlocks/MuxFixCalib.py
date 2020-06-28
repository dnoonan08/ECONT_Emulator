import pandas as pd
import numpy as np

from Utils.encode import decode
decodeV = np.vectorize(decode)

import pickle

def getMuxRegisters(tpgNtupleMapping=False):
    tc_remap = pd.read_csv("Utils/LDM_TC_Mapping.csv")[['TC_Number','ECON_TC_Number_PostMux','ECON_TC_Number_PreMux']]
    
    muxRegisters = tc_remap[['ECON_TC_Number_PostMux','ECON_TC_Number_PreMux']].values
    if tpgNtupleMapping:
        muxRegisters = tc_remap[['TC_Number','ECON_TC_Number_PreMux']].values
    
    x = muxRegisters.tolist()
    x.sort()
    muxRegisters = np.array(x)
    return muxRegisters[:,1]

def Mux(df_Mux_in, Mux_registers):

    Mux_in_headers_ordered = [f'Mux_in_{i}' for i in Mux_registers]
    
    df_Mux_out = df_Mux_in[Mux_in_headers_ordered]
    
    df_Mux_out.columns = [f'Mux_out_{i}' for i in range(48)]
    return df_Mux_out



def FloatToFix(df_Mux_out, isHDM):
    df_F2F = pd.DataFrame(decodeV(df_Mux_out,3 if isHDM else 1),columns=[f'F2F_{i}' for i in range(48)],index=df_Mux_out.index)
    return df_F2F

def getCalibrationRegisters_Thresholds(subdet, layer, wafer, geomVersion, tpgNtupleMapping=False):
    
    if geomVersion in ['v10','v11']:
        with open('Utils/geomDF_v10.pkl','rb') as geomFile:
            geomDF = pickle.load(geomFile).loc[subdet,layer,wafer]
    else:
        with open('Utils/geomDF_v9.pkl','rb') as geomFile:
            geomDF = pickle.load(geomFile).loc[subdet,layer,wafer]

    calibVal, threshVal =  np.round((geomDF.corrFactor_finite*2**11).values).astype(int), geomDF.threshold_ADC.values

    if tpgNtupleMapping:
        return calibVal, threshVal

    tc_remap = pd.read_csv("Utils/LDM_TC_Mapping.csv")[['TC_Number','ECON_TC_Number_PostMux','ECON_TC_Number_PreMux']]
    muxRegisters = tc_remap[['TC_Number','ECON_TC_Number_PostMux']].values

    remappedCalibVal = np.zeros(48,dtype=int)
    remappedThreshVal = np.zeros(48,dtype=int)

    for x in muxRegisters:
        remappedCalibVal[x[1]] = calibVal[x[0]]
        remappedThreshVal[x[1]] = threshVal[x[0]]
    return remappedCalibVal, remappedThreshVal
    
def Calibrate(df_F2F, CALVALUE_Registers):
    
    df_CALQ = (df_F2F*CALVALUE_Registers*2**-11).astype(int)
    df_CALQ.columns = [f'CALQ_{i}' for i in range(48)]
    
    return df_CALQ
