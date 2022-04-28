# -*- coding: utf-8 -*-
"""
Created on Tue Dec  7 12:41:12 2021

@author: bmeihack(bwmm)

"""


"""
12/07/21
    Initial program creation 
    

01/17/22
    Added if statement in StartWaferTest that checks the reported SiteResistance 
    value against a constant iUpperLimit and iLowerLimit value of 5000 and if it 
    goes above or below one of these values the SiteResistance will be set to the 
    constant value. 
    
    At some point this could be expanded to be checked against a lookup table
    for control limits. 


03/24/22
    Added VISweep() function that uses the more efficient buffer allocation 
    Cleaned up code interface and documentation for each module
    
03/25/22
    Modified StartWaferTest() to include options to enable surface profiling 
    for wafers with high warpage. 
    Also added variable for iUpperLimit and iLowLimit to control the reported 
    measurement range. This will need to by dynamically adjusted for some 
    products 
    
    modified structure of program to create a directory under c:\lot\ that is
    originated from the input lot name/number and automatically puts the files
    into that folder. 
    
04/07/22
    Added directory control logic for the storage of the data into s structured
    folder instead of into the root \lot folder
    


"""

#Modules ---------------------------------------------------------------------

import hightime
import nidcpower
import sys 
import os
import velox
import numpy as np
from matplotlib import pyplot as plt
import time
import math
import pandas as pd
import seaborn as sns


#Modules ---------------------------------------------------------------------


#register the velox command set. 
#requires that the velox library is modified 
# \anaconda3\Lib\site-packages\velox\vxmessageserver.py 
# modify the registrationMessage = REGISTRATION_MESSAGE_TEMPLATE.format() to just be registrationMessage = REGISTRATION_MESSAGE_TEMPLATE
msg = velox.MessageServerInterface()

#-----------------------------------------------------------------------------
# Program Constants 
# TODO: Cleanup this section for unused portions. The only thing that is used 
#       as of 03/22 is iUpperLimit, iLowerLimit and vdpConstant. 
#-----------------------------------------------------------------------------


#This defines the resource name for the SMU. Since we don't have multiple 
#SMU it get gets hardcoded
resource_name='4139'


#van der pauw constant = pi/ln(2)
vdpconstant = 4.53236 

#0.001 second delay between measurements
delay = 0.01  

currentStart = 0.00001 #10 microAmp 

measurementList = []
currentlist = []

#upper Resistance Limit
iUpperLimit = 1000

#lower Resistance Limit
iLowerLimit = -1000

path = r'C:\lot'

lotID = "4133957-01R12A-IWDC287"


#-----------------------------------------------------------------------------
# END Program Constants 
#-----------------------------------------------------------------------------



#constants---------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Test a measurement on a static point
#-----------------------------------------------------------------------------

#simple program to test the system. 
def TestIVSweep():
    
    start = time.time()
    measure = IVSweep(100,0.00001,0.001,0.01,iLowerLimit=1500,iUpperLimit=1500)
    stop = time.time()
    
    res = CalcResistance(measure.current,measure.voltage)
    plt.plot(measure.current,measure.voltage)
    plt.show()
    
    print("--------------------------------------------------------------")
    print("total time", stop-start)
    print("site resistance is: ", res)
    print("--------------------------------------------------------------")

def TestVISweep():
    
    start = time.time()
    measure = VISweep(100, 0.0, 0.14, 0.01)
    stop = time.time()
    
    res = CalcResistance(measure.current,measure.voltage)
    plt.plot(measure.current,measure.voltage)
    plt.show()
    
    print("--------------------------------------------------------------")
    print("total time", stop-start)
    print("site resistance is: ", res)
    print("--------------------------------------------------------------")
    
#-----------------------------------------------------------------------------
# ENDTest a measurement on a static point
#-----------------------------------------------------------------------------


 
#-----------------------------------------------------------------------------
# NI Source Measurement Code 
#-----------------------------------------------------------------------------


