import pytest
import struct
import time
import logging
from datetime import datetime
from app.src.gen3plus.solarman_v5 import SolarmanV5
from app.src.config import Config
from app.src.infos import Infos, Register
from app.src.modbus import Modbus
from app.src.messages import State


pytest_plugins = ('pytest_asyncio',)

# initialize the proxy statistics
Infos.static_init()

timestamp = int(time.time())  # 1712861197
heartbeat = 60         

class Writer():
    def __init__(self):
        self.sent_pdu = b''

    def write(self, pdu: bytearray):
        self.sent_pdu = pdu


class Mqtt():
    def __init__(self):
        self.key = ''
        self.data = ''

    async def publish(self, key, data):
        self.key = key
        self.data = data


class MemoryStream(SolarmanV5):
    def __init__(self, msg, chunks = (0,), server_side: bool = True):
        super().__init__(server_side)
        if server_side:
            self.mb.timeout = 1   # overwrite for faster testing
        self.writer = Writer()
        self.mqtt = Mqtt()
        self.__msg = msg
        self.__msg_len = len(msg)
        self.__chunks = chunks
        self.__offs = 0
        self.__chunk_idx = 0
        self.msg_count = 0
        self.addr = 'Test: SrvSide'
        self.db.stat['proxy']['Invalid_Msg_Format'] = 0
        self.db.stat['proxy']['AT_Command'] = 0
        self.db.stat['proxy']['AT_Command_Blocked'] = 0
        self.test_exception_async_write = False
        self.entity_prfx = ''
        self.at_acl = {'mqtt': {'allow': ['AT+'], 'block': ['AT+WEBU']}, 'tsun': {'allow': ['AT+Z', 'AT+UPURL', 'AT+SUPDATE', 'AT+TIME'], 'block': ['AT+WEBU']}}
        self.key = ''
        self.data = ''

    def _timestamp(self):
        return timestamp
    
    def _heartbeat(self) -> int:
        return heartbeat

    def append_msg(self, msg):
        self.__msg += msg
        self.__msg_len += len(msg)    

    def publish_mqtt(self, key, data):
        self.key = key
        self.data = data

    def _read(self) -> int:
        copied_bytes = 0
        try:    
            if (self.__offs < self.__msg_len):
                len = self.__chunks[self.__chunk_idx]
                self.__chunk_idx += 1
                if len!=0:
                    self._recv_buffer += self.__msg[self.__offs:len]
                    copied_bytes = len - self.__offs
                    self.__offs = len
                else:
                    self._recv_buffer += self.__msg[self.__offs:]
                    copied_bytes = self.__msg_len - self.__offs
                    self.__offs = self.__msg_len
        except:
            pass     
        return copied_bytes
    
    async def async_write(self, headline=''):
        if self.test_exception_async_write:
            raise RuntimeError("Peer closed.")

    def createClientStream(self, msg, chunks = (0,)):
        c = MemoryStream(msg, chunks, False)
        self.remoteStream = c
        c. remoteStream = self
        return c

    def _SolarmanV5__flush_recv_msg(self) -> None:
        super()._SolarmanV5__flush_recv_msg()
        self.msg_count += 1
        return


def get_sn() -> bytes:
    return b'\x21\x43\x65\x7b'

def get_sn_int() -> int:
    return 2070233889

def get_inv_no() -> bytes:
    return b'T170000000000001'

def get_invalid_sn():
    return b'R170000000000002'

def total():
    ts = timestamp
    # convert int to little-endian bytes
    return struct.pack('<L',ts)

def hb():
    hb = heartbeat
    # convert int to little-endian bytes
    return struct.pack('<L',hb)

def correct_checksum(buf):
    checksum = sum(buf[1:]) & 0xff
    return checksum.to_bytes(length=1)

def incorrect_checksum(buf):
    checksum = (sum(buf[1:])+1) & 0xff
    return checksum.to_bytes(length=1)

@pytest.fixture
def DeviceIndMsg(): # 0x4110
    msg  = b'\xa5\xd4\x00\x10\x41\x00\x01' +get_sn()  +b'\x02\xba\xd2\x00\x00'
    msg += b'\x19\x00\x00\x00\x00\x00\x00\x00\x05\x3c\x78\x01\x64\x01\x4c\x53'
    msg += b'\x57\x35\x42\x4c\x45\x5f\x31\x37\x5f\x30\x32\x42\x30\x5f\x31\x2e'
    msg += b'\x30\x35\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x40\x2a\x8f\x4f\x51\x54\x31\x39\x32\x2e'
    msg += b'\x31\x36\x38\x2e\x38\x30\x2e\x34\x39\x00\x00\x00\x0f\x00\x01\xb0'
    msg += b'\x02\x0f\x00\xff\x56\x31\x2e\x31\x2e\x30\x30\x2e\x30\x42\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xfe\xfe\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x41\x6c\x6c\x69\x75\x73\x2d\x48\x6f'
    msg += b'\x6d\x65\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' 
    msg += correct_checksum(msg)
    msg += b'\x15'
    return msg

@pytest.fixture
def DeviceRspMsg():  # 0x1110
    msg  = b'\xa5\x0a\x00\x10\x11\x01\x01' +get_sn()  +b'\x02\x01'
    msg += total()  
    msg += hb()
    msg += correct_checksum(msg)
    msg += b'\x15'
    return msg

@pytest.fixture
def InvalidStartByte(): # 0x4110
    msg  = b'\xa4\xd4\x00\x10\x41\x00\x01' +get_sn()  +b'\x02\xba\xd2\x00\x00'
    msg += b'\x19\x00\x00\x00\x00\x00\x00\x00\x05\x3c\x78\x01\x64\x01\x4c\x53'
    msg += b'\x57\x35\x42\x4c\x45\x5f\x31\x37\x5f\x30\x32\x42\x30\x5f\x31\x2e'
    msg += b'\x30\x35\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x40\x2a\x8f\x4f\x51\x54\x31\x39\x32\x2e'
    msg += b'\x31\x36\x38\x2e\x38\x30\x2e\x34\x39\x00\x00\x00\x0f\x00\x01\xb0'
    msg += b'\x02\x0f\x00\xff\x56\x31\x2e\x31\x2e\x30\x30\x2e\x30\x42\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xfe\xfe\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x41\x6c\x6c\x69\x75\x73\x2d\x48\x6f'
    msg += b'\x6d\x65\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += correct_checksum(msg)
    msg += b'\x15'
    return msg

@pytest.fixture
def InvalidStopByte(): # 0x4110
    msg  = b'\xa5\xd4\x00\x10\x41\x00\x01' +get_sn()  +b'\x02\xba\xd2\x00\x00'
    msg += b'\x19\x00\x00\x00\x00\x00\x00\x00\x05\x3c\x78\x01\x64\x01\x4c\x53'
    msg += b'\x57\x35\x42\x4c\x45\x5f\x31\x37\x5f\x30\x32\x42\x30\x5f\x31\x2e'
    msg += b'\x30\x35\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x40\x2a\x8f\x4f\x51\x54\x31\x39\x32\x2e'
    msg += b'\x31\x36\x38\x2e\x38\x30\x2e\x34\x39\x00\x00\x00\x0f\x00\x01\xb0'
    msg += b'\x02\x0f\x00\xff\x56\x31\x2e\x31\x2e\x30\x30\x2e\x30\x42\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xfe\xfe\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x41\x6c\x6c\x69\x75\x73\x2d\x48\x6f'
    msg += b'\x6d\x65\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += correct_checksum(msg)
    msg += b'\x14'
    return msg

@pytest.fixture
def InvalidChecksum(): # 0x4110
    msg  = b'\xa5\xd4\x00\x10\x41\x00\x01' +get_sn()  +b'\x02\xba\xd2\x00\x00'
    msg += b'\x19\x00\x00\x00\x00\x00\x00\x00\x05\x3c\x78\x01\x64\x01\x4c\x53'
    msg += b'\x57\x35\x42\x4c\x45\x5f\x31\x37\x5f\x30\x32\x42\x30\x5f\x31\x2e'
    msg += b'\x30\x35\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x40\x2a\x8f\x4f\x51\x54\x31\x39\x32\x2e'
    msg += b'\x31\x36\x38\x2e\x38\x30\x2e\x34\x39\x00\x00\x00\x0f\x00\x01\xb0'
    msg += b'\x02\x0f\x00\xff\x56\x31\x2e\x31\x2e\x30\x30\x2e\x30\x42\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xfe\xfe\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x41\x6c\x6c\x69\x75\x73\x2d\x48\x6f'
    msg += b'\x6d\x65\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += incorrect_checksum(msg)
    msg += b'\x15'
    return msg

@pytest.fixture
def InverterIndMsg():  # 0x4210
    msg  = b'\xa5\x99\x01\x10\x42\x01\x02' +get_sn()  +b'\x01\xb0\x02\xbc\xc8'
    msg += b'\x24\x32\x6c\x1f\x00\x00\xa0\x47\xe4\x33\x01\x00\x03\x08\x00\x00'
    msg += b'\x59\x31\x37\x45\x37\x41\x30\x46\x30\x31\x30\x42\x30\x31\x33\x45'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x01\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x40\x10\x08\xc8\x00\x49\x13\x8d\x00\x36\x00\x00\x02\x58\x06\x7a'
    msg += b'\x01\x61\x00\xa8\x02\x54\x01\x5a\x00\x8a\x01\xe4\x01\x5a\x00\xbd'
    msg += b'\x02\x8f\x00\x11\x00\x01\x00\x00\x00\x0b\x00\x00\x27\x98\x00\x04'
    msg += b'\x00\x00\x0c\x04\x00\x03\x00\x00\x0a\xe7\x00\x05\x00\x00\x0c\x75'
    msg += b'\x00\x00\x00\x00\x06\x16\x02\x00\x00\x00\x55\xaa\x00\x01\x00\x00'
    msg += b'\x00\x00\x00\x00\xff\xff\x07\xd0\x00\x03\x04\x00\x04\x00\x04\x00'
    msg += b'\x04\x00\x00\x01\xff\xff\x00\x01\x00\x06\x00\x68\x00\x68\x05\x00'
    msg += b'\x09\xcd\x07\xb6\x13\x9c\x13\x24\x00\x01\x07\xae\x04\x0f\x00\x41'
    msg += b'\x00\x0f\x0a\x64\x0a\x64\x00\x06\x00\x06\x09\xf6\x12\x8c\x12\x8c'
    msg += b'\x00\x10\x00\x10\x14\x52\x14\x52\x00\x10\x00\x10\x01\x51\x00\x05'
    msg += b'\x04\x00\x00\x01\x13\x9c\x0f\xa0\x00\x4e\x00\x66\x03\xe8\x04\x00'
    msg += b'\x09\xce\x07\xa8\x13\x9c\x13\x26\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x04\x00\x04\x00\x00\x00\x00\x00\xff\xff\x00\x00'
    msg += b'\x00\x00\x00\x00'
    msg += correct_checksum(msg)
    msg += b'\x15'
    return msg

