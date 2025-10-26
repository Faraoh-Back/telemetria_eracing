#
#  ECI API Demo common helper functions
#
#  converted from IXXAT example by Michael Ummenhofer (ummenhofer@ixxat.de)
#

# Module Imports
#
from ctypes import *  # @UnusedWildImport

from ECI_hwtype import *  # @UnusedWildImport
from ECI_error import *  # @UnusedWildImport


"""
Prints the given hardware information on the screen

@param pstcHwInfo
  Pointer to ECI_HW_INFO to print

@ingroup EciDemo
"""
def EciPrintHwInfo(pstcHwInfo):

    if None == pstcHwInfo:
        print ("ERROR: invalid pointer: pstcHwInfo")
        return
    
    print( "HwInfoVer: \"%u\"" %
          pstcHwInfo.dwVer)
    
    # Struct Version 0
    if pstcHwInfo.dwVer == ECI_STRUCT_VERSION_V0 or pstcHwInfo.dwVer == ECI_STRUCT_VERSION_V1:
        dwCtrlIndex = 0
    
        print("BoardType: \"%s\"" %
              pstcHwInfo.u.V0.szHwBoardType)
        print("HwSerial : \"%s\"" %
              pstcHwInfo.u.V0.szHwSerial)
        print("HwVersion: \"%u.%u.%u.%u\"" %
              (pstcHwInfo.u.V0.abHwVersion[0],
              pstcHwInfo.u.V0.abHwVersion[1],
              pstcHwInfo.u.V0.abHwVersion[2],
              pstcHwInfo.u.V0.abHwVersion[3]))
        print("BmVersion: \"%u.%u.%u.%u\"" %
              (pstcHwInfo.u.V0.abBmVersion[0],
              pstcHwInfo.u.V0.abBmVersion[1],
              pstcHwInfo.u.V0.abBmVersion[2],
              pstcHwInfo.u.V0.abBmVersion[3]))
        print("FwIdentif: \"%s\"" %
              pstcHwInfo.u.V0.szFwIdentification)
        print("FwVersion: \"%u.%u.%u.%u\"" %
              (pstcHwInfo.u.V0.abFwVersion[0],
              pstcHwInfo.u.V0.abFwVersion[1],
              pstcHwInfo.u.V0.abFwVersion[2],
              pstcHwInfo.u.V0.abFwVersion[3]))
        print("EciApiVer: \"%u.%u.%u.%u\"" %
              (pstcHwInfo.u.V0.adwApiVersion[0],
              pstcHwInfo.u.V0.adwApiVersion[1],
              pstcHwInfo.u.V0.adwApiVersion[2],
              pstcHwInfo.u.V0.adwApiVersion[3]))
        
        print("DevId    : \"%u\"" %
              pstcHwInfo.u.V1.dwDevId)

        print("CtrlCount: \"%u\"" %
              pstcHwInfo.u.V0.dwCtrlCount)

        for dwCtrlIndex in range (dwCtrlIndex, pstcHwInfo.u.V0.dwCtrlCount):
            print("CtrlIndex: \"%u\"" %
                  dwCtrlIndex)
            print("CtrlClass: \"0x%04x\"" %
                  pstcHwInfo.u.V0.sCtrlInfo[dwCtrlIndex].wCtrlClass)
            print("CtrlState: \"0x%04x\"" %
                  pstcHwInfo.u.V0.sCtrlInfo[dwCtrlIndex].wCtrlState)