def IVSweep(samples,currentStart,currentEnd, delay):
    
    """
    Sets up a measurement sweep by forcing a current and measuring the voltage
    
    This method sets up a buffer of measurements and the SMU blocks the controller
    to perform the requested measurement samples. 
    
    the return is an array of measurements [float voltage, float current,bool compliance]
    
    Args:
        samples:int = 100
        currentStart = 0.000001 (1microamp)
        currentEnd = 0.0001 (100 microamp)
        delay = 0.01 (time in seconds)
    Example: IVSweep(100, 0.000001, 0.0001, 0.01)
    """
    
    resource_name='4139'
    print("################ Starting Sweep #############################")
    currentList = np.linspace(currentStart,currentEnd,samples)
    
    #setting timeout to an arbitrarily large number to avoid data error
    timeout=100

    startTime = time.time()
    with nidcpower.Session(resource_name) as session:

        # Configure the session.
        session.source_mode = nidcpower.SourceMode.SEQUENCE
        
        session.voltage_level_autorange = False
        session.current_limit_autorange = False
        session.current_level_range = currentEnd*2
        session.source_delay = hightime.timedelta(seconds=delay)
        session.sense = nidcpower.Sense.REMOTE
        session.aperture_time_units = nidcpower.ApertureTimeUnits.POWER_LINE_CYCLES
        session.aperture_time = 2 
        session.voltage_limit_range = 0.6
        session.voltage_limit = 0.6
        
        properties_used = ['output_function', 'current_level']
        session.create_advanced_sequence(sequence_name='my_sequence', property_names=properties_used, set_as_active_sequence=True)

        # voltage_per_step = voltage_max / points_per_output_function
        # for i in range(points_per_output_function):
        #     session.create_advanced_sequence_step(set_as_active_step=False)
        #     session.output_function = nidcpower.OutputFunction.DC_VOLTAGE
        #     session.voltage_level = voltage_per_step * i

        
        for i in range(samples):
            session.create_advanced_sequence_step(set_as_active_step=True)
            session.output_function = nidcpower.OutputFunction.DC_CURRENT
            session.current_level = currentList[i]

        # with session.initiate():
        #     session.wait_for_event(nidcpower.Event.SEQUENCE_ENGINE_DONE)
        #     channel_indices = '0-{0}'.format(session.channel_count - 1)
        #     channels = session.get_channel_names(channel_indices)
        #     measurement_group = [session.channels[name].fetch_multiple(points_per_output_function * 2, timeout=timeout) for name in channels]

        with session.initiate():
            
            session.wait_for_event(nidcpower.Event.MEASURE_COMPLETE)
            channel_indices = '0-{0}'.format(session.channel_count - 1)
            channels = session.get_channel_names(channel_indices)
            
            dataFrame = session.channels['4139/0'].fetch_multiple(count=samples,timeout=timeout)
            dataFrame = pd.DataFrame(dataFrame)
            
            
        session.delete_advanced_sequence(sequence_name='my_sequence')
        stopTime = time.time()
        print("Total Measurement Time", stopTime-startTime)
        
       
        return dataFrame     

def VISweep(samples,voltageStart,voltageEnd, delay):
    #
    """
    Sets up a measurement sweep by forcing a voltage and measuring the current
    
    This method sets up a buffer of measurements and the SMU blocks the controller
    to perform the requested measurement samples. 
    
    the return is an array of measurements [float voltage, float current,bool compliance]
    
    Args:
        samples:int = 100
        voltageStart = 0.0 (0microamp)
        currentEnd = .00001 (10 microvolt)
        delay = 0.01 (time in seconds)
    Example: VISweep(100,0,.14,0.01)
    """
    
    resource_name='4139'
    print("################ Starting Sweep #############################")
    
    #create an evenly spaced list of numbers for the input array of the measurement pounts
    voltageList = np.linspace(voltageStart,voltageEnd,samples)
    
    #setting timeout to an arbitrarily large number to avoid data error
    timeout=100

    startTime = time.time()
    with nidcpower.Session(resource_name) as session:

        # Configure the session.
        session.source_mode = nidcpower.SourceMode.SEQUENCE
        
        session.voltage_level_autorange = True
        session.current_limit_autorange = False
        session.voltage_level_range = voltageEnd*2
        session.source_delay = hightime.timedelta(seconds=delay)
        session.sense = nidcpower.Sense.REMOTE
        session.aperture_time_units = nidcpower.ApertureTimeUnits.POWER_LINE_CYCLES
        session.aperture_time = 2 
        session.current_limit_range = 0.1
        session.current_limit = 0.1
        
        properties_used = ['output_function', 'voltage_level']
        session.create_advanced_sequence(sequence_name='my_sequence', property_names=properties_used, set_as_active_sequence=True)

        # voltage_per_step = voltage_max / points_per_output_function
        # for i in range(points_per_output_function):
        #     session.create_advanced_sequence_step(set_as_active_step=False)
        #     session.output_function = nidcpower.OutputFunction.DC_VOLTAGE
        #     session.voltage_level = voltage_per_step * i

        
        for i in range(samples):
            session.create_advanced_sequence_step(set_as_active_step=True)
            session.output_function = nidcpower.OutputFunction.DC_VOLTAGE
            session.voltage_level = voltageList[i]

        # with session.initiate():
        #     session.wait_for_event(nidcpower.Event.SEQUENCE_ENGINE_DONE)
        #     channel_indices = '0-{0}'.format(session.channel_count - 1)
        #     channels = session.get_channel_names(channel_indices)
        #     measurement_group = [session.channels[name].fetch_multiple(points_per_output_function * 2, timeout=timeout) for name in channels]

        with session.initiate():
            
            session.wait_for_event(nidcpower.Event.MEASURE_COMPLETE)
            channel_indices = '0-{0}'.format(session.channel_count - 1)
            channels = session.get_channel_names(channel_indices)
            
            dataFrame = session.channels['4139/0'].fetch_multiple(count=samples,timeout=timeout)
            dataFrame = pd.DataFrame(dataFrame)
            
            
        session.delete_advanced_sequence(sequence_name='my_sequence')
        stopTime = time.time()
        print("Total Measurement Time", stopTime-startTime)
        
       
        return dataFrame     