@pytest.fixture
def InverterIndMsg1600():  # 0x4210 rated Power 1600W 
    msg  = b'\xa5\x99\x01\x10\x42\xe6\x9e' +get_sn()  +b'\x01\xb0\x02\xbc\xc8'
    msg += b'\x24\x32\x6c\x1f\x00\x00\xa0\x47\xe4\x33\x01\x00\x03\x08\x00\x00'
    msg += b'\x59\x31\x37\x45\x37\x41\x30\x46\x30\x31\x30\x42\x30\x31\x33\x45'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x01\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg +=  b'\x40\x10\x08\xc8\x00\x49\x13\x8d\x00\x36\x00\x00\x06\x40\x06\x7a'
    msg += b'\x01\x61\x00\xa8\x02\x54\x01\x5a\x00\x8a\x01\xe4\x01\x5a\x00\xbd'
    msg += b'\x02\x8f\x00\x11\x00\x01\x00\x00\x00\x0b\x00\x00\x27\x98\x00\x04'
    msg += b'\x00\x00\x0c\x04\x00\x03\x00\x00\x0a\xe7\x00\x05\x00\x00\x0c\x75'
    msg += b'\x00\x00\x00\x00\x06\x16\x02\x00\x00\x00\x55\xaa\x00\x01\x00\x00'
    msg +=  b'\x00\x00\x00\x00\xff\xff\x06\x40\x00\x03\x04\x00\x04\x00\x04\x00'
    msg += b'\x04\x00\x00\x01\xff\xff\x00\x01\x00\x06\x00\x68\x00\x68\x05\x00'
    msg += b'\x09\xcd\x07\xb6\x13\x9c\x13\x24\x00\x01\x07\xae\x04\x0f\x00\x41'
    msg += b'\x00\x0f\x0a\x64\x0a\x64\x00\x06\x00\x06\x09\xf6\x12\x8c\x12\x8c'
    msg += b'\x00\x10\x00\x10\x14\x52\x14\x52\x00\x10\x00\x10\x01\x51\x00\x05'
    msg += b'\x04\x00\x00\x01\x13\x9c\x0f\xa0\x00\x4e\x00\x66\x03\xe8\x04\x00'
    msg += b'\x09\xce\x07\xa8\x13\x9c\x13\x26\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x04\x00\x04\x00\x00\x00\x00\x00\xff\xff\x00\x00'
    msg += b'\x00\x00\x00\x00'
    msg += correct_checksum(msg)
    msg += b'\x15'
    return msg

@pytest.fixture
def InverterIndMsg1800():  # 0x4210 rated Power 1800W 
    msg  = b'\xa5\x99\x01\x10\x42\xe6\x9e' +get_sn()  +b'\x01\xb0\x02\xbc\xc8'
    msg += b'\x24\x32\x6c\x1f\x00\x00\xa0\x47\xe4\x33\x01\x00\x03\x08\x00\x00'
    msg += b'\x59\x31\x37\x45\x37\x41\x30\x46\x30\x31\x30\x42\x30\x31\x33\x45'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x01\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg +=  b'\x40\x10\x08\xc8\x00\x49\x13\x8d\x00\x36\x00\x00\x07\x08\x06\x7a'
    msg += b'\x01\x61\x00\xa8\x02\x54\x01\x5a\x00\x8a\x01\xe4\x01\x5a\x00\xbd'
    msg += b'\x02\x8f\x00\x11\x00\x01\x00\x00\x00\x0b\x00\x00\x27\x98\x00\x04'
    msg += b'\x00\x00\x0c\x04\x00\x03\x00\x00\x0a\xe7\x00\x05\x00\x00\x0c\x75'
    msg += b'\x00\x00\x00\x00\x06\x16\x02\x00\x00\x00\x55\xaa\x00\x01\x00\x00'
    msg +=  b'\x00\x00\x00\x00\xff\xff\x07\x08\x00\x03\x04\x00\x04\x00\x04\x00'
    msg += b'\x04\x00\x00\x01\xff\xff\x00\x01\x00\x06\x00\x68\x00\x68\x05\x00'
    msg += b'\x09\xcd\x07\xb6\x13\x9c\x13\x24\x00\x01\x07\xae\x04\x0f\x00\x41'
    msg += b'\x00\x0f\x0a\x64\x0a\x64\x00\x06\x00\x06\x09\xf6\x12\x8c\x12\x8c'
    msg += b'\x00\x10\x00\x10\x14\x52\x14\x52\x00\x10\x00\x10\x01\x51\x00\x05'
    msg += b'\x04\x00\x00\x01\x13\x9c\x0f\xa0\x00\x4e\x00\x66\x03\xe8\x04\x00'
    msg += b'\x09\xce\x07\xa8\x13\x9c\x13\x26\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x04\x00\x04\x00\x00\x00\x00\x00\xff\xff\x00\x00'
    msg += b'\x00\x00\x00\x00'
    msg += correct_checksum(msg)
    msg += b'\x15'
    return msg

@pytest.fixture
def InverterIndMsg2000():  # 0x4210 rated Power 2000W 
    msg  = b'\xa5\x99\x01\x10\x42\xe6\x9e' +get_sn()  +b'\x01\xb0\x02\xbc\xc8'
    msg += b'\x24\x32\x6c\x1f\x00\x00\xa0\x47\xe4\x33\x01\x00\x03\x08\x00\x00'
    msg += b'\x59\x31\x37\x45\x37\x41\x30\x46\x30\x31\x30\x42\x30\x31\x33\x45'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x01\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg +=  b'\x40\x10\x08\xc8\x00\x49\x13\x8d\x00\x36\x00\x00\x07\xd0\x06\x7a'
    msg += b'\x01\x61\x00\xa8\x02\x54\x01\x5a\x00\x8a\x01\xe4\x01\x5a\x00\xbd'
    msg += b'\x02\x8f\x00\x11\x00\x01\x00\x00\x00\x0b\x00\x00\x27\x98\x00\x04'
    msg += b'\x00\x00\x0c\x04\x00\x03\x00\x00\x0a\xe7\x00\x05\x00\x00\x0c\x75'
    msg += b'\x00\x00\x00\x00\x06\x16\x02\x00\x00\x00\x55\xaa\x00\x01\x00\x00'
    msg += b'\x00\x00\x00\x00\xff\xff\x07\xd0\x00\x03\x04\x00\x04\x00\x04\x00'
    msg += b'\x04\x00\x00\x01\xff\xff\x00\x01\x00\x06\x00\x68\x00\x68\x05\x00'
    msg += b'\x09\xcd\x07\xb6\x13\x9c\x13\x24\x00\x01\x07\xae\x04\x0f\x00\x41'
    msg += b'\x00\x0f\x0a\x64\x0a\x64\x00\x06\x00\x06\x09\xf6\x12\x8c\x12\x8c'
    msg += b'\x00\x10\x00\x10\x14\x52\x14\x52\x00\x10\x00\x10\x01\x51\x00\x05'
    msg += b'\x04\x00\x00\x01\x13\x9c\x0f\xa0\x00\x4e\x00\x66\x03\xe8\x04\x00'
    msg += b'\x09\xce\x07\xa8\x13\x9c\x13\x26\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x04\x00\x04\x00\x00\x00\x00\x00\xff\xff\x00\x00'
    msg += b'\x00\x00\x00\x00'
    msg += correct_checksum(msg)
    msg += b'\x15'
    return msg

@pytest.fixture
def InverterIndMsg800():  # 0x4210 rated Power 800W 
    msg  = b'\xa5\x99\x01\x10\x42\xe6\x9e' +get_sn()  +b'\x01\xb0\x02\xbc\xc8'
    msg += b'\x24\x32\x6c\x1f\x00\x00\xa0\x47\xe4\x33\x01\x00\x03\x08\x00\x00'
    msg += b'\x59\x31\x37\x45\x37\x41\x30\x46\x30\x31\x30\x42\x30\x31\x33\x45'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x01\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg +=  b'\x40\x10\x08\xc8\x00\x49\x13\x8d\x00\x36\x00\x00\x03\x20\x06\x7a'
    msg += b'\x01\x61\x00\xa8\x02\x54\x01\x5a\x00\x8a\x01\xe4\x01\x5a\x00\xbd'
    msg += b'\x02\x8f\x00\x11\x00\x01\x00\x00\x00\x0b\x00\x00\x27\x98\x00\x04'
    msg += b'\x00\x00\x0c\x04\x00\x03\x00\x00\x0a\xe7\x00\x05\x00\x00\x0c\x75'
    msg += b'\x00\x00\x00\x00\x06\x16\x02\x00\x00\x00\x55\xaa\x00\x01\x00\x00'
    msg += b'\x00\x00\x00\x00\xff\xff\x03\x20\x00\x03\x04\x00\x04\x00\x04\x00'
    msg += b'\x04\x00\x00\x01\xff\xff\x00\x01\x00\x06\x00\x68\x00\x68\x05\x00'
    msg += b'\x09\xcd\x07\xb6\x13\x9c\x13\x24\x00\x01\x07\xae\x04\x0f\x00\x41'
    msg += b'\x00\x0f\x0a\x64\x0a\x64\x00\x06\x00\x06\x09\xf6\x12\x8c\x12\x8c'
    msg += b'\x00\x10\x00\x10\x14\x52\x14\x52\x00\x10\x00\x10\x01\x51\x00\x05'
    msg += b'\x04\x00\x00\x01\x13\x9c\x0f\xa0\x00\x4e\x00\x66\x03\xe8\x04\x00'
    msg += b'\x09\xce\x07\xa8\x13\x9c\x13\x26\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x04\x00\x04\x00\x00\x00\x00\x00\xff\xff\x00\x00'
    msg += b'\x00\x00\x00\x00'
    msg += correct_checksum(msg)
    msg += b'\x15'
    return msg

