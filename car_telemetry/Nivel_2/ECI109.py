#  ECI API function definitions for all IXXAT Interfaces.
#
#  Header file of the ECI ( embedded / real time communication interface),
#  a generic library for IXXAT hardware interfaces.
#
#  ~~~~~~~~~~~~
#
#  PCAN-Basic API
#
#  ~~~~~~~~~~~~
#
#  ------------------------------------------------------------------
#  Author      : Michael Hengler
#  Last change : 17.07.2014 Hengler
#
#  Language    : Python 2.7
#  ------------------------------------------------------------------

# Module Imports
#
from ctypes import *  # @UnusedWildImport

from ECI_hwtype import *  # @UnusedWildImport
from ECI_error import *  # @UnusedWildImport
from ECI_logging import *  # @UnusedWildImport

# ///////////////////////////////////////////////////////////
# ECI-Basic API function declarations
# ///////////////////////////////////////////////////////////

# ECI-Basic API class implementation
#
class ECI109:
    """
      ECI-Basic API class implementation
    """      
    def __init__(self):
        # Loads the ECI.so
        #     
        self.dll = cdll.LoadLibrary("libeci109DriverLinux.so")
        if self.dll == None:
            print("Exception: The ECI-Basic shared library couldn't be loaded!")

    """
    Initializes the ECI internal hardware structures. This function must be
    called at first. After that the ECI is in the state ECI_INITIALIZED.

    @param dwCount
      Number of defined hardware parameters defined in ECI_HW_PARA.
    @param astcHwPara
      Array of structure of ECI_HW_PARA to define hardware parameters, which 
      cannot be obtained from the OS.
      ( e.g. ISA-card: memory-Address and the interrupt line)
    
    @retval ECI_RESULT
      ECI_OK on success, otherwise an error code from the @ref e_ECIERROR "ECI error list".
    
    @ingroup EciApi
    
    @note
      Calling this function invalidates all already distributed controller handles!
    """
    def ECIDRV_Initialize (
        self,
        dwCount,
        astcHwPara):
        
        try:
            res = self.dll.ECI109_Initialize(DWORD(dwCount), byref(astcHwPara))
            return res
        except :
            print("Exception on ECIBasic.Initialize")
            raise

    """
    Releases the ECI internal hardware structures and any initializations made
    by the user before. After that the ECI is in the state ECI_UNINITIALIZED.
    
    @retval ECI_RESULT
      ECI_OK on success, otherwise an error code from the @ref e_ECIERROR "ECI error list".
    
    @ingroup EciApi
    
    @note
      Calling this function invalidates all already distributed controller handles!
    """
    def ECIDRV_Release (self):
        try:
            res = self.dll.ECI109_Release()
            return res
        except:
            print("Exception on ECIBasic.ECIDRV_Release")
            raise

    """
    This function returns information of the hardware given by index.
    
    The following information is available:
      - firmware version
      - number of available controllers
      - controller types
      - controller states
    
    @param dwHwIndex
      Index of hardware resp. index into the astcHwPara array (hardware dependent).
    @param pstcHwInfo
      Pointer to ECI_HW_INFO which receives the hardware information.
    
    @retval ECI_RESULT
      ECI_OK on success, otherwise an error code from the @ref e_ECIERROR "ECI error list".
    
    @ingroup EciApi
    """
    def ECIDRV_GetInfo (
        self,
        dwHwIndex,
        pstcHwInfo):
        try:
            res = self.dll.ECI109_GetInfo(dwHwIndex, byref(pstcHwInfo))
            return res
        except:
            print("Exception on ECIBasic.ECIDRV_GetInfo")
            raise

    """
    Function to open and / or initialize a controller of the given hardware. 
    The hardware has to be initialized before by calling ECIDRV_Initialize.
    
    The function:
      - loads and starts the firmware (if necessary)
      - initializes the controllerECIDRV_Initialize
      - delivers a handle for further controller usage
    After that the controller can be started.
    
    This function can also be used to re-configure the controller e.g. changing
    the baud rate without closing the controller handle. Therefore the controller 
    has to be stopped by calling ECIDRV_CtrlStop before. The controller handle 
    does not change and thus remains valid. It also saves time by avoiding 
    reconfiguration of the whole ECI interface.
    
    ECI library state transition: (for the first controller opened)
      ECI_INITIALIZED -> ECI_CONFIGURED
    
    ECI controller state transition: (if controller was closed before)
      ECI_CTRL_UNCONFIGURED -> ECI_CTRL_INITIALIZED
    
    @param phCtrl
      Pointer to ECI_CTRL_HDL which receives the handle to the controller.
    @param dwHwIndex
      Index of hardware resp. index into the astcHwPara array (hardware dependent).
    @param dwCtrlIndex
      Index of the controller (LIN or CAN) to initialize (hardware relative).
    @param pstcCtrlConfig
      Pointer to ECI_CTRL_CONFIG which holds the configuration to initialize
      the controller.
    
    @retval ECI_RESULT
      ECI_OK on success, otherwise an error code from the @ref e_ECIERROR "ECI error list".
    
    @ingroup EciApi
    
    @see ECIDRV_CtrlClose
    """
    def ECIDRV_CtrlOpen (
        self,
        phCtrl,
        dwHwIndex,
        dwCtrlIndex,
        pstcCtrlConfig):
        try:
            res = self.dll.ECI109_CtrlOpen(byref(phCtrl), dwHwIndex, dwCtrlIndex, byref(pstcCtrlConfig))
            return res
        except:
            print( "Exception on ECIBasic.ECIDRV_CtrlOpen")
            raise

    """
    Function to close the controller. After this function, the initialization 
    settings are lost and the controller is in ECI_CTRL_UNCONFIGURED state. The
    passed controller handle becomes invalid and should afterwards be set to
    ECI_INVALID_HANDLE.
    
    ECI library state transition:  (for the last controller closed)
      ECI_CONFIGURED -> ECI_INITIALIZED
    
    ECI controller state transition:
      ECI_CTRL_INITIALIZED or ECI_CTRL_RUNNING -> ECI_CTRL_UNCONFIGURED
    
    @param hCtrl
      Controller handle
    
    @retval ECI_RESULT
      ECI_OK on success, otherwise an error code from the @ref e_ECIERROR "ECI error list".
    
    @ingroup EciApi
    
    @see ECIDRV_CtrlOpen
    """
    def ECIDRV_CtrlClose (
        self,
        hCtrl):
        try:
            res = self.dll.ECI109_CtrlClose(hCtrl)
            return res
        except:
            print("Exception on ECIBasic.ECIDRV_CtrlClose")
            raise


    """
    Function to start the controller communication.
    
    ECI controller state transition:
      ECI_CTRL_INITIALIZED -> ECI_CTRL_RUNNING
    
    @param hCtrl
      Controller handle
    
    @retval ECI_RESULT
      ECI_OK on success, otherwise an error code from the @ref e_ECIERROR "ECI error list".
    
    @ingroup EciApi
    
    @see ECIDRV_CtrlStop
    """
    def ECIDRV_CtrlStart (
        self,
        hCtrl):
        try:
            res = self.dll.ECI109_CtrlStart(hCtrl)
            return res
        except:
            print("Exception on ECIBasic.ECIDRV_CtrlStart")
            raise    

    """
    Function to stop the controller communication.
    
    ECI state transition:
      ECI_CTRL_RUNNING -> ECI_CTRL_INITIALIZED
    
    @param hCtrl
      Controller handle
    @param dwMode (bit field)
      Different stop mode bits defined in e_STOP_FLAGS.
    
    @retval ECI_RESULT
      ECI_OK on success, otherwise an error code from the @ref e_ECIERROR "ECI error list".
    
    @ingroup EciApi
    
    @see ECIDRV_CtrlStart
    """
    def ECIDRV_CtrlStop  (
        self,
        hCtrl,
        dwMode):
        try:
            res = self.dll.ECI109_CtrlStop(hCtrl, dwMode)
            return res
        except:
            print("Exception on ECIBasic.ECIDRV_CtrlStop")
            raise    


    """
    Returns the capabilities of the controller. 
    
    @param hCtrl
      Controller handle
    @param pstcCapabilities
      Pointer to ECI_CTRL_CAPABILITIES which receives the controller capabilities.
    
    @retval ECI_RESULT
      ECI_OK on success, otherwise an error code from the @ref e_ECIERROR "ECI error list".
    
    @ingroup EciApi
    """
    
    def ECIDRV_CtrlGetCapabilities (
        self,
        hCtrl,
        pstcCapabilities):
        try:
            res = self.dll.ECI109_CtrlGetCapabilities(hCtrl, byref(pstcCapabilities))
            return res
        except:
            print("Exception on ECIBasic.ECIDRV_CtrlGetCapabilities")
            raise

    """
    Sets the update rate in milliseconds of the ECI_CTRL_STATUS which can be
    retrieved with ECIDRV_CtrlGetStatus. The ECI_CTRL_STATUS has a default
    interval of 50 ms. To increase or decrease the interval you need to set
    a new update rate.
    
    @param hCtrl
      Controller handle
    @param dwUpdateRate
      Status update rate in milliseconds.
    
    @retval ECI_RESULT
      ECI_OK on success, otherwise an error code from the @ref e_ECIERROR "ECI error list".
    
    @ingroup EciApi
      """

    def ECIDRV_CtrlSetStatusUpdateRate (
        self,
        hCtrl,
        dwUpdateRate):
        try:
            res = self.dll.ECI109_CtrlSetStatusUpdateRate(hCtrl, dwUpdateRate)
            return res
        except:
            print("Exception on ECIBasic.ECIDRV_CtrlSetStatusUpdateRate")
            raise

    """
    Returns the current status of the controller. 
    
    @param hCtrl
      Controller handle
    @param pstcStatus
          Pointer to ECI_CTRL_STATUS which receives the controller status.
          The ECI_CTRL_STATUS union structure uses a version number mechanism to
          distinguish different unions. To tell the ECI API to allow other union
          versions than ECI_STRUCT_VERSION_V0, the dwVer parameter has to be configured
          accordingly. Setting ECI_CANSTATUS.dwVer to ECI_STRUCT_VERSION_V1 enables
          full CAN FD controller status support for instance.
  
    @retval ECI_RESULT
      ECI_OK on success, otherwise an error code from the @ref e_ECIERROR "ECI error list".
    
    @ingroup EciApi
    """
    def ECIDRV_CtrlGetStatus (
        self,
        hCtrl,
        pstcStatus):
        try:
            res = self.dll.ECI109_CtrlGetStatus(hCtrl, byref(pstcStatus))
            return res
        except:
            print("Exception on ECIBasic.ECIDRV_CtrlGetStatus")
            raise   

    """
    Writes on message to the controller's TX FIFO. Therefore the controller has 
    to be in the ECI_CTRL_RUNNING state.
    
    @param hCtrl
      Controller handle
    @param pstcMessage
      Pointer to ECI_CTRL_MESSAGE which holds the message to send.
    @param dwTimeout
      Timeout in [ms] to wait for successful transmission.
      (Waits until the message could be written into the TX FIFO, dependent from 
       hardware type) @n
      Following pre-defined values can be used for polling or blocking mode:
      @ref ECI_NO_WAIT, @ref ECI_WAIT_FOREVER
    
    @retval ECI_RESULT
      ECI_OK on success, otherwise an error code from the @ref e_ECIERROR "ECI error list".
    
    @note
      If driver is running in polling mode, the timeout value must be
      configured to zero. Timeout handling is not available in polling
      mode and must be handled by the user as follows:
      Message transmission:
      * Call ECIDRV_CtrlSend without timeout.
      * If function returns with success you can immediately call this
        function again.
      * If function returns with error, wait some time, e.g. 1 ms
        by calling \ref OS_Sleep before calling this function again.
        Please also refer to \ref api_InterruptVsPolling.
    
    @ingroup EciApi
    """
    def ECIDRV_CtrlSend (
        self,
        hCtrl,
        pstcMessage,
        dwTimeout):
        try:
            res = self.dll.ECI109_CtrlSend(hCtrl, byref(pstcMessage), dwTimeout)
            return res
        except:
            print("Exception on ECIBasic.ECIDRV_CtrlSend")
            raise   
    

    """
    Reads one or messages from the controller's RX FIFO. Therefore the 
    controller has to be in the ECI_CTRL_INITIALIZED or ECI_CTRL_RUNNING state.
    
    This function should be called the after controller is started to ensure no 
    receive messages are lost. This is also necessary if no message reception
    is expected at this time. The ECI interface sends status and timer messages
    to the ECI API which have to processed by the ECI internally. This is done 
    in the ECIDRV_CtrlReceive function to avoid thread locking and thread
    synchronization overhead.
    
    @param hCtrl
      Controller handle
    @param pdwCount
      Pointer to DWORD @n
      [in] : Holds the number of entries of ECI_CTRL_MESSAGE which should be 
             retrieved. @n
      [out]: Number of entries of ECI_CTRL_MESSAGE copied into.
    @param pstcMessage
      Pointer to ECI_CTRL_MESSAGE which receives the message(s) read from RX FIFO.
    @param dwTimeout
      Timeout in [ms] to wait for message reception.
      (Waits until one or more messages could be read from the RX FIFO, dependent 
      from hardware type) @n
      Following pre-defined values can be used for polling or blocking mode:
      @ref ECI_NO_WAIT, @ref ECI_WAIT_FOREVER
    
    @retval ECI_RESULT
      ECI_OK on success, otherwise an error code from the @ref e_ECIERROR "ECI error list".
    
    @note
      If driver is running in polling mode, the timeout value must be
      configured to zero. Timeout handling is not available in polling
      mode and must be handled by the user as follows:
      Message reception:
      * Call ECIDRV_CtrlReceive without timeout.
      * If function returns with success immediately call this function again.
      * If function returns with no message, wait some time, e.g. 1 ms
        by calling \ref OS_Sleep before calling this function again.
        Please also refer to \ref api_InterruptVsPolling.
    
    @ingroup EciApi
    """
    def ECIDRV_CtrlReceive (
        self,
        hCtrl,
        pdwCount,
        pstcMessage,
        dwTimeout):
        try:
            res = self.dll.ECI109_CtrlReceive(hCtrl, byref(pdwCount), byref(pstcMessage), dwTimeout)
            return res
        except:
            print("Exception on ECIBasic.ECIDRV_CtrlReceive")
            raise   

    """
    Function to configure message filtering for the acceptance filter.
    
    @param hCtrl
      Controller handle
    @param pstcFilter
      Pointer ECI_CTRL_FILTER which holds the filter settings to be set.
    
    @retval ECI_RESULT
      ECI_OK on success, otherwise an error code from the @ref e_ECIERROR "ECI error list".
    
    @ingroup EciApi
    """
    def ECIDRV_CtrlSetAccFilter(
        self,
        hCtrl,
        pstcFilter):
        try:
            res = self.dll.ECI109_CtrlSetAccFilter(hCtrl,
                                                   byref(pstcFilter))
            return res
        except:
            print("Exception on ECIBasic.ECIDRV_CtrlSetFilter")
            raise
            
    """
    Function to add one or more ids for message filtering.
    
    @param hCtrl
      Controller handle
    @param pstcFilter
      Pointer ECI_CTRL_FILTER which holds the filter settings to be set.
    
    @retval ECI_RESULT
      ECI_OK on success, otherwise an error code from the @ref e_ECIERROR "ECI error list".
    
    @ingroup EciApi
    """
    def ECIDRV_CtrlAddFilterIds(
        self,
        hCtrl,
        pstcFilter):
        try:
            res = self.dll.ECI109_CtrlAddFilterIds(hCtrl,
                                                   byref(pstcFilter))
            return res
        except:
            print("Exception on ECIBasic.ECIDRV_CtrlSetFilter")
            raise
            
    """
    Function to remove one or more ids from message filtering.
    
    @param hCtrl
      Controller handle
    @param pstcFilter
      Pointer ECI_CTRL_FILTER which holds the filter settings to be set.
    
    @retval ECI_RESULT
      ECI_OK on success, otherwise an error code from the @ref e_ECIERROR "ECI error list".
    
    @ingroup EciApi
    """
    def ECIDRV_CtrlRemFilterIds(
        self,
        hCtrl,
        pstcFilter):
        try:
            res = self.dll.ECI109_CtrlRemFilterIds(hCtrl,
                                                   byref(pstcFilter))
            return res
        except:
            print("Exception on ECIBasic.ECIDRV_CtrlSetFilter")
            raise

    """
    Function to send a user defined command to the driver or hardware.
    
    @param hCtrl
      Controller handle
    @param pstcCmdRequest
      Pointer to ECI_CTRL_CMDREQUEST which holds the request to send.
    @param pstcCmdResponse
      Pointer to ECI_CTRL_CMDRESPONSE which receives the response on success.
    @param dwTimeout
      Timeout in [ms] to wait for the response.
      Following pre-defined values can be used for polling or blocking mode:
      @ref ECI_NO_WAIT, @ref ECI_WAIT_FOREVER
    
    @retval ECI_RESULT
      ECI_OK on success, otherwise an error code from the @ref e_ECIERROR "ECI error list".
    
    @ingroup EciApi
    """
    def ECIDRV_CtrlCommand (
        self,
        hCtrl,
        pstcCmdRequest,
        pstcCmdResponse,
        dwTimeout):
        try:
            res = self.dll.ECI109_CtrlCommand(hCtrl, byref(pstcCmdRequest), byref(pstcCmdResponse), dwTimeout)
            return res
        except:
            print("Exception on ECIBasic.ECIDRV_CtrlCommand")
            raise   


    """
    Function to configure ECI API's build in logging mechanism.
    
    @param pstcConfig
      Pointer to ECI_LOG_CONFIG which holds the configuration to set.
    
    @retval ECI_RESULT
      ECI_OK on success, otherwise an error code from the @ref e_ECIERROR "ECI error list".
    
    @ingroup EciApi
    
    @note 
      This function can only be called if the logging is stopped. @n
      To set the logging API to uninitialized state, call this function with
      dwLogMode set to ECI_LOGGING_MODE_UNDEFINED and
      dwLogSources set to ECI_LOGGING_SOURCE_NONE and
       dwLogSize set to zero.
    """
    def ECIDRV_LogConfig (
        self,
        pstcConfig):
        try:
            res = self.dll.ECI109_LogConfig(byref(pstcConfig))
            return res
        except:
            print("Exception on ECIBasic.ECIDRV_LogConfig")
            raise   


    """
    Function to read one or more entries logged.
    
    @param pdwCount
      Pointer to DWORD @n
      [in] : Holds the number of entries of ECI_LOG_ENTRY which should be 
             retrieved. @n
      [out]: Number of entries of ECI_LOG_ENTRY received.
    @param astcEntry
      Array of ECI_LOG_ENTRY which receives the logging entries.
    @param dwTimeout
      Time to wait for the given amount of logging entries.
    
    @retval ECI_RESULT
      ECI_OK on success, otherwise an error code from the @ref e_ECIERROR "ECI error list".
    
    @ingroup EciApi
    """
    def ECIDRV_LogRead (
        self,
        pdwCount,
        astcEntry,
        dwTimeout):
        try:
            res = self.dll.ECI109_LogRead(byref(pdwCount), byref(astcEntry), dwTimeout)
            return res
        except:
            print("Exception on ECIBasic.ECIDRV_LogRead")
            raise   


    """
    Function to start the logging mechanism.
    
    @retval ECI_RESULT
      ECI_OK on success, otherwise an error code from the @ref e_ECIERROR "ECI error list".
    
    @ingroup EciApi
    """
    def ECIDRV_LogStart (self):
        try:
            res = self.dll.ECI109_LogStart()
            return res
        except:
            print("Exception on ECIBasic.ECIDRV_LogStart")
            raise   

    """
    Function to stop the logging mechanism.
    
    @retval ECI_RESULT
      ECI_OK on success, otherwise an error code from the @ref e_ECIERROR "ECI error list".
    
    @ingroup EciApi
    """
    def ECIDRV_LogStop (self):
        try:
            res = self.dll.ECI109_LogStop()
            return res
        except:
            print("Exception on ECIBasic.ECIDRV_LogStop")
            raise   


    """
    Function to delete all currently logged entries.
    
    @retval ECI_RESULT
      ECI_OK on success, otherwise an error code from the @ref e_ECIERROR "ECI error list".
    
    @ingroup EciApi
    
    @note This function can only be called if the logging is stopped.
    """
    def ECIDRV_LogClear (self):
        try:
            res = self.dll.ECI109_LogClear()
            return res
        except:
            print("Exception on ECIBasic.ECIDRV_LogClear")
            raise   

    """
    Function to retrieve a human readable error description of the given error
    code. The returned string is zero-terminated and valid until a further call
    (from any thread) to this function.
    
    @param dwError
      ECI error code to retrieve error description from
    
    @retval "const char*"
      Pointer to a zero-terminated error string.
    
    @see e_ECIERROR
    
    @ingroup EciApi
    
    @note An ECI error string can only be retrieved after a successful call of
      @ref ECIDRV_Initialize.
    """
    def ECIDRV_GetErrorString (
        self,
        dwError):
        try:
            self.dll.ECI109_GetErrorString.restype = c_char_p
            res = self.dll.ECI109_GetErrorString(dwError)

            return c_char_p(res).value 
        except:
            print("Exception on ECIBasic.ECIDRV_GetErrorString")
            raise   

