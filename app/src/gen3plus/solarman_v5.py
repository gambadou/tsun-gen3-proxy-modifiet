import struct
import logging
import time
import asyncio
from datetime import datetime

if __name__ == "app.src.gen3plus.solarman_v5":
    from app.src.messages import hex_dump_memory, Message, State
    from app.src.modbus import Modbus
    from app.src.my_timer import Timer
    from app.src.config import Config
    from app.src.gen3plus.infos_g3p import InfosG3P
    from app.src.infos import Register
else:  # pragma: no cover
    from messages import hex_dump_memory, Message, State
    from config import Config
    from modbus import Modbus
    from my_timer import Timer
    from gen3plus.infos_g3p import InfosG3P
    from infos import Register

logger = logging.getLogger('msg')


class Sequence():
    def __init__(self, server_side: bool):
        self.rcv_idx = 0
        self.snd_idx = 0
        self.server_side = server_side

    def set_recv(self, val: int):
        if self.server_side:
            self.rcv_idx = val >> 8
            self.snd_idx = val & 0xff
        else:
            self.rcv_idx = val & 0xff
            self.snd_idx = val >> 8

    def get_send(self):
        self.snd_idx += 1
        self.snd_idx &= 0xff
        if self.server_side:
            return (self.rcv_idx << 8) | self.snd_idx
        else:
            return (self.snd_idx << 8) | self.rcv_idx

    def __str__(self):
        return f'{self.rcv_idx:02x}:{self.snd_idx:02x}'