@pytest.fixture
def InverterIndMsg_81():  # 0x4210 fcode 0x81
    msg  = b'\xa5\x99\x01\x10\x42\x02\x03' +get_sn()  +b'\x81\xb0\x02\xbc\xc8'
    msg += b'\x24\x32\x6c\x1f\x00\x00\xa0\x07\x04\x03\x01\x00\x03\x08\x00\x00'
    msg += b'\x59\x31\x37\x45\x37\x41\x30\x46\x30\x31\x30\x42\x30\x31\x33\x45'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x01\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x40\x10\x08\xc8\x00\x49\x13\x8d\x00\x36\x00\x00\x02\x58\x06\x7a'
    msg += b'\x01\x61\x00\xa8\x02\x54\x01\x5a\x00\x8a\x01\xe4\x01\x5a\x00\xbd'
    msg += b'\x02\x8f\x00\x11\x00\x01\x00\x00\x00\x0b\x00\x00\x27\x98\x00\x04'
    msg += b'\x00\x00\x0c\x04\x00\x03\x00\x00\x0a\xe7\x00\x05\x00\x00\x0c\x75'
    msg += b'\x00\x00\x00\x00\x06\x16\x02\x00\x00\x00\x55\xaa\x00\x01\x00\x00'
    msg += b'\x00\x00\x00\x00\xff\xff\x07\xd0\x00\x03\x04\x00\x04\x00\x04\x00'
    msg += b'\x04\x00\x00\x01\xff\xff\x00\x01\x00\x06\x00\x68\x00\x68\x05\x00'
    msg += b'\x09\xcd\x07\xb6\x13\x9c\x13\x24\x00\x01\x07\xae\x04\x0f\x00\x41'
    msg += b'\x00\x0f\x0a\x64\x0a\x64\x00\x06\x00\x06\x09\xf6\x12\x8c\x12\x8c'
    msg += b'\x00\x10\x00\x10\x14\x52\x14\x52\x00\x10\x00\x10\x01\x51\x00\x05'
    msg += b'\x04\x00\x00\x01\x13\x9c\x0f\xa0\x00\x4e\x00\x66\x03\xe8\x04\x00'
    msg += b'\x09\xce\x07\xa8\x13\x9c\x13\x26\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x04\x00\x04\x00\x00\x00\x00\x00\xff\xff\x00\x00'
    msg += b'\x00\x00\x00\x00'
    msg += correct_checksum(msg)
    msg += b'\x15'
    return msg

@pytest.fixture
def InverterRspMsg():  # 0x1210
    msg  = b'\xa5\x0a\x00\x10\x12\x02\02' +get_sn()  +b'\x01\x01'
    msg += total()  
    msg += hb()
    msg += correct_checksum(msg)
    msg += b'\x15'
    return msg

@pytest.fixture
def InverterRspMsg_81():  # 0x1210 fcode 0x81
    msg  = b'\xa5\x0a\x00\x10\x12\x03\03' +get_sn()  +b'\x81\x01'
    msg += total()  
    msg += hb()
    msg += correct_checksum(msg)
    msg += b'\x15'
    return msg

@pytest.fixture
def UnknownMsg():  # 0x5110
    msg  = b'\xa5\x0a\x00\x10\x51\x10\x84' +get_sn()  +b'\x01\x01\x69\x6f\x09'
    msg += b'\x66\x78\x00\x00\x00'               
    msg += correct_checksum(msg)
    msg += b'\x15'
    return msg

@pytest.fixture
def SyncStartIndMsg():  # 0x4310
    msg  = b'\xa5\x2f\x00\x10\x43\x0c\x0d' +get_sn()  +b'\x81\x7a\x0b\x2e\x32'
    msg += b'\x39\x00\x00\x00\x00\x00\x00\x00\x0c\x00\x41\x6c\x6c\x69\x75\x73'
    msg += b'\x2d\x48\x6f\x6d\x65\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x61\x01'
    msg += correct_checksum(msg)
    msg += b'\x15'
    return msg

@pytest.fixture
def SyncStartRspMsg():  # 0x1310
    msg  = b'\xa5\x0a\x00\x10\x13\x0d\x0d' +get_sn()  +b'\x81\x01'
    msg += total()  
    msg += hb()
    msg += correct_checksum(msg)
    msg += b'\x15'
    return msg

@pytest.fixture
def SyncStartFwdMsg():  # 0x4310
    msg  = b'\xa5\x2f\x00\x10\x43\x0d\x0e' +get_sn()  +b'\x81\x7a\x0b\x2e\x32'
    msg += b'\x39\x00\x00\x00\x00\x00\x00\x00\x0c\x00\x41\x6c\x6c\x69\x75\x73'
    msg += b'\x2d\x48\x6f\x6d\x65\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x61\x01'
    msg += correct_checksum(msg)
    msg += b'\x15'
    return msg


@pytest.fixture
def AtCommandIndMsg():  # 0x4510
    msg  = b'\xa5\x27\x00\x10\x45\x03\x02' +get_sn() +b'\x01\x02\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'           
    msg += b'AT+TIME=214028,1,60,120\r'
    msg += correct_checksum(msg)
    msg += b'\x15'
    return msg

@pytest.fixture
def AtCommandIndMsgBlock():  # 0x4510
    msg  = b'\xa5\x17\x00\x10\x45\x03\x02' +get_sn() +b'\x01\x02\x00'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'           
    msg += b'AT+WEBU\r'
    msg += correct_checksum(msg)
    msg += b'\x15'
    return msg

@pytest.fixture
def AtCommandRspMsg():  # 0x1510
    msg  = b'\xa5\x11\x00\x10\x15\x03\x03' +get_sn()  +b'\x01\x01'
    msg += total()  
    msg += hb()
    msg += b'\x00\x00\x00\x00+ok'
    msg += correct_checksum(msg)
    msg += b'\x15'
    return msg

@pytest.fixture
def HeartbeatIndMsg():  # 0x4710
    msg  = b'\xa5\x01\x00\x10\x47\x10\x84' +get_sn()
    msg += b'\x00'               
    msg += correct_checksum(msg)
    msg += b'\x15'
    return msg

@pytest.fixture
def HeartbeatRspMsg():  # 0x1710
    msg  = b'\xa5\x0a\x00\x10\x17\x11\x84' +get_sn()  +b'\x00\x01'
    msg += total()  
    msg += hb()
    msg += correct_checksum(msg)
    msg += b'\x15'
    return msg

@pytest.fixture
def SyncEndIndMsg():  # 0x4810
    msg  = b'\xa5\x3c\x00\x10\x48\x06\x07' +get_sn() +b'\x01\xa5\x3c\x2e\x32'
    msg += b'\x2c\x00\x00\x00\xc1\x01\xec\x33\x01\x05\x2c\xff\xff\xff\xff\xff'
    msg += b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
    msg += b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
    msg += b'\xff\xff\xff\xff\xff\xff\xff'
    msg += correct_checksum(msg)
    msg += b'\x15'
    return msg

@pytest.fixture
def SyncEndRspMsg():  # 0x1810
    msg  = b'\xa5\x0a\x00\x10\x18\x07\x07' +get_sn()  +b'\x01\x01'
    msg += total()  
    msg += hb()
    msg += correct_checksum(msg)
    msg += b'\x15'
    return msg

@pytest.fixture
def MsgModbusCmd():
    msg  = b'\xa5\x17\x00\x10\x45\x03\x02' +get_sn()  +b'\x02\xb0\x02'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x06\x20\x08'
    msg += b'\x00\x00\x03\xc8'
    msg += correct_checksum(msg)
    msg += b'\x15'
    return msg

@pytest.fixture
def MsgModbusCmdFwd():
    msg  = b'\xa5\x17\x00\x10\x45\x01\x00' +get_sn()  +b'\x02\xb0\x02'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x06\x20\x08'
    msg += b'\x00\x00\x03\xc8'
    msg += correct_checksum(msg)
    msg += b'\x15'
    return msg

@pytest.fixture
def MsgModbusCmdCrcErr():
    msg  = b'\xa5\x17\x00\x10\x45\x03\x02' +get_sn()  +b'\x02\xb0\x02'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x06\x20\x08'
    msg += b'\x00\x00\x04\xc8'
    msg += correct_checksum(msg)
    msg += b'\x15'
    return msg

@pytest.fixture
def MsgModbusRsp():  # 0x1510
    msg  = b'\xa5\x3b\x00\x10\x15\x03\x03' +get_sn()  +b'\x02\x01'
    msg += total()  
    msg += hb()
    msg += b'\x0a\xe2\xfa\x33\x01\x03\x28\x40\x10\x08\xd8'
    msg += b'\x00\x00\x13\x87\x00\x31\x00\x68\x02\x58\x00\x00\x01\x53\x00\x02'
    msg += b'\x00\x00\x01\x52\x00\x02\x00\x00\x01\x53\x00\x03\x00\x00\x00\x04'
    msg += b'\x00\x01\x00\x00\x6c\x68'
    msg += correct_checksum(msg)
    msg += b'\x15'
    return msg

@pytest.fixture
def MsgModbusInvalid():  # 0x1510
    msg  = b'\xa5\x3b\x00\x10\x15\x03\x03' +get_sn()  +b'\x02\x00'
    msg += total()  
    msg += hb()
    msg += b'\x0a\xe2\xfa\x33\x01\x03\x28\x40\x10\x08\xd8'
    msg += b'\x00\x00\x13\x87\x00\x31\x00\x68\x02\x58\x00\x00\x01\x53\x00\x02'
    msg += b'\x00\x00\x01\x52\x00\x02\x00\x00\x01\x53\x00\x03\x00\x00\x00\x04'
    msg += b'\x00\x01\x00\x00\x6c\x68'
    msg += correct_checksum(msg)
    msg += b'\x15'
    return msg

@pytest.fixture
def MsgUnknownCmd():
    msg  = b'\xa5\x17\x00\x10\x45\x03\x02' +get_sn()  +b'\x03\xb0\x02'
    msg += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x06\x20\x08'
    msg += b'\x00\x00\x03\xc8'
    msg += correct_checksum(msg)
    msg += b'\x15'
    return msg

@pytest.fixture
def MsgUnknownCmdRsp():  # 0x1510
    msg  = b'\xa5\x3b\x00\x10\x15\x03\x03' +get_sn()  +b'\x03\x01'
    msg += total()  
    msg += hb()
    msg += b'\x0a\xe2\xfa\x33\x01\x03\x28\x40\x10\x08\xd8'
    msg += b'\x00\x00\x13\x87\x00\x31\x00\x68\x02\x58\x00\x00\x01\x53\x00\x02'
    msg += b'\x00\x00\x01\x52\x00\x02\x00\x00\x01\x53\x00\x03\x00\x00\x00\x04'
    msg += b'\x00\x01\x00\x00\x6c\x68'
    msg += correct_checksum(msg)
    msg += b'\x15'
    return msg

@pytest.fixture
def ConfigTsunAllowAll():
    Config.config = {'solarman':{'enabled': True}, 'inverters':{'allow_all':True}}