#Sweep current and measure voltage using on/off method of control. 
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            
def IVSweep_v1(samples, currentStart,currentEnd, delay):
    
    """
    Sets up a measurement sweep by forcing a current and measuring the voltage.
    This methodology is slower because it uses an interative loop to call the
    measurement compared to the IVSweep base function which instantiates a buffer
    of (n) measurements. This method is about 2X slower for the same settings 
    and may introduce additional noise in the measurement from the power line 
    or other RF sources depending on the measurement cycle. 
    
    the return is an array of measurements [float voltage, float current,bool compliance]
    
    Args:
        samples:int = 100
        currentStart = 0.000001 (1microamp)
        currentEnd = 0.0001 (100 microamp)
        delay = 0.01 (time in seconds)
    Example: IVSweep_v1(100, 0, 0.001, 0.01)

    """
    
    currentlist = np.linspace(currentStart,currentEnd,samples)
    current = []
    voltage = []
    compliance = []
    
    for i in range(samples):
        with nidcpower.Session(resource_name='4139') as session:
            
            

        # Configure the session.
            session.source_mode = nidcpower.SourceMode.SINGLE_POINT
            session.output_function = nidcpower.OutputFunction.DC_CURRENT
            
            session.current_level_range = currentlist[samples-1]*2
            
            session.voltage_limit_range = 0.6
            session.voltage_limit = 0.6
            session.source_delay = hightime.timedelta(seconds=delay)
            session.measure_when = nidcpower.MeasureWhen.AUTOMATICALLY_AFTER_SOURCE_COMPLETE
            session.current_level = currentlist[i]
            session.sense = nidcpower.Sense.REMOTE
            session.aperture_time_units = nidcpower.ApertureTimeUnits.POWER_LINE_CYCLES
            session.aperture_time = 2  
            
            
            
        
        
            with session.initiate():
                channel_indices = '0-{0}'.format(session.channel_count - 1)
                channels = session.get_channel_names(channel_indices)
                for channel_name in channels:
                    #print('Channel: {0}'.format(channel_name))
                    #print('---------------------------------')
                    #print('Measurement :', i)
                    
                    tempArray = session.channels[channel_name].fetch_multiple(count=1)
                    voltage.append(tempArray[0].voltage)
                    current.append(tempArray[0].current)
                    compliance.append(tempArray[0].in_compliance)
    dataFrame = pd.DataFrame(data=[current,voltage,compliance]).T
    new_dtypes = {"current": np.float64, "voltage": np.float64,"compliance": bool}
    
    dataFrame.columns = ['current','voltage','compliance']   
    dataFrame = dataFrame.astype(new_dtypes)    
         
    return dataFrame


#Sweeps current using Local sense versus remote sense. Local sense uses 
#sensing on the same line such as for measurements which only have 2 contacts
#Notice that this uses the v1 sweep which loops through a single source event

#no use case for this currently 


def IVSweep_v1_Local(samples, currentStart,currentEnd, delay):
    
    """
    Sets up a measurement sweep by forcing a current and measuring the voltage.
    This methodology is slower because it uses an interative loop to call the
    measurement compared to the IVSweep base function which instantiates a buffer
    of (n) measurements. This method is about 2X slower for the same settings 
    and may introduce additional noise in the measurement from the power line 
    or other RF sources depending on the measurement cycle. 
    
    the return is an array of measurements [float voltage, float current,bool compliance]
    
    Args:
        samples:int = 100
        currentStart = 0.000001 (1microamp)
        currentEnd = 0.0001 (100 microamp)
        delay = 0.01 (time in seconds)
    Example: IVSweep_v1(100, 0, 0.001, 0.01)

    """
    
    currentlist = np.linspace(currentStart,currentEnd,samples)
    current = []
    voltage = []
    compliance = []
    
    for i in range(samples):
        with nidcpower.Session(resource_name='4139') as session:
            
            

        # Configure the session.
            session.source_mode = nidcpower.SourceMode.SINGLE_POINT
            session.output_function = nidcpower.OutputFunction.DC_CURRENT
            session.voltage_limit = .06
            session.current_level_range = currentlist[samples-1]*2
            
            session.voltage_limit_range = 0.6
            session.voltage_limit = 0.6
            session.source_delay = hightime.timedelta(seconds=delay)
            session.measure_when = nidcpower.MeasureWhen.AUTOMATICALLY_AFTER_SOURCE_COMPLETE
            session.current_level = currentlist[i]
            session.sense = nidcpower.Sense.LOCAL
            session.aperture_time_units = nidcpower.ApertureTimeUnits.POWER_LINE_CYCLES
            session.aperture_time = 2    
            
            
        
        
            with session.initiate():
                channel_indices = '0-{0}'.format(session.channel_count - 1)
                channels = session.get_channel_names(channel_indices)
                for channel_name in channels:
                    #print('Channel: {0}'.format(channel_name))
                    #print('---------------------------------')
                    #print('Measurement :', i)
                    
                    tempArray = session.channels[channel_name].fetch_multiple(count=1)
                    voltage.append(tempArray[0].voltage)
                    current.append(tempArray[0].current)
                    compliance.append(tempArray[0].in_compliance)
    dataFrame = pd.DataFrame(data=[current,voltage,compliance]).T
    new_dtypes = {"current": np.float64, "voltage": np.float64,"compliance": bool}
    
    dataFrame.columns = ['current','voltage','compliance']   
    dataFrame = dataFrame.astype(new_dtypes)             
    return dataFrame

