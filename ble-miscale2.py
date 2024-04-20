import sys
import asyncio
import binascii
import logging
from bleak import BleakScanner
from bleak import BleakClient
from bleak import BleakError
from bitstring import BitArray
from tg_bot import sendToTelegram

KNOWN_ADDR="5C:64:F3:12:21:9C" # MiScale2
SERVICE_WEIGHT_SCALE="0000181d-0000-1000-8000-00805f9b34fb" # Weight Service UUID

logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
stdoutHandler = logging.StreamHandler(sys.stdout)
stdoutHandler.setLevel(logging.DEBUG)
stdoutHandler.setFormatter(formatter)

fileHandler = logging.FileHandler('ble-miscale2.log')
fileHandler.setLevel(logging.DEBUG)
fileHandler.setFormatter(formatter)

logger.addHandler(stdoutHandler)
logger.addHandler(fileHandler)

PREVIOUS_VALUE = None

"""
Send message to telegram
"""
def sendMessage(msg):
    response = sendToTelegram(msg)
    logger.info("Request result: %s", response)

"""
Value is stable (scale display blinking)
"""
def isStable(ctrlByte):
    return True if ctrlByte & (1<<5) else False

"""
Somebody released scale
"""
def isReleased(ctrlByte):
    return True if ctrlByte & (1<<7) else False

"""
Data is velid and ready to use
"""
def isReadyToUse(ctrlByte, value):
    global PREVIOUS_VALUE
    if isReleased(ctrlByte):
        PREVIOUS_VALUE = None
        return False
    elif isStable(ctrlByte):
        if PREVIOUS_VALUE == value:
            return False
        else:
            PREVIOUS_VALUE = value
            return True 
    else:
        return False

"""
Parse hex data string: extract weight and unit
"""
def parseWeight(data):
    data2 = bytes.fromhex(data[0:])
    ctrlByte = data2[0]
    unitValue = int(ctrlByte & 0b00000011)
    measured = (int((data[4:6] + data[2:4]), 16) * 0.01)
    if unitValue == 2: unit = 'kg'; measured = measured/2
    elif unitValue == 3: unit = 'lb'
    else: unit = 'unknown'
    measured = round(measured, 2)
    isStable = True if ctrlByte & (1<<5) else False
    return measured, unit, ctrlByte, isStable

"""
Scan advertizement data from known device MAC-adress,
then do some actions
"""
async def scanByAddr(MISCALE_MAC):
    logger.info("Scan started for MAC %s", MISCALE_MAC)
    stop_event = asyncio.Event()
    # TODO: add something that calls stop_event.set()
    def callback(device, advertising_data):
        if device.address == MISCALE_MAC:
            try:
                data = advertising_data.service_data["0000181d-0000-1000-8000-00805f9b34fb"] # <class 'bytes'>
                dataHex = binascii.b2a_hex(data).decode('ascii')
                measured, unit, ctrlByte, isStable = parseWeight(dataHex)
                logger.info("Parsed %s %s %s %s", measured, unit, f"{ctrlByte:0{8}b}", isStable)
                if isReadyToUse(ctrlByte, measured):
                    sendMessage(msg = str(measured) + unit)
            except Exception as error:
                logger.error("Exception: %s", error)

    async with BleakScanner(callback) as scanner:
        # Important! Wait for an event to trigger stop, otherwise scanner will stop immediately
        await stop_event.wait()

asyncio.run(scanByAddr(KNOWN_ADDR))