@pytest.fixture
def ConfigNoTsunInv1():
    Config.config = {'solarman':{'enabled': False},'inverters':{'Y170000000000001':{'monitor_sn': 2070233889,'node_id':'inv1','suggested_area':'roof'}}}

@pytest.fixture
def ConfigTsunInv1():
    Config.config = {'solarman':{'enabled': True},'inverters':{'Y170000000000001':{'monitor_sn': 2070233889,'node_id':'inv1','suggested_area':'roof'}}}

def test_read_message(DeviceIndMsg):
    m = MemoryStream(DeviceIndMsg, (0,))
    m.read()         # read complete msg, and dispatch msg
    assert not m.header_valid  # must be invalid, since msg was handled and buffer flushed
    assert m.msg_count == 1
    assert m.header_len==11
    assert m.snr == 2070233889
    assert m.unique_id == None
    assert m.control == 0x4110
    assert str(m.seq) == '01:00'
    assert m.data_len == 0xd4
    assert m._recv_buffer==b''
    assert m._send_buffer==b''
    assert m._forward_buffer==b''
    assert m.db.stat['proxy']['Invalid_Msg_Format'] == 0
    m.close()

def test_invalid_start_byte(InvalidStartByte, DeviceIndMsg):
    # received a message with wrong start byte plus an valid message
    # the complete receive buffer must be cleared to 
    # find the next valid message
    m = MemoryStream(InvalidStartByte, (0,))
    m.append_msg(DeviceIndMsg)
    m.read()         # read complete msg, and dispatch msg
    assert not m.header_valid  # must be invalid, since start byte is wrong
    assert m.msg_count == 0
    assert m.header_len==11
    assert m.snr == 2070233889
    assert m.unique_id == 0
    assert m.control == 0x4110
    assert str(m.seq) == '01:00'
    assert m.data_len == 0xd4
    assert m._recv_buffer==b''
    assert m._send_buffer==b''
    assert m._forward_buffer==b''
    assert m.db.stat['proxy']['Invalid_Msg_Format'] == 1
    m.close()

def test_invalid_stop_byte(InvalidStopByte):
    # received a message with wrong stop byte
    # the complete receive buffer must be cleared to 
    # find the next valid message
    m = MemoryStream(InvalidStopByte, (0,))
    m.read()         # read complete msg, and dispatch msg
    assert not m.header_valid  # must be invalid, since start byte is wrong
    assert m.msg_count == 1     # msg flush was called
    assert m.header_len==11
    assert m.snr == 2070233889
    assert m.unique_id == 0
    assert m.control == 0x4110
    assert str(m.seq) == '01:00'
    assert m.data_len == 0xd4
    assert m._recv_buffer==b''
    assert m._send_buffer==b''
    assert m._forward_buffer==b''
    assert m.db.stat['proxy']['Invalid_Msg_Format'] == 1
    m.close()

def test_invalid_stop_byte2(InvalidStopByte, DeviceIndMsg):
    # received a message with wrong stop byte plus an valid message
    # only the first message must be discarded
    m = MemoryStream(InvalidStopByte, (0,))
    m.append_msg(DeviceIndMsg)
    m.read()         # read complete msg, and dispatch msg
    assert not m.header_valid  # must be invalid, since start byte is wrong
    assert m.msg_count == 1     # msg flush was called
    assert m.header_len==11
    assert m.snr == 2070233889
    assert m.unique_id == 0
    assert m.control == 0x4110
    assert str(m.seq) == '01:00'
    assert m.data_len == 0xd4
    assert m._recv_buffer==DeviceIndMsg
    assert m._send_buffer==b''
    assert m._forward_buffer==b''
    assert m.db.stat['proxy']['Invalid_Msg_Format'] == 1

    m.read()         # read complete msg, and dispatch msg
    assert not m.header_valid  # must be invalid, since msg was handled and buffer flushed
    assert m.msg_count == 2
    assert m.header_len==11
    assert m.snr == 2070233889
    assert m.unique_id == None
    assert m.control == 0x4110
    assert str(m.seq) == '01:00'
    assert m.data_len == 0xd4
    assert m._recv_buffer==b''
    assert m._send_buffer==b''
    assert m._forward_buffer==b''
    assert m.db.stat['proxy']['Invalid_Msg_Format'] == 1
    m.close()

def test_invalid_stop_start_byte(InvalidStopByte, InvalidStartByte):
    # received a message with wrong stop byte plus an invalid message
    # with fron start byte
    # the complete receive buffer must be cleared to 
    # find the next valid message
    m = MemoryStream(InvalidStopByte, (0,))
    m.append_msg(InvalidStartByte)
    m.read()         # read complete msg, and dispatch msg
    assert not m.header_valid  # must be invalid, since start byte is wrong
    assert m.msg_count == 1     # msg flush was called
    assert m.header_len==11
    assert m.snr == 2070233889
    assert m.unique_id == 0
    assert m.control == 0x4110
    assert str(m.seq) == '01:00'
    assert m.data_len == 0xd4
    assert m._recv_buffer==b''
    assert m._send_buffer==b''
    assert m._forward_buffer==b''
    assert m.db.stat['proxy']['Invalid_Msg_Format'] == 1
    m.close()

def test_invalid_checksum(InvalidChecksum, DeviceIndMsg):
    # received a message with wrong checksum plus an valid message
    # only the first message must be discarded
    m = MemoryStream(InvalidChecksum, (0,))
    m.append_msg(DeviceIndMsg)
    m.read()         # read complete msg, and dispatch msg
    assert not m.header_valid  # must be invalid, since start byte is wrong
    assert m.msg_count == 1     # msg flush was called
    assert m.header_len==11
    assert m.snr == 2070233889
    assert m.unique_id == 0
    assert m.control == 0x4110
    assert str(m.seq) == '01:00'
    assert m.data_len == 0xd4
    assert m._recv_buffer==DeviceIndMsg
    assert m._send_buffer==b''
    assert m._forward_buffer==b''
    assert m.db.stat['proxy']['Invalid_Msg_Format'] == 1

    m.read()         # read complete msg, and dispatch msg
    assert not m.header_valid  # must be invalid, since msg was handled and buffer flushed
    assert m.msg_count == 2
    assert m.header_len==11
    assert m.snr == 2070233889
    assert m.unique_id == None
    assert m.control == 0x4110
    assert str(m.seq) == '01:00'
    assert m.data_len == 0xd4
    assert m._recv_buffer==b''
    assert m._send_buffer==b''
    assert m._forward_buffer==b''
    assert m.db.stat['proxy']['Invalid_Msg_Format'] == 1
    m.close()

def test_read_message_twice(ConfigNoTsunInv1, DeviceIndMsg, DeviceRspMsg):
    ConfigNoTsunInv1
    m = MemoryStream(DeviceIndMsg, (0,))
    m.append_msg(DeviceIndMsg)
    m.read()         # read complete msg, and dispatch msg
    assert not m.header_valid  # must be invalid, since msg was handled and buffer flushed
    assert m.msg_count == 1
    assert m.header_len==11
    assert m.snr == 2070233889
    assert m.unique_id == '2070233889'
    assert m.control == 0x4110
    assert str(m.seq) == '01:01'
    assert m.data_len == 0xd4
    assert m._send_buffer==DeviceRspMsg
    assert m._forward_buffer==b''
    assert m.db.stat['proxy']['Invalid_Msg_Format'] == 0
    
    m._send_buffer = bytearray(0) # clear send buffer for next test    
    m.read()         # read complete msg, and dispatch msg
    assert not m.header_valid  # must be invalid, since msg was handled and buffer flushed
    assert m.msg_count == 2
    assert m.header_len==11
    assert m.snr == 2070233889
    assert m.unique_id == '2070233889'
    assert m.control == 0x4110
    assert str(m.seq) == '01:01'
    assert m.data_len == 0xd4
    assert m._send_buffer==DeviceRspMsg
    assert m._forward_buffer==b''
    assert m.db.stat['proxy']['Invalid_Msg_Format'] == 0
    m.close()

def test_read_message_in_chunks(DeviceIndMsg):
    m = MemoryStream(DeviceIndMsg, (4,11,0))
    m.read()        # read 4 bytes, header incomplere
    assert not m.header_valid  # must be invalid, since header not complete
    assert m.msg_count == 0
    m.read()        # read missing bytes for complete header
    assert m.header_valid      # must be valid, since header is complete but not the msg
    assert m.msg_count == 0
    assert m.header_len==11
    assert m.snr == 2070233889
    assert m.unique_id == 0 # should be None ?
    assert m.control == 0x4110
    assert str(m.seq) == '01:00'
    assert m.data_len == 0xd4
    assert m.db.stat['proxy']['Invalid_Msg_Format'] == 0
    m.read()    # read rest of message
    assert not m.header_valid  # must be invalid, since msg was handled and buffer flushed
    assert m.msg_count == 1
    assert m.db.stat['proxy']['Invalid_Msg_Format'] == 0
    m.close()

def test_read_message_in_chunks2(ConfigTsunInv1, DeviceIndMsg):
    ConfigTsunInv1
    m = MemoryStream(DeviceIndMsg, (4,10,0))
    m.read()        # read 4 bytes, header incomplere
    assert not m.header_valid
    assert m.msg_count == 0
    m.read()        # read 6 more bytes, header incomplere
    assert not m.header_valid
    assert m.msg_count == 0
    m.read()        # read rest of message
    assert not m.header_valid  # must be invalid, since msg was handled and buffer flushed
    assert m.header_len==11
    assert m.snr == 2070233889
    assert m.unique_id == '2070233889'
    assert m.control == 0x4110
    assert str(m.seq) == '01:01'
    assert m.data_len == 0xd4
    assert m.msg_count == 1
    assert m.db.stat['proxy']['Invalid_Msg_Format'] == 0
    m.read()        # read rest of message
    assert m.msg_count == 1
    assert not m.header_valid  # must be invalid, since msg was handled and buffer flushed
    assert m.db.stat['proxy']['Invalid_Msg_Format'] == 0
    m.close()