class SolarmanV5(Message):
    AT_CMD = 1
    MB_RTU_CMD = 2
    MB_START_TIMEOUT = 40
    '''start delay for Modbus polling in server mode'''
    MB_REGULAR_TIMEOUT = 60
    '''regular Modbus polling time in server mode'''
    MB_CLIENT_DATA_UP = 30
    '''Data up time in client mode'''
    HDR_FMT = '<BLLL'
    '''format string for packing of the header'''

    def __init__(self, server_side: bool, client_mode: bool):
        super().__init__(server_side, self.send_modbus_cb, mb_timeout=8)

        self.header_len = 11  # overwrite construcor in class Message
        self.control = 0
        self.seq = Sequence(server_side)
        self.snr = 0
        self.db = InfosG3P(client_mode)
        self.time_ofs = 0
        self.forward_at_cmd_resp = False
        self.no_forwarding = False
        '''not allowed to connect to TSUN cloud by connection type'''
        self.switch = {

            0x4210: self.msg_data_ind,   # real time data
            0x1210: self.msg_response,   # at least every 5 minutes

            0x4710: self.msg_hbeat_ind,  # heatbeat
            0x1710: self.msg_response,   # every 2 minutes

            # every 3 hours comes a sync seuqence:
            # 00:00:00  0x4110   device data     ftype: 0x02
            # 00:00:02  0x4210   real time data  ftype: 0x01
            # 00:00:03  0x4210   real time data  ftype: 0x81
            # 00:00:05  0x4310   wifi data       ftype: 0x81    sub-id 0x0018: 0c   # noqa: E501
            # 00:00:06  0x4310   wifi data       ftype: 0x81    sub-id 0x0018: 1c   # noqa: E501
            # 00:00:07  0x4310   wifi data       ftype: 0x01    sub-id 0x0018: 0c   # noqa: E501
            # 00:00:08  0x4810   options?        ftype: 0x01

            0x4110: self.msg_dev_ind,     # device data, sync start
            0x1110: self.msg_response,    # every 3 hours

            0x4310: self.msg_sync_start,  # regulary after 3-6 hours
            0x1310: self.msg_response,
            0x4810: self.msg_sync_end,    # sync end
            0x1810: self.msg_response,

            #
            # MODbus or AT cmd
            0x4510: self.msg_command_req,  # from server
            0x1510: self.msg_command_rsp,     # from inverter
            # 0x0510: self.msg_command_rsp,     # from inverter
        }

        self.log_lvl = {

            0x4210: logging.INFO,   # real time data
            0x1210: logging.INFO,   # at least every 5 minutes

            0x4710: logging.DEBUG,  # heatbeat
            0x1710: logging.DEBUG,  # every 2 minutes

            0x4110: logging.INFO,   # device data, sync start
            0x1110: logging.INFO,   # every 3 hours

            0x4310: logging.INFO,   # regulary after 3-6 hours
            0x1310: logging.INFO,

            0x4810: logging.INFO,   # sync end
            0x1810: logging.INFO,

            #
            # MODbus or AT cmd
            0x4510: logging.INFO,  # from server
            0x1510: self.get_cmd_rsp_log_lvl,
        }
        self.modbus_elms = 0    # for unit tests
        g3p_cnf = Config.get('gen3plus')

        if 'at_acl' in g3p_cnf:  # pragma: no cover
            self.at_acl = g3p_cnf['at_acl']

        self.node_id = 'G3P'  # will be overwritten in __set_serial_no
        self.mb_timer = Timer(self.mb_timout_cb, self.node_id)
        self.mb_timeout = self.MB_REGULAR_TIMEOUT
        self.mb_first_timeout = self.MB_START_TIMEOUT
        '''timer value for next Modbus polling request'''
        self.modbus_polling = False
        self.sensor_list = 0x0000

    '''
    Our puplic methods
    '''
    def close(self) -> None:
        logging.debug('Solarman.close()')
        if self.server_side:
            # set inverter state to offline, if output power is very low
            logging.debug('close power: '
                          f'{self.db.get_db_value(Register.OUTPUT_POWER, -1)}')
            if self.db.get_db_value(Register.OUTPUT_POWER, 999) < 2:
                self.db.set_db_def_value(Register.INVERTER_STATUS, 0)
                self.new_data['env'] = True

        # we have references to methods of this class in self.switch
        # so we have to erase self.switch, otherwise this instance can't be
        # deallocated by the garbage collector ==> we get a memory leak
        self.switch.clear()
        self.log_lvl.clear()
        self.state = State.closed
        self.mb_timer.close()
        super().close()

    async def send_start_cmd(self, snr: int, host: str,
                             start_timeout=MB_CLIENT_DATA_UP):
        self.no_forwarding = True
        self.snr = snr
        self.__set_serial_no(snr)
        self.mb_timeout = start_timeout
        self.db.set_db_def_value(Register.IP_ADDRESS, host)
        self.db.set_db_def_value(Register.POLLING_INTERVAL,
                                 self.mb_timeout)
        self.db.set_db_def_value(Register.HEARTBEAT_INTERVAL,
                                 120)
        self.new_data['controller'] = True

        self.state = State.up
        self._send_modbus_cmd(Modbus.READ_REGS, 0x3000, 48, logging.DEBUG)
        self.mb_timer.start(self.mb_timeout)

    def new_state_up(self):
        if self.state is not State.up:
            self.state = State.up
            if (self.modbus_polling):
                self.mb_timer.start(self.mb_first_timeout)
                self.db.set_db_def_value(Register.POLLING_INTERVAL,
                                         self.mb_timeout)

    def __set_config_parms(self, inv: dict):
        '''init connection with params from the configuration'''
        self.node_id = inv['node_id']
        self.sug_area = inv['suggested_area']
        self.modbus_polling = inv['modbus_polling']
        self.sensor_list = inv['sensor_list']

    def __set_serial_no(self, snr: int):
        '''check the serial number and configure the inverter connection'''
        serial_no = str(snr)
        if self.unique_id == serial_no:
            logger.debug(f'SerialNo: {serial_no}')
        else:
            inverters = Config.get('inverters')
            # logger.debug(f'Inverters: {inverters}')

            for inv in inverters.values():
                # logger.debug(f'key: {key} -> {inv}')
                if (type(inv) is dict and 'monitor_sn' in inv
                   and inv['monitor_sn'] == snr):
                    self.__set_config_parms(inv)
                    self.db.set_pv_module_details(inv)
                    logger.debug(f'SerialNo {serial_no} allowed! area:{self.sug_area}')  # noqa: E501
                    break
            else:
                self.node_id = ''
                self.sug_area = ''
                if 'allow_all' not in inverters or not inverters['allow_all']:
                    self.inc_counter('Unknown_SNR')
                    self.unique_id = None
                    logger.warning(f'ignore message from unknow inverter! (SerialNo: {serial_no})')  # noqa: E501
                    return
                logger.warning(f'SerialNo {serial_no} not known but accepted!')

            self.unique_id = serial_no

    def read(self) -> float:
        '''process all received messages in the _recv_buffer'''
        self._read()
        while True:
            if not self.header_valid:
                self.__parse_header(self._recv_buffer, len(self._recv_buffer))

            if self.header_valid and len(self._recv_buffer) >= \
               (self.header_len + self.data_len+2):
                self.__process_complete_received_msg()
                self.__flush_recv_msg()
            else:
                return 0  # wait 0s before sending a response

    def __process_complete_received_msg(self):
        log_lvl = self.log_lvl.get(self.control, logging.WARNING)
        if callable(log_lvl):
            log_lvl = log_lvl()
        hex_dump_memory(log_lvl, f'Received from {self.addr}:',
                        self._recv_buffer, self.header_len +
                        self.data_len+2)
        if self.__trailer_is_ok(self._recv_buffer, self.header_len
                                + self.data_len + 2):
            if self.state == State.init:
                self.state = State.received
            self.__set_serial_no(self.snr)
            self.__dispatch_msg()

    def forward(self, buffer, buflen) -> None:
        '''add the actual receive msg to the forwarding queue'''
        if self.no_forwarding:
            return
        tsun = Config.get('solarman')
        if tsun['enabled']:
            self._forward_buffer += buffer[:buflen]
            hex_dump_memory(logging.DEBUG, 'Store for forwarding:',
                            buffer, buflen)

            fnc = self.switch.get(self.control, self.msg_unknown)
            logger.info(self.__flow_str(self.server_side, 'forwrd') +
                        f' Ctl: {int(self.control):#04x}'
                        f' Msg: {fnc.__name__!r}')

    def _init_new_client_conn(self) -> bool:
        return False

    '''
    Our private methods
    '''
    def __flow_str(self, server_side: bool, type: str):  # noqa: F821
        switch = {
            'rx':      '  <',
            'tx':      '  >',
            'forwrd':  '<< ',
            'drop':    ' xx',
            'rxS':     '>  ',
            'txS':     '<  ',
            'forwrdS': ' >>',
            'dropS':   'xx ',
        }
        if server_side:
            type += 'S'
        return switch.get(type, '???')

    def _timestamp(self):
        # utc as epoche
        return int(time.time())    # pragma: no cover

    def _heartbeat(self) -> int:
        return 60                  # pragma: no cover

    def __parse_header(self, buf: bytes, buf_len: int) -> None:

        if (buf_len < self.header_len):  # enough bytes for complete header?
            return

        result = struct.unpack_from('<BHHHL', buf, 0)

        # store parsed header values in the class
        start = result[0]            # start byte
        self.data_len = result[1]    # len of variable id string
        self.control = result[2]
        self.seq.set_recv(result[3])
        self.snr = result[4]

        if start != 0xA5:
            hex_dump_memory(logging.ERROR,
                            'Drop packet w invalid start byte from'
                            f' {self.addr}:', buf, buf_len)

            self.inc_counter('Invalid_Msg_Format')
            # erase broken recv buffer
            self._recv_buffer = bytearray()
            return
        self.header_valid = True

    def __trailer_is_ok(self, buf: bytes, buf_len: int) -> bool:
        crc = buf[self.data_len+11]
        stop = buf[self.data_len+12]
        if stop != 0x15:
            hex_dump_memory(logging.ERROR,
                            'Drop packet w invalid stop byte from '
                            f'{self.addr}:', buf, buf_len)
            self.inc_counter('Invalid_Msg_Format')
            if len(self._recv_buffer) > (self.data_len+13):
                next_start = buf[self.data_len+13]
                if next_start != 0xa5:
                    # erase broken recv buffer
                    self._recv_buffer = bytearray()

            return False

        check = sum(buf[1:buf_len-2]) & 0xff
        if check != crc:
            self.inc_counter('Invalid_Msg_Format')
            logger.debug(f'CRC {int(crc):#02x} {int(check):#08x}'
                         f' Stop:{int(stop):#02x}')
            # start & stop byte are valid, discard only this message
            return False

        return True

    def __build_header(self, ctrl) -> None:
        '''build header for new transmit message'''
        self.send_msg_ofs = len(self._send_buffer)

        self._send_buffer += struct.pack(
            '<BHHHL', 0xA5, 0, ctrl, self.seq.get_send(), self.snr)
        fnc = self.switch.get(ctrl, self.msg_unknown)
        logger.info(self.__flow_str(self.server_side, 'tx') +
                    f' Ctl: {int(ctrl):#04x} Msg: {fnc.__name__!r}')

    def __finish_send_msg(self) -> None:
        '''finish the transmit message, set lenght and checksum'''
        _len = len(self._send_buffer) - self.send_msg_ofs
        struct.pack_into('<H', self._send_buffer, self.send_msg_ofs+1, _len-11)
        check = sum(self._send_buffer[self.send_msg_ofs+1:self.send_msg_ofs +
                                      _len]) & 0xff
        self._send_buffer += struct.pack('<BB', check, 0x15)    # crc & stop

    def _update_header(self, _forward_buffer):
        '''update header for message before forwarding,
        set sequence and checksum'''
        _len = len(_forward_buffer)
        ofs = 0
        while ofs < _len:
            result = struct.unpack_from('<BH', _forward_buffer, ofs)
            data_len = result[1]    # len of variable id string

            struct.pack_into('<H', _forward_buffer, ofs+5,
                             self.seq.get_send())

            check = sum(_forward_buffer[ofs+1:ofs+data_len+11]) & 0xff
            struct.pack_into('<B', _forward_buffer, ofs+data_len+11, check)
            ofs += (13 + data_len)

    def __dispatch_msg(self) -> None:
        fnc = self.switch.get(self.control, self.msg_unknown)
        if self.unique_id:
            logger.info(self.__flow_str(self.server_side, 'rx') +
                        f' Ctl: {int(self.control):#04x}' +
                        f' Msg: {fnc.__name__!r}')
            fnc()
        else:
            logger.info(self.__flow_str(self.server_side, 'drop') +
                        f' Ctl: {int(self.control):#04x}' +
                        f' Msg: {fnc.__name__!r}')

    def __flush_recv_msg(self) -> None:
        self._recv_buffer = self._recv_buffer[(self.header_len +
                                               self.data_len+2):]
        self.header_valid = False

    def __send_ack_rsp(self, msgtype, ftype, ack=1):
        self.__build_header(msgtype)
        self._send_buffer += struct.pack('<BBLL', ftype, ack,
                                         self._timestamp(),
                                         self._heartbeat())
        self.__finish_send_msg()

    def send_modbus_cb(self, pdu: bytearray, log_lvl: int, state: str):
        if self.state != State.up:
            logger.warning(f'[{self.node_id}] ignore MODBUS cmd,'
                           ' cause the state is not UP anymore')
            return
        self.__build_header(0x4510)
        self._send_buffer += struct.pack('<BHLLL', self.MB_RTU_CMD,
                                         self.sensor_list, 0, 0, 0)
        self._send_buffer += pdu
        self.__finish_send_msg()
        hex_dump_memory(log_lvl, f'Send Modbus {state}:{self.addr}:',
                        self._send_buffer, len(self._send_buffer))
        self.writer.write(self._send_buffer)
        self._send_buffer = bytearray(0)  # self._send_buffer[sent:]

    def _send_modbus_cmd(self, func, addr, val, log_lvl) -> None:
        if self.state != State.up:
            logger.log(log_lvl, f'[{self.node_id}] ignore MODBUS cmd,'
                       ' as the state is not UP')
            return
        self.mb.build_msg(Modbus.INV_ADDR, func, addr, val, log_lvl)

    async def send_modbus_cmd(self, func, addr, val, log_lvl) -> None:
        self._send_modbus_cmd(func, addr, val, log_lvl)

    def mb_timout_cb(self, exp_cnt):
        self.mb_timer.start(self.mb_timeout)

        self._send_modbus_cmd(Modbus.READ_REGS, 0x3000, 48, logging.DEBUG)

        if 1 == (exp_cnt % 30):
            # logging.info("Regular Modbus Status request")
            self._send_modbus_cmd(Modbus.READ_REGS, 0x2000, 96, logging.DEBUG)

    def at_cmd_forbidden(self, cmd: str, connection: str) -> bool:
        return not cmd.startswith(tuple(self.at_acl[connection]['allow'])) or \
                cmd.startswith(tuple(self.at_acl[connection]['block']))

    async def send_at_cmd(self, at_cmd: str) -> None:
        if self.state != State.up:
            logger.warning(f'[{self.node_id}] ignore AT+ cmd,'
                           ' as the state is not UP')
            return
        at_cmd = at_cmd.strip()

        if self.at_cmd_forbidden(cmd=at_cmd, connection='mqtt'):
            data_json = f'\'{at_cmd}\' is forbidden'
            node_id = self.node_id
            key = 'at_resp'
            logger.info(f'{key}: {data_json}')
            await self.mqtt.publish(f'{self.entity_prfx}{node_id}{key}', data_json)  # noqa: E501
            return

        self.forward_at_cmd_resp = False
        self.__build_header(0x4510)
        self._send_buffer += struct.pack(f'<BHLLL{len(at_cmd)}sc', self.AT_CMD,
                                         0x0002, 0, 0, 0,
                                         at_cmd.encode('utf-8'), b'\r')
        self.__finish_send_msg()
        try:
            await self.async_write('Send AT Command:')
        except Exception:
            self._send_buffer = bytearray(0)

    def __forward_msg(self):
        self.forward(self._recv_buffer, self.header_len+self.data_len+2)

    def __build_model_name(self):
        db = self.db
        max_pow = db.get_db_value(Register.MAX_DESIGNED_POWER, 0)
        rated = db.get_db_value(Register.RATED_POWER, 0)
        model = None
        if max_pow == 2000:
            if rated == 800 or rated == 600:
                model = f'TSOL-MS{max_pow}({rated})'
            else:
                model = f'TSOL-MS{max_pow}'
        elif max_pow == 1800 or max_pow == 1600:
            model = f'TSOL-MS{max_pow}'
        if model:
            logger.info(f'Model: {model}')
            self.db.set_db_def_value(Register.EQUIPMENT_MODEL, model)

    def __process_data(self, ftype, ts):
        inv_update = False
        msg_type = self.control >> 8
        for key, update in self.db.parse(self._recv_buffer, msg_type, ftype,
                                         self.node_id):
            if update:
                if key == 'inverter':
                    inv_update = True
                self._set_mqtt_timestamp(key, ts)
                self.new_data[key] = True

        if inv_update:
            self.__build_model_name()
    '''
    Message handler methods
    '''
    def msg_unknown(self):
        logger.warning(f"Unknow Msg: ID:{int(self.control):#04x}")
        self.inc_counter('Unknown_Msg')
        self.__forward_msg()

    def msg_dev_ind(self):
        data = self._recv_buffer[self.header_len:]
        result = struct.unpack_from(self.HDR_FMT, data, 0)
        ftype = result[0]  # always 2
        total = result[1]
        tim = result[2]
        res = result[3]  # always zero
        logger.info(f'frame type:{ftype:02x}'
                    f' timer:{tim:08x}s  null:{res}')
        if self.time_ofs:
            #     dt = datetime.fromtimestamp(total + self.time_ofs)
            #     logger.info(f'ts: {dt.strftime("%Y-%m-%d %H:%M:%S")}')
            ts = total + self.time_ofs
        else:
            ts = None
        self.__process_data(ftype, ts)
        self.sensor_list = int(self.db.get_db_value(Register.SENSOR_LIST, 0),
                               16)
        self.__forward_msg()
        self.__send_ack_rsp(0x1110, ftype)

    def msg_data_ind(self):
        data = self._recv_buffer
        result = struct.unpack_from('<BHLLLHL', data, self.header_len)
        ftype = result[0]  # 1 or 0x81
        sensor = result[1]
        total = result[2]
        tim = result[3]
        if 1 == ftype:
            self.time_ofs = result[4]
        unkn = result[5]
        cnt = result[6]
        if sensor != self.sensor_list:
            logger.warning(f'Unexpected Sensor-List:{sensor:04x}'
                           f' (!={self.sensor_list:04x})')
        logger.info(f'ftype:{ftype:02x} timer:{tim:08x}s'
                    f' ??: {unkn:04x} cnt:{cnt}')
        if self.time_ofs:
            #     dt = datetime.fromtimestamp(total + self.time_ofs)
            #     logger.info(f'ts: {dt.strftime("%Y-%m-%d %H:%M:%S")}')
            ts = total + self.time_ofs
        else:
            ts = None

        self.__process_data(ftype, ts)
        self.__forward_msg()
        self.__send_ack_rsp(0x1210, ftype)
        self.new_state_up()

    def msg_sync_start(self):
        data = self._recv_buffer[self.header_len:]
        result = struct.unpack_from(self.HDR_FMT, data, 0)
        ftype = result[0]
        total = result[1]
        self.time_ofs = result[3]

        dt = datetime.fromtimestamp(total + self.time_ofs)
        logger.info(f'ts: {dt.strftime("%Y-%m-%d %H:%M:%S")}')

        self.__forward_msg()
        self.__send_ack_rsp(0x1310, ftype)

    def msg_command_req(self):
        data = self._recv_buffer[self.header_len:
                                 self.header_len+self.data_len]
        result = struct.unpack_from('<B', data, 0)
        ftype = result[0]
        if ftype == self.AT_CMD:
            at_cmd = data[15:].decode()
            if self.at_cmd_forbidden(cmd=at_cmd, connection='tsun'):
                self.inc_counter('AT_Command_Blocked')
                return
            self.inc_counter('AT_Command')
            self.forward_at_cmd_resp = True

        elif ftype == self.MB_RTU_CMD:
            if self.remote_stream.mb.recv_req(data[15:],
                                              self.remote_stream.
                                              __forward_msg):
                self.inc_counter('Modbus_Command')
            else:
                logger.error('Invalid Modbus Msg')
                self.inc_counter('Invalid_Msg_Format')
            return

        self.__forward_msg()

    def publish_mqtt(self, key, data):  # pragma: no cover
        asyncio.ensure_future(
            self.mqtt.publish(key, data))

    def get_cmd_rsp_log_lvl(self) -> int:
        ftype = self._recv_buffer[self.header_len]
        if ftype == self.AT_CMD:
            if self.forward_at_cmd_resp:
                return logging.INFO
            return logging.DEBUG
        elif ftype == self.MB_RTU_CMD \
                and self.server_side:
            return self.mb.last_log_lvl

        return logging.WARNING

    def msg_command_rsp(self):
        data = self._recv_buffer[self.header_len:
                                 self.header_len+self.data_len]
        ftype = data[0]
        if ftype == self.AT_CMD:
            if not self.forward_at_cmd_resp:
                data_json = data[14:].decode("utf-8")
                node_id = self.node_id
                key = 'at_resp'
                logger.info(f'{key}: {data_json}')
                self.publish_mqtt(f'{self.entity_prfx}{node_id}{key}', data_json)  # noqa: E501
                return
        elif ftype == self.MB_RTU_CMD:
            self.__modbus_command_rsp(data)
            return
        self.__forward_msg()

    def __modbus_command_rsp(self, data):
        '''precess MODBUS RTU response'''
        valid = data[1]
        modbus_msg_len = self.data_len - 14
        # logger.debug(f'modbus_len:{modbus_msg_len} accepted:{valid}')
        if valid == 1 and modbus_msg_len > 4:
            # logger.info(f'first byte modbus:{data[14]}')
            inv_update = False
            self.modbus_elms = 0
            for key, update, _ in self.mb.recv_resp(self.db, data[14:],
                                                    self.node_id):
                self.modbus_elms += 1
                if update:
                    if key == 'inverter':
                        inv_update = True
                    self._set_mqtt_timestamp(key, self._timestamp())
                    self.new_data[key] = True
            if inv_update:
                self.__build_model_name()

    def msg_hbeat_ind(self):
        data = self._recv_buffer[self.header_len:]
        result = struct.unpack_from('<B', data, 0)
        ftype = result[0]

        self.__forward_msg()
        self.__send_ack_rsp(0x1710, ftype)
        self.new_state_up()

    def msg_sync_end(self):
        data = self._recv_buffer[self.header_len:]
        result = struct.unpack_from(self.HDR_FMT, data, 0)
        ftype = result[0]
        total = result[1]
        self.time_ofs = result[3]

        dt = datetime.fromtimestamp(total + self.time_ofs)
        logger.info(f'ts: {dt.strftime("%Y-%m-%d %H:%M:%S")}')

        self.__forward_msg()
        self.__send_ack_rsp(0x1810, ftype)

    def msg_response(self):
        data = self._recv_buffer[self.header_len:]
        result = struct.unpack_from('<BBLL', data, 0)
        ftype = result[0]  # always 2
        valid = result[1] == 1  # status
        ts = result[2]
        set_hb = result[3]  # always 60 or 120
        logger.debug(f'ftype:{ftype} accepted:{valid}'
                     f' ts:{ts:08x}  nextHeartbeat: {set_hb}s')

        dt = datetime.fromtimestamp(ts)
        logger.debug(f'ts: {dt.strftime("%Y-%m-%d %H:%M:%S")}')