#Sweep voltage and measure current using the V1 method
def VISweep_v1(samples, voltageStart, voltageEnd, delay):
       
    """
    Sets up a measurement sweep by voltage and and measuring current.
    This methodology is slower because it uses an interative loop to call the
    measurement compared to the IVSweep base function which instantiates a buffer
    of (n) measurements. This method is about 2X slower for the same settings 
    and may introduce additional noise in the measurement from the power line 
    or other RF sources depending on the measurement cycle. 
    
    the return is an array of measurements [float voltage, float current,bool compliance]
    
    Args:
        samples:int = 100
        voltageStart = 0.000001 (1microamp)
        voltageEnd = 0.0001 (100 microamp)
        delay = 0.01 (time in seconds)
    Example: VISweep_v1(100, 0.001, 0.2, 0.01)

    """
    
    voltagelist = np.linspace(voltageStart,voltageEnd,samples)
    current = []
    voltage = []
    compliance = []
    
    for i in range(samples):
        with nidcpower.Session(resource_name='4139') as session:
            
            

        # Configure the session.
            session.source_mode = nidcpower.SourceMode.SINGLE_POINT
            session.output_function = nidcpower.OutputFunction.DC_VOLTAGE
            session.current_limit = .0001
            session.voltage_level_range = voltagelist[samples-1]*2
            
            session.current_limit_range = 0.1
            session.current_limit = 0.1
            session.source_delay = hightime.timedelta(seconds=delay)
            session.measure_when = nidcpower.MeasureWhen.AUTOMATICALLY_AFTER_SOURCE_COMPLETE
            session.voltage_level = voltagelist[i]
            session.sense = nidcpower.Sense.REMOTE
            
            session.aperture_time_units = nidcpower.ApertureTimeUnits.POWER_LINE_CYCLES
            session.aperture_time = 2    
            
        
        
            with session.initiate():
                channel_indices = '0-{0}'.format(session.channel_count - 1)
                channels = session.get_channel_names(channel_indices)
                for channel_name in channels:
                    #print('Channel: {0}'.format(channel_name))
                    #print('---------------------------------')
                    #print('Measurement :', i)
                    
                    tempArray = session.channels[channel_name].fetch_multiple(count=1)
                    voltage.append(tempArray[0].voltage)
                    current.append(tempArray[0].current)
                    compliance.append(tempArray[0].in_compliance)
    dataFrame = pd.DataFrame(data=[current,voltage,compliance]).T
    new_dtypes = {"current": np.float64, "voltage": np.float64,"compliance": bool}
    
    dataFrame.columns = ['current','voltage','compliance']   
    dataFrame = dataFrame.astype(new_dtypes)             
    return dataFrame

#-----------------------------------------------------------------------------
# END NI Source Measurement Code 
#-----------------------------------------------------------------------------




#-----------------------------------------------------------------------------
# Calculations 
#-----------------------------------------------------------------------------

def CalcResistance(current,voltage):
    A = np.vstack([current,np.ones(len(current))]).T
    m,c = np.linalg.lstsq(A,voltage,rcond=None)[0]
                                                  
    #m is the slope of the regression of the IV sweep
    return m

def CalcSheetResistance(resistance):  #symmetric van der pauw structure
    sheetR = vdpconstant*resistance
    
    return sheetR
    
    
def IVSweepRepeatability(samples):
    """
    Measures the repeatability of a Current sweep and outputs the
    measured resistance and 1 sigma repeatability
    
    Args:
        samples:int = 30
    Example:IVSweepRepeatability(30)
    """
    
    integrator = []
    for i in range(samples):
        measure = IVSweep(100,0.00001,0.0001,0.01)       
        res = CalcResistance(measure.current,measure.voltage)
        integrator.append(res)
        print("Standard Deviation: ", np.std(integrator))

        print("Measurement: ", res)