def test_read_two_messages(ConfigTsunAllowAll, DeviceIndMsg, DeviceRspMsg, InverterIndMsg, InverterRspMsg):
    ConfigTsunAllowAll
    m = MemoryStream(DeviceIndMsg, (0,))
    m.append_msg(InverterIndMsg)
    m.read()         # read complete msg, and dispatch msg
    assert not m.header_valid  # must be invalid, since msg was handled and buffer flushed
    assert m.msg_count == 1
    assert m.header_len==11
    assert m.snr == 2070233889
    assert m.unique_id == '2070233889'
    assert m.control == 0x4110
    assert str(m.seq) == '01:01'
    assert m.data_len == 0xd4
    assert m.msg_count == 1
    assert m.db.stat['proxy']['Invalid_Msg_Format'] == 0
    assert m._forward_buffer==DeviceIndMsg
    assert m._send_buffer==DeviceRspMsg
 
    m._send_buffer = bytearray(0) # clear send buffer for next test  
    m._init_new_client_conn()
    assert m._send_buffer==b''
    assert m._recv_buffer==InverterIndMsg
    
    m._send_buffer = bytearray(0) # clear send buffer for next test
    m._forward_buffer = bytearray(0) # clear forward buffer for next test
    m.read()         # read complete msg, and dispatch msg
    assert m.db.stat['proxy']['Invalid_Msg_Format'] == 0
    assert not m.header_valid  # must be invalid, since msg was handled and buffer flushed
    assert m.msg_count == 2
    assert m.header_len==11
    assert m.snr == 2070233889
    assert m.unique_id == '2070233889'
    assert m.control == 0x4210
    assert str(m.seq) == '02:02'
    assert m.data_len == 0x199
    assert m.db.stat['proxy']['Invalid_Msg_Format'] == 0
    assert m._forward_buffer==InverterIndMsg
    assert m._send_buffer==InverterRspMsg

    m._send_buffer = bytearray(0) # clear send buffer for next test    
    m._init_new_client_conn()
    assert m._send_buffer==b''
    m.close()

def test_read_two_messages2(ConfigTsunAllowAll, InverterIndMsg, InverterIndMsg_81, InverterRspMsg, InverterRspMsg_81):
    ConfigTsunAllowAll
    m = MemoryStream(InverterIndMsg, (0,))
    m.append_msg(InverterIndMsg_81)
    m.read()         # read complete msg, and dispatch msg
    assert not m.header_valid  # must be invalid, since msg was handled and buffer flushed
    assert m.msg_count == 1
    assert m.header_len==11
    assert m.snr == 2070233889
    assert m.unique_id == '2070233889'
    assert m.control == 0x4210
    assert m.time_ofs == 0x33e447a0
    assert str(m.seq) == '02:02'
    assert m.data_len == 0x199
    assert m.msg_count == 1
    assert m.db.stat['proxy']['Invalid_Msg_Format'] == 0
    assert m._forward_buffer==InverterIndMsg
    assert m._send_buffer==InverterRspMsg
 
    m._send_buffer = bytearray(0) # clear send buffer for next test  
    m._init_new_client_conn()
    assert m._send_buffer==b''
    assert m._recv_buffer==InverterIndMsg_81
    
    m._send_buffer = bytearray(0) # clear send buffer for next test
    m._forward_buffer = bytearray(0) # clear forward buffer for next test
    m.read()         # read complete msg, and dispatch msg
    assert m.db.stat['proxy']['Invalid_Msg_Format'] == 0
    assert not m.header_valid  # must be invalid, since msg was handled and buffer flushed
    assert m.msg_count == 2
    assert m.header_len==11
    assert m.snr == 2070233889
    assert m.unique_id == '2070233889'
    assert m.control == 0x4210
    assert m.time_ofs == 0x33e447a0
    assert str(m.seq) == '03:03'
    assert m.data_len == 0x199
    assert m.db.stat['proxy']['Invalid_Msg_Format'] == 0
    assert m._forward_buffer==InverterIndMsg_81
    assert m._send_buffer==InverterRspMsg_81

    m._send_buffer = bytearray(0) # clear send buffer for next test    
    m._init_new_client_conn()
    assert m._send_buffer==b''
    m.close()

def test_unkown_message(ConfigTsunInv1, UnknownMsg):
    ConfigTsunInv1
    m = MemoryStream(UnknownMsg, (0,))
    m.read()         # read complete msg, and dispatch msg
    assert not m.header_valid  # must be invalid, since msg was handled and buffer flushed
    assert m.msg_count == 1
    assert m.header_len==11
    assert m.snr == 2070233889
    assert m.unique_id == '2070233889'
    assert m.control == 0x5110
    assert str(m.seq) == '84:10'
    assert m.data_len == 0x0a
    assert m._recv_buffer==b''
    assert m._send_buffer==b''
    assert m._forward_buffer==UnknownMsg
    assert m.db.stat['proxy']['Invalid_Msg_Format'] == 0
    m.close()

def test_device_rsp(ConfigTsunInv1, DeviceRspMsg):
    ConfigTsunInv1
    m = MemoryStream(DeviceRspMsg, (0,), False)
    m.read()         # read complete msg, and dispatch msg
    assert not m.header_valid  # must be invalid, since msg was handled and buffer flushed
    assert m.msg_count == 1
    assert m.header_len==11
    assert m.snr == 2070233889
    assert m.unique_id == '2070233889'
    assert m.control == 0x1110
    assert str(m.seq) == '01:01'
    assert m.data_len == 0x0a
    assert m._recv_buffer==b''
    assert m._send_buffer==b''
    assert m._forward_buffer==b''
    assert m.db.stat['proxy']['Invalid_Msg_Format'] == 0
    m.close()

def test_inverter_rsp(ConfigTsunInv1, InverterRspMsg):
    ConfigTsunInv1
    m = MemoryStream(InverterRspMsg, (0,), False)
    m.read()         # read complete msg, and dispatch msg
    assert not m.header_valid  # must be invalid, since msg was handled and buffer flushed
    assert m.msg_count == 1
    assert m.header_len==11
    assert m.snr == 2070233889
    assert m.unique_id == '2070233889'
    assert m.control == 0x1210
    assert str(m.seq) == '02:02'
    assert m.data_len == 0x0a
    assert m._recv_buffer==b''
    assert m._send_buffer==b''
    assert m._forward_buffer==b''
    assert m.db.stat['proxy']['Invalid_Msg_Format'] == 0
    m.close()

def test_heartbeat_ind(ConfigTsunInv1, HeartbeatIndMsg, HeartbeatRspMsg):
    ConfigTsunInv1
    m = MemoryStream(HeartbeatIndMsg, (0,))
    m.read()         # read complete msg, and dispatch msg
    assert not m.header_valid  # must be invalid, since msg was handled and buffer flushed
    assert m.msg_count == 1
    assert m.header_len==11
    assert m.snr == 2070233889
    # assert m.unique_id == '2070233889'
    assert m.control == 0x4710
    assert str(m.seq) == '84:11'  # value after sending response
    assert m.data_len == 0x01
    assert m._recv_buffer==b''
    assert m._send_buffer==HeartbeatRspMsg
    assert m._forward_buffer==HeartbeatIndMsg
    assert m.db.stat['proxy']['Invalid_Msg_Format'] == 0
    m.close()

def test_heartbeat_rsp(ConfigTsunInv1, HeartbeatRspMsg):
    ConfigTsunInv1
    m = MemoryStream(HeartbeatRspMsg, (0,), False)
    m.read()         # read complete msg, and dispatch msg
    assert not m.header_valid  # must be invalid, since msg was handled and buffer flushed
    assert m.msg_count == 1
    assert m.header_len==11
    assert m.snr == 2070233889
    assert m.unique_id == '2070233889'
    assert m.control == 0x1710
    assert str(m.seq) == '11:84'  # value after sending response
    assert m.data_len == 0x0a
    assert m._recv_buffer==b''
    assert m._send_buffer==b''
    assert m._forward_buffer==b''
    assert m.db.stat['proxy']['Invalid_Msg_Format'] == 0
    m.close()

def test_sync_start_ind(ConfigTsunInv1, SyncStartIndMsg, SyncStartRspMsg, SyncStartFwdMsg):
    ConfigTsunInv1
    m = MemoryStream(SyncStartIndMsg, (0,))
    m.read()         # read complete msg, and dispatch msg
    assert not m.header_valid  # must be invalid, since msg was handled and buffer flushed
    assert m.msg_count == 1
    assert m.header_len==11
    assert m.snr == 2070233889
    # assert m.unique_id == '2070233889'
    assert m.control == 0x4310
    assert str(m.seq) == '0d:0d'  # value after sending response
    assert m.data_len == 47
    assert m._recv_buffer==b''
    assert m._send_buffer==SyncStartRspMsg
    assert m._forward_buffer==SyncStartIndMsg
    assert m.db.stat['proxy']['Invalid_Msg_Format'] == 0

    m.seq.server_side = False  # simulate forawding to TSUN cloud
    m._update_header(m._forward_buffer)
    assert str(m.seq) == '0d:0e'  # value after forwarding indication
    assert m._forward_buffer==SyncStartFwdMsg

    m.close()

def test_sync_start_rsp(ConfigTsunInv1, SyncStartRspMsg):
    ConfigTsunInv1
    m = MemoryStream(SyncStartRspMsg, (0,), False)
    m.read()         # read complete msg, and dispatch msg
    assert not m.header_valid  # must be invalid, since msg was handled and buffer flushed
    assert m.msg_count == 1
    assert m.header_len==11
    assert m.snr == 2070233889
    assert m.unique_id == '2070233889'
    assert m.control == 0x1310
    assert str(m.seq) == '0d:0d'  # value after sending response
    assert m.data_len == 0x0a
    assert m._recv_buffer==b''
    assert m._send_buffer==b''
    assert m._forward_buffer==b''
    assert m.db.stat['proxy']['Invalid_Msg_Format'] == 0
    m.close()

def test_sync_end_ind(ConfigTsunInv1, SyncEndIndMsg, SyncEndRspMsg):
    ConfigTsunInv1
    m = MemoryStream(SyncEndIndMsg, (0,))
    m.read()         # read complete msg, and dispatch msg
    assert not m.header_valid  # must be invalid, since msg was handled and buffer flushed
    assert m.msg_count == 1
    assert m.header_len==11
    assert m.snr == 2070233889
    # assert m.unique_id == '2070233889'
    assert m.control == 0x4810
    assert str(m.seq) == '07:07'  # value after sending response
    assert m.data_len == 60
    assert m._recv_buffer==b''
    assert m._send_buffer==SyncEndRspMsg
    assert m._forward_buffer==SyncEndIndMsg
    assert m.db.stat['proxy']['Invalid_Msg_Format'] == 0
    m.close()

def test_sync_end_rsp(ConfigTsunInv1, SyncEndRspMsg):
    ConfigTsunInv1
    m = MemoryStream(SyncEndRspMsg, (0,), False)
    m.read()         # read complete msg, and dispatch msg
    assert not m.header_valid  # must be invalid, since msg was handled and buffer flushed
    assert m.msg_count == 1
    assert m.header_len==11
    assert m.snr == 2070233889
    assert m.unique_id == '2070233889'
    assert m.control == 0x1810
    assert str(m.seq) == '07:07'  # value after sending response
    assert m.data_len == 0x0a
    assert m._recv_buffer==b''
    assert m._send_buffer==b''
    assert m._forward_buffer==b''
    assert m.db.stat['proxy']['Invalid_Msg_Format'] == 0
    m.close()