"""  
Prints the given controller capabilities on the screen

@param pstcCtrlCaps
  Pointer to ECI_CTRL_CAPABILITIES to print

@ingroup EciDemo
"""
def EciPrintCtrlCapabilities(pstcCtrlCaps):
    if None == pstcCtrlCaps:
        print("ERROR: invalid pointer: pstcCtrlCaps")
        return

    # Switch on controller class
    if pstcCtrlCaps.wCtrlClass == ECI_CTRL_CAN:
        print("CapsVer  : \"%u\"" %
              pstcCtrlCaps.u.sCanCaps.dwVer)

        # Struct Version 0
        if pstcCtrlCaps.u.sCanCaps.dwVer == ECI_STRUCT_VERSION_V0:
            print("CanType  : \"0x%04x\"" %
                  pstcCtrlCaps.u.sCanCaps.u.V0.wCanType)
            print("BusCoupl : \"0x%04x\"" %
                  pstcCtrlCaps.u.sCanCaps.u.V0.wBusCoupling)
            print("Feature  : \"0x%04x\"" %
                  pstcCtrlCaps.u.sCanCaps.u.V0.dwFeatures)
            print("ClockFreq: \"%u\"" %
                  pstcCtrlCaps.u.sCanCaps.u.V0.dwClockFreq)
            print("TscDiv   : \"%u\"" %
                  pstcCtrlCaps.u.sCanCaps.u.V0.dwTscDivisor)
            print("DtxDiv   : \"%u\"" %
                  pstcCtrlCaps.u.sCanCaps.u.V0.dwDtxDivisor)
            print("DtxMaxTic: \"%u\"" %
                  pstcCtrlCaps.u.sCanCaps.u.V0.dwDtxMaxTicks)
            print("PrioQueue: \"%u\"" %
                  pstcCtrlCaps.u.sCanCaps.u.V0.dwNoOfPrioQueues)

    elif pstcCtrlCaps.wCtrlClass == ECI_CTRL_LIN:
        print("CapsVer  : \"%u\"" %
              pstcCtrlCaps.u.sCanCaps.dwVer)

        # Struct Version 0
        if pstcCtrlCaps.u.sLinCaps.dwVer == ECI_STRUCT_VERSION_V0:
            print("LinType  : \"0x%04x\"" %
                  pstcCtrlCaps.u.sLinCaps.u.V0.wLinType)
            print("BusCoupl : \"0x%04x\"" %
                  pstcCtrlCaps.u.sLinCaps.u.V0.wBusCoupling)
            print("Feature  : \"0x%04x\"" %
                  pstcCtrlCaps.u.sLinCaps.u.V0.dwFeatures)
            print("ClockFreq: \"%u\"" %
                  pstcCtrlCaps.u.sLinCaps.u.V0.dwClockFreq)
            print("TscDiv   : \"%u\"" %
                  pstcCtrlCaps.u.sLinCaps.u.V0.dwTscDivisor)
            print("DtxDiv   : \"%u\"" %
                  pstcCtrlCaps.u.sLinCaps.u.V0.dwDtxDivisor)
            print("DtxMaxTic: \"%u\"" %
                  pstcCtrlCaps.u.sLinCaps.u.V0.dwDtxMaxTicks)
            print("PrioQueue: \"%u\"" %
                  pstcCtrlCaps.u.sLinCaps.u.V0.dwNoOfPrioQueues)
    else:
        pass