def VISweepRepeatability(samples):
    """
    Measures the repeatability of a Voltage sweep and outputs the
    measured resistance and 1 sigma repeatability
    
    Args:
        samples:int = 30
    Example:VISweepRepeatability(30)
    """
    integrator = []
    for i in range(samples):
        measure = VISweep(100, 0.00001, 0.0001, 0.01)
        res = CalcResistance(measure.current,measure.voltage)
        integrator.append(res)
        print("Standard Deviation: ", np.std(integrator))

        print("Measurement: ", res)

#-----------------------------------------------------------------------------
# END Calculations 
#-----------------------------------------------------------------------------


#-----------------------------------------------------------------------------
# VELOX Code 
#-----------------------------------------------------------------------------

def UnitTest(lotID,samples,start,end,delayTime,):
   
    
    """
    Unit test to validate function calls to Velox without touching down  
    
    Args:
        lotID:string = 1234567-22RN6
        samples:int = 100 
        start:float = 0.00001 (10microAmps)
        end:float = 0.0001 (100microAmps)
        delayTime:float = 0.01 (10mSec)
    
    Example:StartWaferTest(lotID,100,0.00001,0.0001,0.01)
    """
    
    #prior to starting the measurement, map the surface contour for better contact
    
    #velox.DoWaferProfiling()
    
    measurementVariables = ['DieX', 
                            'DieY',
                            'SiteNumber',
                            'Site', 
                            'Resistance']
    measurementData = pd.DataFrame(columns=measurementVariables)
    dataFrameTypes = {'DieX':int,
                      'DieY':int,
                      'SiteNumber':int,
                      'Site':str,
                      'Resistance':float,
                      }
    measurementData.astype(dataFrameTypes)

    
    

    #gets the number of die to measure in the wafer map
    iDieSamplePlan = int(velox.GetNumSelectedDies())


    #read the Map Position that is currently active. This requires the system  
    #to have passed pattern recognition at the site if Automation function is trained
    sReadMapPosition = velox.ReadMapPosition2()
    site = tuple([sReadMapPosition.CurDie,sReadMapPosition.CurSite])
    iSubDieCount = velox.GetDieInfo()
    endsite = tuple([iDieSamplePlan-1,iSubDieCount-1])
    
      
    if site != (1,0):
        #if the system is not currently at the first die in the map, move there
        try:
            sStepFirstDie = velox.StepFirstDie()
        except:
            print("failed to pattern req")
            sStepFirstDie = velox.StepFirstDie()
            sReadMapPosition = velox.ReadMapPosition2()
            
        
        #test plan will kick off.     
        for i in range(iDieSamplePlan):
            print("Testing Die ", str(velox.ReadMapPosition2().DieX)+","+str(velox.ReadMapPosition2().DieY))
            for j in range(iSubDieCount):
                   
                sReadMapPosition = velox.ReadMapPosition2()
                iDieX = sReadMapPosition.DieX
                iDieY = sReadMapPosition.DieY
                iSubDie = sReadMapPosition.CurSite
                sSubDieLabel = velox.GetSubDieLabelAsNum()
                print("Testing site ", sSubDieLabel)
                
                #put the chuck into contact with the probe pins
                #velox.MoveChuckContact()
                #stablize for 100mSec
                #time.sleep(0.1)
                
                #SweepTable = IVSweep(samples, start, end, delayTime)
                time.sleep(0.1)
                #ivDF = pd.DataFrame(SweepTable)
                #ivDF.to_csv(r'C:/Lot/'+lotID+str(" ")+str(iDieX)+"_"+str(iDieY)+sSubDieLabel,sep=",")
                
                #SiteResistance = CalcResistance(SweepTable.current,SweepTable.voltage)
                """
                Check if SiteResistance is above or below this arbitrary value 
                and cap it to avoid the charts getting massive limit ranges
    
                """
                #if SiteResistance > iUpperLimit:
                    #SiteResistance = iUpperLimit
                #elif SiteResistance < iLowerLimit:
                    #SiteResistance = iLowerLimit
                    
                #plt.plot(measure.current,measure.voltage)
                #plt.show()
                #print("Current Site Resistance: ", SiteResistance)
                #velox.SetDieMapResult(SiteResistance)
                #Create a temporary list to hold the measurement information. 
                #tempdf = [iDieX,iDieY,iSubDie,sSubDieLabel,SiteResistance]
                
                #check the dataframe length so we can append to the end. 
                #dataframePos = len(measurementData)
                #append the dataframe
               # measurementData.loc[dataframePos] = tempdf  
                
                #take a picture of the probe site after moving to sep. pos.
                #velox.MoveChuckSeparation()
                #time.sleep(0.05)
                #velox.SnapImage('Scope',r'C:/Lot/'+str(iDieX)+"_"+str(iDieY)+"_"+sSubDieLabel+'Afer.jpg',0)
                if tuple([i,j]) == endsite:
                    break
                try:
                    velox.StepNextDie()
                except:
                    velox.StepNextDie()
                    print("failed to pattern req")
                    pass
                
                
                
    elif site == (1,0):
        
        for i in range(iDieSamplePlan):
            print("Testing Die ", str(velox.ReadMapPosition2().DieX)+","+str(velox.ReadMapPosition2().DieY))
            for j in range(iSubDieCount):
                
                    
                sReadMapPosition = velox.ReadMapPosition2()
                iDieX = sReadMapPosition.DieX
                iDieY = sReadMapPosition.DieY
                iSubDie = sReadMapPosition.CurSite
                sSubDieLabel = velox.GetSubDieLabelAsNum()
                print("Testing site ", sSubDieLabel)
                
                #put the chuck into contact with the probe pins
                #velox.MoveChuckContact()
                #stablize for 100mSec
                time.sleep(0.1)
                
                #SweepTable = IVSweep(samples, start, end, delayTime)
                #time.sleep(0.1)
                #ivDF = pd.DataFrame(SweepTable)
                #ivDF.to_csv(r'C:/Lot/'+lotID+str(" ")+str(iDieX)+"_"+str(iDieY)+sSubDieLabel,sep=",")
                
                #SiteResistance = CalcResistance(SweepTable.current,SweepTable.voltage)
                
                #check if the resistance is outside of this arbitrary limit. 
                #if it is, clip it. 
                #if SiteResistance > iUpperLimit:
                    #SiteResistance = iUpperLimit
                #elif SiteResistance < iLowerLimit:
                    #SiteResistance = iLowerLimit
                
                print("Current Site Resistance: Test Routine")
                #velox.SetDieMapResult(SiteResistance)
                #Create a temporary list to hold the measurement information. 
                #tempdf = [iDieX,iDieY,iSubDie,sSubDieLabel,SiteResistance]
                
                #check the dataframe length so we can append to the end. 
                #dataframePos = len(measurementData)
                #append the dataframe
                #measurementData.loc[dataframePos] = tempdf  
                
                #take a picture of the probe site after moving to sep. pos.
                #velox.MoveChuckSeparation()
                #time.sleep(0.05)
                #velox.SnapImage('Scope',r'C:/Lot/'+str(iDieX)+"_"+str(iDieY)+"_"+sSubDieLabel+'Afer.jpg',0)
                if tuple([i,j]) == endsite:
                    break
                try:
                    velox.StepNextDie()
                except:
                    velox.StepNextDie()
                    print("failed to pattern req")
                    pass
                
    #measurementData.to_csv(r'C:/Lot/'+str(lotID)+".csv",sep=',')
    
    #plotBoxPlot(measurementData)
    #plotHistogram(measurementData)
    #plotWaferMap(measurementData)
    
    
    
    return measurementData