def test_build_modell_600(ConfigTsunAllowAll, InverterIndMsg):
    ConfigTsunAllowAll
    m = MemoryStream(InverterIndMsg, (0,))
    assert 0 == m.db.get_db_value(Register.MAX_DESIGNED_POWER, 0)
    assert None == m.db.get_db_value(Register.RATED_POWER, None)
    assert None == m.db.get_db_value(Register.INVERTER_TEMP, None)
    m.read()         # read complete msg, and dispatch msg
    assert 2000 == m.db.get_db_value(Register.MAX_DESIGNED_POWER, 0)
    assert 600 == m.db.get_db_value(Register.RATED_POWER, 0)
    assert 'TSOL-MS2000(600)' == m.db.get_db_value(Register.EQUIPMENT_MODEL, 0)

    m._send_buffer = bytearray(0) # clear send buffer for next test    
    m._init_new_client_conn()
    assert m._send_buffer==b''
    m.close()

def test_build_modell_1600(ConfigTsunAllowAll, InverterIndMsg1600):
    ConfigTsunAllowAll
    m = MemoryStream(InverterIndMsg1600, (0,))
    assert 0 == m.db.get_db_value(Register.MAX_DESIGNED_POWER, 0)
    assert None == m.db.get_db_value(Register.RATED_POWER, None)
    assert None == m.db.get_db_value(Register.INVERTER_TEMP, None)
    m.read()         # read complete msg, and dispatch msg
    assert 1600 == m.db.get_db_value(Register.MAX_DESIGNED_POWER, 0)
    assert 1600 == m.db.get_db_value(Register.RATED_POWER, 0)
    assert 'TSOL-MS1600' == m.db.get_db_value(Register.EQUIPMENT_MODEL, 0)
    m.close()

def test_build_modell_1800(ConfigTsunAllowAll, InverterIndMsg1800):
    ConfigTsunAllowAll
    m = MemoryStream(InverterIndMsg1800, (0,))
    assert 0 == m.db.get_db_value(Register.MAX_DESIGNED_POWER, 0)
    assert None == m.db.get_db_value(Register.RATED_POWER, None)
    assert None == m.db.get_db_value(Register.INVERTER_TEMP, None)
    m.read()         # read complete msg, and dispatch msg
    assert 1800 == m.db.get_db_value(Register.MAX_DESIGNED_POWER, 0)
    assert 1800 == m.db.get_db_value(Register.RATED_POWER, 0)
    assert 'TSOL-MS1800' == m.db.get_db_value(Register.EQUIPMENT_MODEL, 0)
    m.close()

def test_build_modell_2000(ConfigTsunAllowAll, InverterIndMsg2000):
    ConfigTsunAllowAll
    m = MemoryStream(InverterIndMsg2000, (0,))
    assert 0 == m.db.get_db_value(Register.MAX_DESIGNED_POWER, 0)
    assert None == m.db.get_db_value(Register.RATED_POWER, None)
    assert None == m.db.get_db_value(Register.INVERTER_TEMP, None)
    m.read()         # read complete msg, and dispatch msg
    assert 2000 == m.db.get_db_value(Register.MAX_DESIGNED_POWER, 0)
    assert 2000 == m.db.get_db_value(Register.RATED_POWER, 0)
    assert 'TSOL-MS2000' == m.db.get_db_value(Register.EQUIPMENT_MODEL, 0)
    m.close()

def test_build_modell_800(ConfigTsunAllowAll, InverterIndMsg800):
    ConfigTsunAllowAll
    m = MemoryStream(InverterIndMsg800, (0,))
    assert 0 == m.db.get_db_value(Register.MAX_DESIGNED_POWER, 0)
    assert None == m.db.get_db_value(Register.RATED_POWER, None)
    assert None == m.db.get_db_value(Register.INVERTER_TEMP, None)
    m.read()         # read complete msg, and dispatch msg
    assert 800 == m.db.get_db_value(Register.MAX_DESIGNED_POWER, 0)
    assert 800 == m.db.get_db_value(Register.RATED_POWER, 0)
    assert 'TSOL-MSxx00' == m.db.get_db_value(Register.EQUIPMENT_MODEL, 0)
    m.close()

def test_build_logger_modell(ConfigTsunAllowAll, DeviceIndMsg):
    ConfigTsunAllowAll
    m = MemoryStream(DeviceIndMsg, (0,))
    assert 0 == m.db.get_db_value(Register.COLLECTOR_FW_VERSION, 0)
    assert 'IGEN TECH' == m.db.get_db_value(Register.CHIP_TYPE, None)
    assert None == m.db.get_db_value(Register.CHIP_MODEL, None)
    m.read()         # read complete msg, and dispatch msg
    assert 'LSW5BLE_17_02B0_1.05' == m.db.get_db_value(Register.CHIP_MODEL, 0)
    assert 'V1.1.00.0B' == m.db.get_db_value(Register.COLLECTOR_FW_VERSION, 0).rstrip('\00')
    m.close()

def test_msg_iterator():
    m1 = SolarmanV5(server_side=True)
    m2 = SolarmanV5(server_side=True)
    m3 = SolarmanV5(server_side=True)
    m3.close()
    del m3
    test1 = 0
    test2 = 0
    for key in SolarmanV5:
        if key == m1:
            test1+=1
        elif key == m2:
            test2+=1
        elif type(key) != SolarmanV5:
            continue
        else:
            assert False
    assert test1 == 1
    assert test2 == 1

def test_proxy_counter():
    m = SolarmanV5(server_side=True)
    assert m.new_data == {}
    m.db.stat['proxy']['Unknown_Msg'] = 0
    Infos.new_stat_data['proxy'] =  False

    m.inc_counter('Unknown_Msg')
    assert m.new_data == {}
    assert Infos.new_stat_data == {'proxy': True}
    assert 1 == m.db.stat['proxy']['Unknown_Msg']

    Infos.new_stat_data['proxy'] =  False
    m.dec_counter('Unknown_Msg')
    assert m.new_data == {}
    assert Infos.new_stat_data == {'proxy': True}
    assert 0 == m.db.stat['proxy']['Unknown_Msg']
    m.close()

@pytest.mark.asyncio
async def test_msg_build_modbus_req(ConfigTsunInv1, DeviceIndMsg, DeviceRspMsg, InverterIndMsg, InverterRspMsg, MsgModbusCmd):
    ConfigTsunInv1
    m = MemoryStream(DeviceIndMsg, (0,), True)
    m.append_msg(InverterIndMsg)
    m.read()
    assert m.control == 0x4110
    assert str(m.seq) == '01:01'
    assert m._recv_buffer==InverterIndMsg   # unhandled next message
    assert m._send_buffer==DeviceRspMsg
    assert m._forward_buffer==DeviceIndMsg

    m._send_buffer = bytearray(0) # clear send buffer for next test    
    m._forward_buffer = bytearray(0) # clear send buffer for next test    
    await m.send_modbus_cmd(Modbus.WRITE_SINGLE_REG, 0x2008, 0, logging.DEBUG)
    assert m._recv_buffer==InverterIndMsg   # unhandled next message
    assert 0 == m.send_msg_ofs
    assert m._forward_buffer == b''
    assert m.writer.sent_pdu == b'' # modbus command must be ignore, cause connection is still not up
    assert m._send_buffer == b''    # modbus command must be ignore, cause connection is still not up

    m.read()
    assert m.control == 0x4210
    assert str(m.seq) == '02:02'
    assert m._recv_buffer==b''
    assert m._send_buffer==InverterRspMsg
    assert m._forward_buffer==InverterIndMsg

    m._send_buffer = bytearray(0) # clear send buffer for next test    
    m._forward_buffer = bytearray(0) # clear send buffer for next test    
    await m.send_modbus_cmd(Modbus.WRITE_SINGLE_REG, 0x2008, 0, logging.DEBUG)
    assert 0 == m.send_msg_ofs
    assert m._forward_buffer == b''
    assert m.writer.sent_pdu == MsgModbusCmd
    assert m._send_buffer == b''

    m._send_buffer = bytearray(0) # clear send buffer for next test    
    m.test_exception_async_write = True
    await m.send_modbus_cmd(Modbus.WRITE_SINGLE_REG, 0x2008, 0, logging.DEBUG)
    assert 0 == m.send_msg_ofs
    assert m._forward_buffer == b''
    assert m._send_buffer == b''
    m.close()

@pytest.mark.asyncio
async def test_AT_cmd(ConfigTsunAllowAll, DeviceIndMsg, DeviceRspMsg, InverterIndMsg, InverterRspMsg, AtCommandIndMsg, AtCommandRspMsg):
    ConfigTsunAllowAll
    m = MemoryStream(DeviceIndMsg, (0,), True)
    m.append_msg(InverterIndMsg)
    m.append_msg(AtCommandRspMsg)
    m.read()   # read device ind
    assert m.control == 0x4110
    assert str(m.seq) == '01:01'
    assert m._recv_buffer==InverterIndMsg + AtCommandRspMsg  # unhandled next message
    assert m._send_buffer==DeviceRspMsg
    assert m._forward_buffer==DeviceIndMsg

    m._send_buffer = bytearray(0) # clear send buffer for next test    
    m._forward_buffer = bytearray(0) # clear send buffer for next test    
    await m.send_at_cmd('AT+TIME=214028,1,60,120')
    assert m._recv_buffer==InverterIndMsg + AtCommandRspMsg     # unhandled next message
    assert m._send_buffer==b''
    assert m._forward_buffer==b''
    assert str(m.seq) == '01:01'
    assert m.mqtt.key == ''
    assert m.mqtt.data == ""

    m.read() # read inverter ind
    assert m.control == 0x4210
    assert str(m.seq) == '02:02'
    assert m._recv_buffer==AtCommandRspMsg   # unhandled next message
    assert m._send_buffer==InverterRspMsg
    assert m._forward_buffer==InverterIndMsg
    
    m._send_buffer = bytearray(0) # clear send buffer for next test    
    m._forward_buffer = bytearray(0) # clear send buffer for next test    
    await m.send_at_cmd('AT+TIME=214028,1,60,120')
    assert m._recv_buffer==AtCommandRspMsg   # unhandled next message
    assert m._send_buffer==AtCommandIndMsg
    assert m._forward_buffer==b''
    assert str(m.seq) == '02:03'
    assert m.mqtt.key == ''
    assert m.mqtt.data == ""

    m._send_buffer = bytearray(0) # clear send buffer for next test    
    m.read() # read at resp
    assert m.control == 0x1510
    assert str(m.seq) == '03:03'
    assert m._recv_buffer==b''
    assert m._send_buffer==b''
    assert m._forward_buffer==b''
    assert m.key == 'at_resp'
    assert m.data == "+ok"

    m.test_exception_async_write = True
    await m.send_at_cmd('AT+TIME=214028,1,60,120')
    assert m._recv_buffer==b''
    assert m._send_buffer==b''
    assert m._forward_buffer==b''
    assert str(m.seq) == '03:04'
    assert m.forward_at_cmd_resp == False
    assert m.mqtt.key == ''
    assert m.mqtt.data == ""
    m.close()