"""
Prints the given controller message on the screen

@param pstcCtrlMsg
  Pointer to ECI_CTRL_MESSAGE to print

@ingroup EciDemo
"""
def EciPrintCtrlMessage(pstcCtrlMsg, sameLine = False):
    if None == pstcCtrlMsg:
        print("ERROR: invalid pointer: pstcCtrlMsg")
        return

    # CAN
    if pstcCtrlMsg.wCtrlClass == ECI_CTRL_CAN:
        # Struct Version 0
        if(ECI_STRUCT_VERSION_V0 == pstcCtrlMsg.u.sCanMessage.dwVer):
            print("Time: %10u, Type: %2u, ID: %08X, Flags: %c%c%c%c " %
                   (pstcCtrlMsg.u.sCanMessage.u.V0.dwTime,
                   pstcCtrlMsg.u.sCanMessage.u.V0.uMsgInfo.Bits.type,
                   pstcCtrlMsg.u.sCanMessage.u.V0.dwMsgId,
                   'E' if pstcCtrlMsg.u.sCanMessage.u.V0.uMsgInfo.Bits.ext else ' ',
                   'R' if pstcCtrlMsg.u.sCanMessage.u.V0.uMsgInfo.Bits.rtr else ' ',
                   'S' if pstcCtrlMsg.u.sCanMessage.u.V0.uMsgInfo.Bits.srr else ' ',
                   'O' if pstcCtrlMsg.u.sCanMessage.u.V0.uMsgInfo.Bits.ovr else ' ')),

        # Print Data if not RTR
        if not pstcCtrlMsg.u.sCanMessage.u.V0.uMsgInfo.Bits.rtr:
            # Data available
            if pstcCtrlMsg.u.sCanMessage.u.V0.uMsgInfo.Bits.dlc:
                print("Data: "),
                for bIndex in range (0, pstcCtrlMsg.u.sCanMessage.u.V0.uMsgInfo.Bits.dlc):
                    print("%02X " % pstcCtrlMsg.u.sCanMessage.u.V0.abData[bIndex]),
        else:
            print("DLC: %u" % pstcCtrlMsg.u.sCanMessage.u.V0.uMsgInfo.Bits.dlc)

    # LIN
    elif pstcCtrlMsg.wCtrlClass == ECI_CTRL_LIN:
        # Struct Version 0
        if ECI_STRUCT_VERSION_V0 == pstcCtrlMsg.u.sLinMessage.dwVer:
            print("Time: %10u, Type: %2u, ID: %08X, Flags: %c%c%c%c " %
                   (pstcCtrlMsg.u.sLinMessage.u.V0.dwTime,
                   pstcCtrlMsg.u.sLinMessage.u.V0.uMsgInfo.Bits.type,
                   pstcCtrlMsg.u.sLinMessage.u.V0.dwMsgId,
                   'E' if pstcCtrlMsg.u.sLinMessage.u.V0.uMsgInfo.Bits.ecs else ' ',
                   'I' if pstcCtrlMsg.u.sLinMessage.u.V0.uMsgInfo.Bits.ido else ' ',
                   'S' if pstcCtrlMsg.u.sLinMessage.u.V0.uMsgInfo.Bits.sor else ' ',
                   'O' if pstcCtrlMsg.u.sLinMessage.u.V0.uMsgInfo.Bits.ovr else ' ')),

        # Print Data if not ID only
        if not pstcCtrlMsg.u.sLinMessage.u.V0.uMsgInfo.Bits.ido:
            # Data available
            if pstcCtrlMsg.u.sLinMessage.u.V0.uMsgInfo.Bits.dlc:
                print("Data: "),
                for bIndex in range(0, pstcCtrlMsg.u.sLinMessage.u.V0.uMsgInfo.Bits.dlc):
                    print("%02X " % pstcCtrlMsg.u.sLinMessage.u.V0.abData[bIndex]),
        else:
            print("DLC: %u" % pstcCtrlMsg.u.sLinMessage.u.V0.uMsgInfo.Bits.dlc),

    if sameLine:
        print "",
    else:
        print ""

"""
Returns the nth controller of given controller class.

@param pstcHwInfo
  Reference to ECI_HW_INFO to find controller from.

@param eCtrlClass
  Class of controller to find.

@param dwRelCtrlIndex
  Relative controller index of given controller class.

@param pdwCtrIndex
  Variable which receives the controller index.

@retval pdwCtrIndex
  returns the index of the nth controller of given controller class.

@ingroup EciDemo
"""
def EciGetNthCtrlOfClass(
    pstcHwInfo,
    eCtrlClass,
    dwRelCtrlIndex,
    pdwCtrIndex):
    
    
    hResult = ECI_ERR_RESOURCE_NOT_FOUND

    if ((None != pstcHwInfo) and (None != pdwCtrIndex)):
        # Struct Version 0
        if pstcHwInfo.dwVer == ECI_STRUCT_VERSION_V0: 
            # Iterate through all controllers
            for dwIndex in range (0, pstcHwInfo.u.V0.dwCtrlCount):
                if pstcHwInfo.u.V0.sCtrlInfo[dwIndex].wCtrlClass == eCtrlClass:
                    # Controller not found yet
                    if hResult != ECI_OK:
                        if dwRelCtrlIndex == 0:
                            # Controller found
                            pdwCtrIndex = dwIndex  # reqiures byref in the calling code 
                            # C code: *pdwCtrIndex = dwIndex
                            hResult = ECI_OK
                        else:
                            dwRelCtrlIndex -= 1
    else:
        hResult = ECI_ERR_INVALID_POINTER

    return pdwCtrIndex