def StartWaferTest(lotID,samples,start,end,delayTime,profile = False,iUpperLimit=1000,iLowerLimit=-1000):
    
    
   
    
    """
    Measures a wafer using IVSweep function where the user specifies the
    lot ID, interval of the samples, start current, end current and 
    delay period between each sample measurement. 
    
    Args:
        lotID:string = 1234567-22RN6
        samples:int = 100 
        start:float = 0.00001 (10microAmps)
        end:float = 0.0001 (100microAmps)
        delayTime:float = 0.01 (10mSec)
    
    Example:StartWaferTest(lotID,100,0.00001,0.0001,0.01,profile = false)
    """
    
    #prior to starting the measurement, map the surface contour for better contact
   
    
   #TODO. Come back and fix the logic here for creating a directory. 
    os.chdir(path) 
    bDirExists = os.path.isdir(lotID)
    if bDirExists != True:
        os.mkdir(lotID)
        os.chdir(lotID)
        os.mkdir("Plots")
        os.mkdir("Measurements")
        os.mkdir("Images")
        
    else:
        os.chdir(lotID)
        bPlots = os.path.isdir("Plots")
        if bPlots != True:
            os.mkdir("Plots")
        bMeasurements = os.path.isdir("Measurements")   
        if bMeasurements !=True:
            os.mkdir("Measurements")
        bImages = os.path.isdir("Images")
        if bImages != True:
            os.mkdir("Images")
    #need to assign image path due to the way velox.SnapImage works with #FullPath 
    imagePath = os.path.join(path,lotID,"Images")
            
            
        
   
    if profile == True:
        velox.DoWaferProfiling()
        
    
    measurementVariables = ['DieX', 
                            'DieY',
                            'SiteNumber',
                            'Site', 
                            'Resistance']
    measurementData = pd.DataFrame(columns=measurementVariables)
    dataFrameTypes = {'DieX':int,
                      'DieY':int,
                      'SiteNumber':int,
                      'Site':str,
                      'Resistance':float,
                      }
    measurementData.astype(dataFrameTypes)

    
    

    #gets the number of die to measure in the wafer map
    iDieSamplePlan = int(velox.GetNumSelectedDies())


    #read the Map Position that is currently active. This requires the system  
    #to have passed pattern recognition at the site if Automation function is trained
    sReadMapPosition = velox.ReadMapPosition2()
    site = tuple([sReadMapPosition.CurDie,sReadMapPosition.CurSite])
    iSubDieCount = velox.GetDieInfo()
    endsite = tuple([iDieSamplePlan-1,iSubDieCount-1])
    
      
    if site != (1,0):
        #if the system is not currently at the first die in the map, move there
        try:
            sStepFirstDie = velox.StepFirstDie()
        except:
            print("failed to pattern req")
            sStepFirstDie = velox.StepFirstDie()
            sReadMapPosition = velox.ReadMapPosition2()
            
        
        #test plan will kick off.     
        for i in range(iDieSamplePlan):
            print("Testing Die ", str(velox.ReadMapPosition2().DieX)+","+str(velox.ReadMapPosition2().DieY))
            for j in range(iSubDieCount):
                   
                sReadMapPosition = velox.ReadMapPosition2()
                iDieX = sReadMapPosition.DieX
                iDieY = sReadMapPosition.DieY
                iSubDie = sReadMapPosition.CurSite
                sSubDieLabel = velox.GetSubDieLabelAsNum()
                print("Testing site ", sSubDieLabel)
                
                #put the chuck into contact with the probe pins
                velox.MoveChuckContact()
                #stablize for 100mSec
                time.sleep(0.1)
                
                SweepTable = IVSweep(samples, start, end, delayTime)
                time.sleep(0.05)
                ivDF = pd.DataFrame(SweepTable)
                
                #ivDF.to_csv(r'C:/Lot/'+lotID+str(" ")+str(iDieX)+"_"+str(iDieY)+sSubDieLabel,sep=",")
                ivDF.to_csv('Measurements'+'/'+str(lotID)+str(" ")+str(iDieX)+"_"+str(iDieY)+sSubDieLabel,sep=",")
                
                SiteResistance = CalcResistance(SweepTable.current,SweepTable.voltage)
                """
                Check if SiteResistance is above or below this arbitrary value 
                and cap it to avoid the charts getting massive limit ranges
    
                """
                if SiteResistance > iUpperLimit:
                    SiteResistance = iUpperLimit
                elif SiteResistance < iLowerLimit:
                    SiteResistance = iLowerLimit
                    
                #plt.plot(measure.current,measure.voltage)
                #plt.show()
                print("Current Site Resistance: ", SiteResistance)
                velox.SetDieMapResult(SiteResistance)
                #Create a temporary list to hold the measurement information. 
                tempdf = [iDieX,iDieY,iSubDie,sSubDieLabel,SiteResistance]
                
                #check the dataframe length so we can append to the end. 
                dataframePos = len(measurementData)
                #append the dataframe
                measurementData.loc[dataframePos] = tempdf  
                
                #take a picture of the probe site after moving to sep. pos.
                velox.MoveChuckSeparation()
                time.sleep(0.01)
                velox.SnapImage('Scope',str(imagePath)+"\\"+str(lotID)+"_"+str(iDieX)+"_"+str(iDieY)+"_"+sSubDieLabel+"_"+'Afer.jpg',0)
                #v2 velox.SnapImage('Scope',r'C:/Lot/'+str(lotID)+"_"+str(iDieX)+"_"+str(iDieY)+"_"+sSubDieLabel+"_"+'Afer.jpg',0)
                #velox.SnapImage('Scope',str(iDieX)+"_"+str(iDieY)+"_"+sSubDieLabel+'Afer.jpg',0)
                if tuple([i,j]) == endsite:
                    break
                try:
                    velox.StepNextDie()
                except:
                    velox.StepNextDie()
                    print("failed to pattern req")
                    pass
                
                
                
    elif site == (1,0):
        
        for i in range(iDieSamplePlan):
            print("Testing Die ", str(velox.ReadMapPosition2().DieX)+","+str(velox.ReadMapPosition2().DieY))
            for j in range(iSubDieCount):
                
                    
                sReadMapPosition = velox.ReadMapPosition2()
                iDieX = sReadMapPosition.DieX
                iDieY = sReadMapPosition.DieY
                iSubDie = sReadMapPosition.CurSite
                sSubDieLabel = velox.GetSubDieLabelAsNum()
                print("Testing site ", sSubDieLabel)
                
                #put the chuck into contact with the probe pins
                velox.MoveChuckContact()
                #stablize for 100mSec
                time.sleep(0.1)
                
                SweepTable = IVSweep(samples, start, end, delayTime)
                time.sleep(0.05)
                ivDF = pd.DataFrame(SweepTable)
                ivDF.to_csv('Measurements'+'/'+str(lotID)+str(" ")+str(iDieX)+"_"+str(iDieY)+sSubDieLabel,sep=",")
                
                SiteResistance = CalcResistance(SweepTable.current,SweepTable.voltage)
                
                #check if the resistance is outside of this arbitrary limit. 
                #if it is, clip it. 
                if SiteResistance > iUpperLimit:
                    SiteResistance = iUpperLimit
                elif SiteResistance < iLowerLimit:
                    SiteResistance = iLowerLimit
                
                print("Current Site Resistance: ", SiteResistance)
                velox.SetDieMapResult(SiteResistance)
                #Create a temporary list to hold the measurement information. 
                tempdf = [iDieX,iDieY,iSubDie,sSubDieLabel,SiteResistance]
                
                #check the dataframe length so we can append to the end. 
                dataframePos = len(measurementData)
                #append the dataframe
                measurementData.loc[dataframePos] = tempdf  
                
                #take a picture of the probe site after moving to sep. pos.
                velox.MoveChuckSeparation()
                time.sleep(0.01)
                velox.SnapImage('Scope',str(imagePath)+"\\"+str(lotID)+"_"+str(iDieX)+"_"+str(iDieY)+"_"+sSubDieLabel+"_"+'Afer.jpg',0)
                #v2 velox.SnapImage('Scope',r'C:/Lot/'+str(lotID)+"/"+str(lotID)+"_"+str(iDieX)+"_"+str(iDieY)+"_"+sSubDieLabel+"_"+'Afer.jpg',0)
                #velox.SnapImage('Scope',str(iDieX)+"_"+str(iDieY)+"_"+sSubDieLabel+'Afer.jpg',0)
                if tuple([i,j]) == endsite:
                    break
                try:
                    velox.StepNextDie()
                except:
                    velox.StepNextDie()
                    print("failed to pattern req")
                    pass
                
    measurementData.to_csv(str(lotID)+".csv",sep=',')
    
    plotBoxPlot(measurementData)
    plotHistogram(measurementData)
    plotWaferMap(measurementData)
    
    
    
    return measurementData