@pytest.mark.asyncio
async def test_AT_cmd_blocked(ConfigTsunAllowAll, DeviceIndMsg, DeviceRspMsg, InverterIndMsg, InverterRspMsg, AtCommandIndMsg):
    ConfigTsunAllowAll
    m = MemoryStream(DeviceIndMsg, (0,), True)
    m.append_msg(InverterIndMsg)
    m.read()
    assert m.control == 0x4110
    assert str(m.seq) == '01:01'
    assert m._recv_buffer==InverterIndMsg   # unhandled next message
    assert m._send_buffer==DeviceRspMsg
    assert m._forward_buffer==DeviceIndMsg

    m._send_buffer = bytearray(0) # clear send buffer for next test    
    m._forward_buffer = bytearray(0) # clear send buffer for next test    
    await m.send_at_cmd('AT+WEBU')
    assert m._recv_buffer==InverterIndMsg   # unhandled next message
    assert m._send_buffer==b''
    assert m._forward_buffer==b''
    assert str(m.seq) == '01:01'
    assert m.mqtt.key == ''
    assert m.mqtt.data == ""

    m.read()
    assert m.control == 0x4210
    assert str(m.seq) == '02:02'
    assert m._recv_buffer==b''
    assert m._send_buffer==InverterRspMsg
    assert m._forward_buffer==InverterIndMsg
    
    m._send_buffer = bytearray(0) # clear send buffer for next test    
    m._forward_buffer = bytearray(0) # clear send buffer for next test    
    await m.send_at_cmd('AT+WEBU')
    assert m._recv_buffer==b''
    assert m._send_buffer==b''
    assert m._forward_buffer==b''
    assert str(m.seq) == '02:02'
    assert m.forward_at_cmd_resp == False
    assert m.mqtt.key == 'at_resp'
    assert m.mqtt.data == "'AT+WEBU' is forbidden"
    m.close()

def test_AT_cmd_ind(ConfigTsunInv1, AtCommandIndMsg):
    ConfigTsunInv1
    m = MemoryStream(AtCommandIndMsg, (0,), False)
    m.db.stat['proxy']['Unknown_Ctrl'] = 0
    m.db.stat['proxy']['AT_Command'] = 0
    m.db.stat['proxy']['AT_Command_Blocked'] = 0
    m.db.stat['proxy']['Modbus_Command'] = 0
    m.read()         # read complete msg, and dispatch msg
    assert not m.header_valid  # must be invalid, since msg was handled and buffer flushed
    assert m.msg_count == 1
    assert m.header_len==11
    assert m.snr == 2070233889
    # assert m.unique_id == '2070233889'
    assert m.control == 0x4510
    assert str(m.seq) == '03:02'
    assert m.data_len == 39
    assert m._recv_buffer==b''
    assert m._send_buffer==b''
    assert m._forward_buffer==AtCommandIndMsg
    assert m.db.stat['proxy']['Invalid_Msg_Format'] == 0
    assert m.db.stat['proxy']['AT_Command'] == 1
    assert m.db.stat['proxy']['AT_Command_Blocked'] == 0
    assert m.db.stat['proxy']['Modbus_Command'] == 0
    m.close()

def test_AT_cmd_ind_block(ConfigTsunInv1, AtCommandIndMsgBlock):
    ConfigTsunInv1
    m = MemoryStream(AtCommandIndMsgBlock, (0,), False)
    m.db.stat['proxy']['Unknown_Ctrl'] = 0
    m.db.stat['proxy']['AT_Command'] = 0
    m.db.stat['proxy']['AT_Command_Blocked'] = 0
    m.db.stat['proxy']['Modbus_Command'] = 0
    m.read()         # read complete msg, and dispatch msg
    assert not m.header_valid  # must be invalid, since msg was handled and buffer flushed
    assert m.msg_count == 1
    assert m.header_len==11
    assert m.snr == 2070233889
    # assert m.unique_id == '2070233889'
    assert m.control == 0x4510
    assert str(m.seq) == '03:02'
    assert m.data_len == 23
    assert m._recv_buffer==b''
    assert m._send_buffer==b''
    assert m._forward_buffer==b''
    assert m.db.stat['proxy']['Invalid_Msg_Format'] == 0
    assert m.db.stat['proxy']['AT_Command'] == 0
    assert m.db.stat['proxy']['AT_Command_Blocked'] == 1
    assert m.db.stat['proxy']['Modbus_Command'] == 0
    m.close()

def test_msg_at_command_rsp1(ConfigTsunInv1, AtCommandRspMsg):
    ConfigTsunInv1
    m = MemoryStream(AtCommandRspMsg)
    m.db.stat['proxy']['Unknown_Ctrl'] = 0
    m.db.stat['proxy']['Modbus_Command'] = 0
    m.forward_at_cmd_resp = True
    m.read()         # read complete msg, and dispatch msg
    assert not m.header_valid  # must be invalid, since msg was handled and buffer flushed
    assert m.msg_count == 1
    assert m.control == 0x1510
    assert str(m.seq) == '03:03'
    assert m.header_len==11
    assert m.data_len==17
    assert m._forward_buffer==AtCommandRspMsg
    assert m._send_buffer==b''
    assert m.db.stat['proxy']['Unknown_Ctrl'] == 0
    assert m.db.stat['proxy']['Modbus_Command'] == 0
    m.close()

def test_msg_at_command_rsp2(ConfigTsunInv1, AtCommandRspMsg):
    ConfigTsunInv1
    m = MemoryStream(AtCommandRspMsg)
    m.db.stat['proxy']['Unknown_Ctrl'] = 0
    m.db.stat['proxy']['Modbus_Command'] = 0
    m.forward_at_cmd_resp = False
    m.read()         # read complete msg, and dispatch msg
    assert not m.header_valid  # must be invalid, since msg was handled and buffer flushed
    assert m.msg_count == 1
    assert m.control == 0x1510
    assert str(m.seq) == '03:03'
    assert m.header_len==11
    assert m.data_len==17
    assert m._forward_buffer==b''
    assert m._send_buffer==b''
    assert m.db.stat['proxy']['Unknown_Ctrl'] == 0
    assert m.db.stat['proxy']['Modbus_Command'] == 0
    m.close()

def test_msg_modbus_req(ConfigTsunInv1, MsgModbusCmd, MsgModbusCmdFwd):
    ConfigTsunInv1
    m = MemoryStream(b'')
    m.snr = get_sn_int()
    m.state = State.up
    c = m.createClientStream(MsgModbusCmd)

    m.db.stat['proxy']['Unknown_Ctrl'] = 0
    m.db.stat['proxy']['AT_Command'] = 0
    m.db.stat['proxy']['Modbus_Command'] = 0
    m.db.stat['proxy']['Invalid_Msg_Format'] = 0
    c.read()         # read complete msg, and dispatch msg
    assert not c.header_valid  # must be invalid, since msg was handled and buffer flushed
    assert c.msg_count == 1
    assert c.control == 0x4510
    assert str(c.seq) == '03:02'
    assert c.header_len==11
    assert c.data_len==23
    assert c._forward_buffer==b''
    assert c._send_buffer==b''
    assert m.writer.sent_pdu == MsgModbusCmdFwd
    assert m.db.stat['proxy']['Unknown_Ctrl'] == 0
    assert m.db.stat['proxy']['AT_Command'] == 0
    assert m.db.stat['proxy']['Modbus_Command'] == 1
    assert m.db.stat['proxy']['Invalid_Msg_Format'] == 0
    m.close()

def test_msg_modbus_req2(ConfigTsunInv1, MsgModbusCmdCrcErr):
    ConfigTsunInv1
    m = MemoryStream(b'')
    m.snr = get_sn_int()
    m.state = State.up
    c = m.createClientStream(MsgModbusCmdCrcErr)

    m.db.stat['proxy']['Unknown_Ctrl'] = 0
    m.db.stat['proxy']['AT_Command'] = 0
    m.db.stat['proxy']['Modbus_Command'] = 0
    m.db.stat['proxy']['Invalid_Msg_Format'] = 0
    c.read()         # read complete msg, and dispatch msg
    assert not c.header_valid  # must be invalid, since msg was handled and buffer flushed
    assert c.msg_count == 1
    assert c.control == 0x4510
    assert str(c.seq) == '03:02'
    assert c.header_len==11
    assert c.data_len==23
    assert c._forward_buffer==b''
    assert c._send_buffer==b''
    assert m.writer.sent_pdu==b''
    assert m.db.stat['proxy']['Unknown_Ctrl'] == 0
    assert m.db.stat['proxy']['AT_Command'] == 0
    assert m.db.stat['proxy']['Modbus_Command'] == 0
    assert m.db.stat['proxy']['Invalid_Msg_Format'] == 1
    m.close()

def test_msg_unknown_cmd_req(ConfigTsunInv1, MsgUnknownCmd):
    ConfigTsunInv1
    m = MemoryStream(MsgUnknownCmd, (0,), False)
    m.db.stat['proxy']['Unknown_Ctrl'] = 0
    m.db.stat['proxy']['AT_Command'] = 0
    m.db.stat['proxy']['Modbus_Command'] = 0
    m.db.stat['proxy']['Invalid_Msg_Format'] = 0
    m.read()         # read complete msg, and dispatch msg
    assert not m.header_valid  # must be invalid, since msg was handled and buffer flushed
    assert m.msg_count == 1
    assert m.control == 0x4510
    assert str(m.seq) == '03:02'
    assert m.header_len==11
    assert m.data_len==23
    assert m._forward_buffer==MsgUnknownCmd
    assert m._send_buffer==b''
    assert m.db.stat['proxy']['Unknown_Ctrl'] == 0
    assert m.db.stat['proxy']['AT_Command'] == 0
    assert m.db.stat['proxy']['Modbus_Command'] == 0
    assert m.db.stat['proxy']['Invalid_Msg_Format'] == 0
    m.close()

def test_msg_modbus_rsp1(ConfigTsunInv1, MsgModbusRsp):
    '''Modbus response without a valid Modbus request must be dropped'''
    ConfigTsunInv1
    m = MemoryStream(MsgModbusRsp)
    m.db.stat['proxy']['Unknown_Ctrl'] = 0
    m.db.stat['proxy']['Modbus_Command'] = 0
    m.read()         # read complete msg, and dispatch msg
    assert not m.header_valid  # must be invalid, since msg was handled and buffer flushed
    assert m.msg_count == 1
    assert m.control == 0x1510
    assert str(m.seq) == '03:03'
    assert m.header_len==11
    assert m.data_len==59
    assert m._forward_buffer==b''
    assert m._send_buffer==b''
    assert m.db.stat['proxy']['Unknown_Ctrl'] == 0
    assert m.db.stat['proxy']['Modbus_Command'] == 0
    m.close()

def test_msg_modbus_rsp2(ConfigTsunInv1, MsgModbusRsp):
    '''Modbus response with a valid Modbus request must be forwarded'''
    ConfigTsunInv1
    m = MemoryStream(MsgModbusRsp)
    m.append_msg(MsgModbusRsp)

    m.mb.rsp_handler = m._SolarmanV5__forward_msg
    m.mb.last_addr = 1
    m.mb.last_fcode = 3
    m.mb.last_len = 20
    m.mb.last_reg = 0x3008
    m.mb.req_pend = True
    m.mb.err = 0
    # assert m.db.db == {'inverter': {'Manufacturer': 'TSUN', 'Equipment_Model': 'TSOL-MSxx00'}}
    m.new_data['inverter'] = False

    m.read()         # read complete msg, and dispatch msg
    assert not m.header_valid  # must be invalid, since msg was handled and buffer flushed
    assert m.mb.err == 0
    assert m.msg_count == 1
    assert m._forward_buffer==MsgModbusRsp
    assert m._send_buffer==b''
    # assert m.db.db == {'inverter': {'Version': 'V5.1.09', 'Rated_Power': 300}, 'grid': {'Voltage': 225.9, 'Current': 0.41, 'Frequency': 49.99, 'Output_Power': 94.8}, 'env': {'Inverter_Temp': 22}, 'input': {'pv1': {'Voltage': 0.8, 'Current': 0.0, 'Power': 0.0}, 'pv2': {'Voltage': 34.5, 'Current': 2.89, 'Power': 99.8}, 'pv3': {'Voltage': 0.0, 'Current': 0.0, 'Power': 0.0}, 'pv4': {'Voltage': 0.0, 'Current': 0.0, 'Power': 0.0}}}
    assert m.db.get_db_value(Register.VERSION) == 'V4.0.10'
    assert m.new_data['inverter'] == True
    m.new_data['inverter'] = False

    m.mb.req_pend = True
    m.read()         # read complete msg, and dispatch msg
    assert not m.header_valid  # must be invalid, since msg was handled and buffer flushed
    assert m.mb.err == 0
    assert m.msg_count == 2
    assert m._forward_buffer==MsgModbusRsp
    assert m._send_buffer==b''
    # assert m.db.db == {'inverter': {'Version': 'V5.1.09', 'Rated_Power': 300}, 'grid': {'Voltage': 225.9, 'Current': 0.41, 'Frequency': 49.99, 'Output_Power': 94.8}, 'env': {'Inverter_Temp': 22}, 'input': {'pv1': {'Voltage': 0.8, 'Current': 0.0, 'Power': 0.0}, 'pv2': {'Voltage': 34.5, 'Current': 2.89, 'Power': 99.8}, 'pv3': {'Voltage': 0.0, 'Current': 0.0, 'Power': 0.0}, 'pv4': {'Voltage': 0.0, 'Current': 0.0, 'Power': 0.0}}}
    assert m.db.get_db_value(Register.VERSION) == 'V4.0.10'
    assert m.new_data['inverter'] == False

    m.close()

def test_msg_modbus_rsp3(ConfigTsunInv1, MsgModbusRsp):
    '''Modbus response with a valid Modbus request must be forwarded'''
    ConfigTsunInv1
    m = MemoryStream(MsgModbusRsp)
    m.append_msg(MsgModbusRsp)

    m.mb.rsp_handler = m._SolarmanV5__forward_msg
    m.mb.last_addr = 1
    m.mb.last_fcode = 3
    m.mb.last_len = 20
    m.mb.last_reg = 0x3008
    m.mb.req_pend = True
    m.mb.err = 0
    # assert m.db.db == {'inverter': {'Manufacturer': 'TSUN', 'Equipment_Model': 'TSOL-MSxx00'}}
    m.new_data['inverter'] = False

    m.read()         # read complete msg, and dispatch msg
    assert not m.header_valid  # must be invalid, since msg was handled and buffer flushed
    assert m.mb.err == 0
    assert m.msg_count == 1
    assert m._forward_buffer==MsgModbusRsp
    assert m._send_buffer==b''
    # assert m.db.db == {'inverter': {'Version': 'V5.1.09', 'Rated_Power': 300}, 'grid': {'Voltage': 225.9, 'Current': 0.41, 'Frequency': 49.99, 'Output_Power': 94.8}, 'env': {'Inverter_Temp': 22}, 'input': {'pv1': {'Voltage': 0.8, 'Current': 0.0, 'Power': 0.0}, 'pv2': {'Voltage': 34.5, 'Current': 2.89, 'Power': 99.8}, 'pv3': {'Voltage': 0.0, 'Current': 0.0, 'Power': 0.0}, 'pv4': {'Voltage': 0.0, 'Current': 0.0, 'Power': 0.0}}}
    assert m.db.get_db_value(Register.VERSION) == 'V4.0.10'
    assert m.new_data['inverter'] == True
    m.new_data['inverter'] = False

    m.read()         # read complete msg, and dispatch msg
    assert not m.header_valid  # must be invalid, since msg was handled and buffer flushed
    assert m.mb.err == 5
    assert m.msg_count == 2
    assert m._forward_buffer==MsgModbusRsp
    assert m._send_buffer==b''
    # assert m.db.db == {'inverter': {'Version': 'V5.1.09', 'Rated_Power': 300}, 'grid': {'Voltage': 225.9, 'Current': 0.41, 'Frequency': 49.99, 'Output_Power': 94.8}, 'env': {'Inverter_Temp': 22}, 'input': {'pv1': {'Voltage': 0.8, 'Current': 0.0, 'Power': 0.0}, 'pv2': {'Voltage': 34.5, 'Current': 2.89, 'Power': 99.8}, 'pv3': {'Voltage': 0.0, 'Current': 0.0, 'Power': 0.0}, 'pv4': {'Voltage': 0.0, 'Current': 0.0, 'Power': 0.0}}}
    assert m.db.get_db_value(Register.VERSION) == 'V4.0.10'
    assert m.new_data['inverter'] == False

    m.close()

def test_msg_unknown_rsp(ConfigTsunInv1, MsgUnknownCmdRsp):
    ConfigTsunInv1
    m = MemoryStream(MsgUnknownCmdRsp)
    m.db.stat['proxy']['Unknown_Ctrl'] = 0
    m.db.stat['proxy']['Modbus_Command'] = 0
    m.read()         # read complete msg, and dispatch msg
    assert not m.header_valid  # must be invalid, since msg was handled and buffer flushed
    assert m.msg_count == 1
    assert m.control == 0x1510
    assert str(m.seq) == '03:03'
    assert m.header_len==11
    assert m.data_len==59
    assert m._forward_buffer==MsgUnknownCmdRsp
    assert m._send_buffer==b''
    assert m.db.stat['proxy']['Unknown_Ctrl'] == 0
    assert m.db.stat['proxy']['Modbus_Command'] == 0
    m.close()

def test_msg_modbus_invalid(ConfigTsunInv1, MsgModbusInvalid):
    ConfigTsunInv1
    m = MemoryStream(MsgModbusInvalid, (0,), False)
    m.db.stat['proxy']['Unknown_Ctrl'] = 0
    m.db.stat['proxy']['Modbus_Command'] = 0
    m.read()         # read complete msg, and dispatch msg
    assert not m.header_valid  # must be invalid, since msg was handled and buffer flushed
    assert m.msg_count == 1
    assert m._forward_buffer==b''
    assert m._send_buffer==b''
    assert m.db.stat['proxy']['Unknown_Ctrl'] == 0
    assert m.db.stat['proxy']['Modbus_Command'] == 0
    m.close()

def test_msg_modbus_fragment(ConfigTsunInv1, MsgModbusRsp):
    ConfigTsunInv1
    # receive more bytes than expected (7 bytes from the next msg)
    m = MemoryStream(MsgModbusRsp+b'\x00\x00\x00\x45\x10\x52\x31', (0,))
    m.db.stat['proxy']['Unknown_Ctrl'] = 0
    m.db.stat['proxy']['Modbus_Command'] = 0
    m.mb.rsp_handler = m._SolarmanV5__forward_msg
    m.mb.last_addr = 1
    m.mb.last_fcode = 3
    m.mb.last_len = 20
    m.mb.last_reg = 0x3008
    m.mb.req_pend = True
    m.mb.err = 0

    m.read()         # read complete msg, and dispatch msg
    assert not m.header_valid  # must be invalid, since msg was handled and buffer flushed
    assert m.msg_count == 1
    assert m._forward_buffer==MsgModbusRsp
    assert m._send_buffer == b''
    assert m.mb.err == 0
    assert m.modbus_elms == 20-1  # register 0x300d is unknown, so one value can't be mapped
    assert m.db.stat['proxy']['Unknown_Ctrl'] == 0
    assert m.db.stat['proxy']['Modbus_Command'] == 0
    m.close()
'''
def test_zombie_conn(ConfigTsunInv1, MsgInverterInd):
    ConfigTsunInv1
    tracer.setLevel(logging.DEBUG)
    m1 = MemoryStream(MsgInverterInd, (0,))
    m2 = MemoryStream(MsgInverterInd, (0,))
    m3 = MemoryStream(MsgInverterInd, (0,))
    assert m1.state == m1.State.init
    assert m2.state == m2.State.init
    assert m3.state == m3.State.init
    m1.read()         # read complete msg, and set unique_id
    assert m1.state == m1.State.init
    assert m2.state == m2.State.init
    assert m3.state == m3.State.init
    m2.read()         # read complete msg, and set unique_id
    assert m1.state == m1.State.closed
    assert m2.state == m2.State.init
    assert m3.state == m3.State.init
    m3.read()         # read complete msg, and set unique_id
    assert m1.state == m1.State.closed
    assert m2.state == m2.State.closed
    assert m3.state == m3.State.init
    m1.close()
    m2.close()
    m3.close()
'''