#-----------------------------------------------------------------------------
# VELOX Code 
#-----------------------------------------------------------------------------





#-----------------------------------------------------------------------------
# Plotting Code 
#----------------------------------------------------------------------------- 
def plotIWDCData(df):
    df.groupby("Site")["Resistance"].plot(figsize=(15,5), title="IWDC Test Structures" )
    plt.legend(bbox_to_anchor=(1, 1), loc='upper left', ncol=1)
    plt.tight_layout()
    
    
def plotHistogram(df):
    
    df['Resistance'].hist(by=df['Site'],density= True, figsize=(15,12))
    plt.tight_layout()
    plt.ylabel("Resistance")
    plt.tight_layout()
    plt.title(lotID)
    plt.savefig('Plots'+'/'+str(lotID)+"_Histogram"+".jpg",sep=',')
    plt.close()
    


def plotBoxPlot(df):
   
    df.boxplot(column=['Resistance'],by='Site', rot=90,figsize=(10,7))
    plt.ylabel("Resistance")
    plt.tight_layout()
    plt.title(lotID)
    plt.savefig('Plots'+'/'+str(lotID)+"_BoxPlot"+".jpg",sep=',')
    plt.close()

def plotWaferMap(df):
    #requires the import of seaborn as sns 
    SiteList = []
    for i, g in df.groupby(['Site']):
        SiteList.append(g)
                  
    for i in range(len(SiteList)):
        dieDataList = SiteList[i]
        time.sleep(.1)
        Z = dieDataList.pivot_table(index='DieX',columns='DieY',values='Resistance').T.values
        time.sleep(.1)
        fig, ax = plt.subplots(figsize=(5,5))
        sns.heatmap(Z,cmap='jet',cbar_kws={'label': 'Resistance'}).set_title(dieDataList.iloc[0,3])
        plt.suptitle(lotID,fontsize=18)
        xTicks = sorted(dieDataList['DieX'].unique())
        yTicks = sorted(dieDataList['DieY'].unique(),reverse=True)
        ax.set_yticklabels(yTicks)
        ax.set_xticklabels(xTicks)
        
        plt.savefig('Plots'+'/'+str(lotID)+"_HeatMap"+dieDataList.iloc[0,3]+".jpg",sep=',')
        time.sleep(.1)
        plt.close()
    


    


#plot a single sites values 

################### INCOMPLETE ################################
# SiteList = []
# for i, g in iWDC954_22R6A.groupby(['Site']):
#     SiteList.append(g)
# plt.plot(SiteList[17]['Resistance']) 


#-----------------------------------------------------------------------------
# END Plotting Code 
#-----------------------------------------------------------------------------   
