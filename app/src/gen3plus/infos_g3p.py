
from typing import Generator
from itertools import chain

from infos import Infos, Register, ProxyMode, Fmt


class RegisterFunc:
    @staticmethod
    def prod_sum(info: Infos, arr: dict) -> None | int:
        result = 0
        for sum in arr:
            prod = 1
            for factor in sum:
                val = info.get_db_value(factor)
                if val is None:
                    return None
                prod = prod * val
            result += prod
        return result

    @staticmethod
    def cmp_values(info: Infos, params: map) -> None | int:
        try:
            val = info.get_db_value(params['reg'])
            if val < params['cmp_val']:
                return params['res'][0]
            if val == params['cmp_val']:
                return params['res'][1]
            return params['res'][2]
        except Exception:
            pass
        return None


class RegisterMap:
    # make the class read/only by using __slots__
    __slots__ = ()

    FMT_2_16BIT_VAL = '!HH'
    FMT_3_16BIT_VAL = '!HHH'
    FMT_4_16BIT_VAL = '!HHHH'

    map = {
        # 0x41020007: {'reg': Register.DEVICE_SNR,           'fmt': '<L'},                 # noqa: E501
        0x41020018: {'reg': Register.DATA_UP_INTERVAL,     'fmt': '<B', 'ratio':    60, 'dep': ProxyMode.SERVER},  # noqa: E501
        0x41020019: {'reg': Register.COLLECT_INTERVAL,     'fmt': '<B', 'quotient': 60, 'dep': ProxyMode.SERVER},  # noqa: E501
        0x4102001a: {'reg': Register.HEARTBEAT_INTERVAL,   'fmt': '<B', 'ratio':    1},  # noqa: E501
        0x4102001b: {'reg': None,                          'fmt': '<B', 'const':    1},  # noqa: E501 Max No Of Connected Devices
        0x4102001c: {'reg': Register.SIGNAL_STRENGTH,      'fmt': '<B', 'ratio':    1, 'dep': ProxyMode.SERVER},  # noqa: E501
        0x4102001d: {'reg': None,                          'fmt': '<B', 'const':    1},  # noqa: E501
        0x4102001e: {'reg': Register.CHIP_MODEL,           'fmt': '!40s'},               # noqa: E501
        0x41020046: {'reg': Register.MAC_ADDR,             'fmt': '!6B', 'func': Fmt.mac},  # noqa: E501
        0x4102004c: {'reg': Register.IP_ADDRESS,           'fmt': '!16s'},               # noqa: E501
        0x4102005c: {'reg': None,                          'fmt': '<B', 'const':   15},  # noqa: E501
        0x4102005e: {'reg': None,                          'fmt': '<B', 'const':    1},  # noqa: E501 No Of Sensors (ListLen)
        0x4102005f: {'reg': Register.SENSOR_LIST,          'fmt': '<H', 'func': Fmt.hex4},   # noqa: E501
        0x41020061: {'reg': None,                          'fmt': '<HB', 'const':  (15, 255)},  # noqa: E501
        0x41020064: {'reg': Register.COLLECTOR_FW_VERSION, 'fmt': '!40s'},               # noqa: E501
        0x4102008c: {'reg': None,                          'fmt': '<BB', 'const':  (254, 254)},  # noqa: E501
        0x4102008e: {'reg': None,                          'fmt': '<B'},                 # noqa: E501 Encryption Certificate File Status
        0x4102008f: {'reg': None,                          'fmt': '!40s'},               # noqa: E501
        0x410200b7: {'reg': Register.SSID,                 'fmt': '!40s'},               # noqa: E501
    }
    map_02b0 = {
        0x4201000c: {'reg': Register.SENSOR_LIST,          'fmt': '<H', 'func': Fmt.hex4},   # noqa: E501
        0x4201001c: {'reg': Register.POWER_ON_TIME,        'fmt': '<H', 'ratio':    1, 'dep': ProxyMode.SERVER},  # noqa: E501, or packet number
        0x42010020: {'reg': Register.SERIAL_NUMBER,        'fmt': '!16s'},               # noqa: E501

        # Start MODBUS Block: 0x3000 (R/O Measurements)
        0x420100c0: {'reg': Register.INVERTER_STATUS,      'fmt': '!H'},                 # noqa: E501
        0x420100c2: {'reg': Register.DETECT_STATUS_1,      'fmt': '!H'},                 # noqa: E501
        0x420100c4: {'reg': Register.DETECT_STATUS_2,      'fmt': '!H'},                 # noqa: E501
        0x420100c6: {'reg': Register.EVENT_ALARM,          'fmt': '!H'},                 # noqa: E501
        0x420100c8: {'reg': Register.EVENT_FAULT,          'fmt': '!H'},                 # noqa: E501
        0x420100ca: {'reg': Register.EVENT_BF1,            'fmt': '!H'},                 # noqa: E501
        0x420100cc: {'reg': Register.EVENT_BF2,            'fmt': '!H'},                 # noqa: E501
        # 0x420100ce
        0x420100d0: {'reg': Register.VERSION,              'fmt': '!H', 'func': Fmt.version},  # noqa: E501
        0x420100d2: {'reg': Register.GRID_VOLTAGE,         'fmt': '!H', 'ratio':  0.1},  # noqa: E501
        0x420100d4: {'reg': Register.GRID_CURRENT,         'fmt': '!H', 'ratio': 0.01},  # noqa: E501
        0x420100d6: {'reg': Register.GRID_FREQUENCY,       'fmt': '!H', 'ratio': 0.01},  # noqa: E501
        0x420100d8: {'reg': Register.INVERTER_TEMP,        'fmt': '!H', 'offset': -40},  # noqa: E501
        # 0x420100da
        0x420100dc: {'reg': Register.RATED_POWER,          'fmt': '!H', 'ratio':    1},  # noqa: E501
        0x420100de: {'reg': Register.OUTPUT_POWER,         'fmt': '!H', 'ratio':  0.1},  # noqa: E501
        0x420100e0: {'reg': Register.PV1_VOLTAGE,          'fmt': '!H', 'ratio':  0.1},  # noqa: E501
        0x420100e2: {'reg': Register.PV1_CURRENT,          'fmt': '!H', 'ratio': 0.01},  # noqa: E501
        0x420100e4: {'reg': Register.PV1_POWER,            'fmt': '!H', 'ratio':  0.1},  # noqa: E501
        0x420100e6: {'reg': Register.PV2_VOLTAGE,          'fmt': '!H', 'ratio':  0.1},  # noqa: E501
        0x420100e8: {'reg': Register.PV2_CURRENT,          'fmt': '!H', 'ratio': 0.01},  # noqa: E501
        0x420100ea: {'reg': Register.PV2_POWER,            'fmt': '!H', 'ratio':  0.1},  # noqa: E501
        0x420100ec: {'reg': Register.PV3_VOLTAGE,          'fmt': '!H', 'ratio':  0.1},  # noqa: E501
        0x420100ee: {'reg': Register.PV3_CURRENT,          'fmt': '!H', 'ratio': 0.01},  # noqa: E501
        0x420100f0: {'reg': Register.PV3_POWER,            'fmt': '!H', 'ratio':  0.1},  # noqa: E501
        0x420100f2: {'reg': Register.PV4_VOLTAGE,          'fmt': '!H', 'ratio':  0.1},  # noqa: E501
        0x420100f4: {'reg': Register.PV4_CURRENT,          'fmt': '!H', 'ratio': 0.01},  # noqa: E501
        0x420100f6: {'reg': Register.PV4_POWER,            'fmt': '!H', 'ratio':  0.1},  # noqa: E501
        0x420100f8: {'reg': Register.DAILY_GENERATION,     'fmt': '!H', 'ratio': 0.01},  # noqa: E501
        0x420100fa: {'reg': Register.TOTAL_GENERATION,     'fmt': '!L', 'ratio': 0.01},  # noqa: E501
        0x420100fe: {'reg': Register.PV1_DAILY_GENERATION, 'fmt': '!H', 'ratio': 0.01},  # noqa: E501
        0x42010100: {'reg': Register.PV1_TOTAL_GENERATION, 'fmt': '!L', 'ratio': 0.01},  # noqa: E501
        0x42010104: {'reg': Register.PV2_DAILY_GENERATION, 'fmt': '!H', 'ratio': 0.01},  # noqa: E501
        0x42010106: {'reg': Register.PV2_TOTAL_GENERATION, 'fmt': '!L', 'ratio': 0.01},  # noqa: E501
        0x4201010a: {'reg': Register.PV3_DAILY_GENERATION, 'fmt': '!H', 'ratio': 0.01},  # noqa: E501
        0x4201010c: {'reg': Register.PV3_TOTAL_GENERATION, 'fmt': '!L', 'ratio': 0.01},  # noqa: E501
        0x42010110: {'reg': Register.PV4_DAILY_GENERATION, 'fmt': '!H', 'ratio': 0.01},  # noqa: E501
        0x42010112: {'reg': Register.PV4_TOTAL_GENERATION, 'fmt': '!L', 'ratio': 0.01},  # noqa: E501
        0x42010116: {'reg': Register.INV_UNKNOWN_1,        'fmt': '!H'},                 # noqa: E501

        # Start MODBUS Block: 0x2000 (R/W Config Paramaneters)
        0x42010118: {'reg': Register.BOOT_STATUS,          'fmt': '!H'},
        0x4201011a: {'reg': Register.DSP_STATUS,           'fmt': '!H'},
        0x4201011c: {'reg': None,                          'fmt': '!H', 'const':    1},  # noqa: E501
        0x4201011e: {'reg': Register.WORK_MODE,            'fmt': '!H'},
        0x42010124: {'reg': Register.OUTPUT_SHUTDOWN,      'fmt': '!H'},
        0x42010126: {'reg': Register.MAX_DESIGNED_POWER,   'fmt': '!H'},
        0x42010128: {'reg': Register.RATED_LEVEL,          'fmt': '!H'},
        0x4201012a: {'reg': Register.INPUT_COEFFICIENT,    'fmt': '!H', 'ratio':  100/1024},  # noqa: E501
        0x4201012c: {'reg': Register.GRID_VOLT_CAL_COEF,   'fmt': '!H'},
        0x4201012e: {'reg': None,                          'fmt': '!H', 'const':   1024},  # noqa: E501
        0x42010130: {'reg': None,                          'fmt': FMT_4_16BIT_VAL, 'const': (1024, 1, 0xffff, 1)},  # noqa: E501
        0x42010138: {'reg': Register.PROD_COMPL_TYPE,      'fmt': '!H'},
        0x4201013a: {'reg': None,                          'fmt': FMT_3_16BIT_VAL, 'const': (0x68, 0x68, 0x500)},  # noqa: E501
        0x42010140: {'reg': None,                          'fmt': FMT_4_16BIT_VAL, 'const': (0x9cd, 0x7b6, 0x139c, 0x1324)},  # noqa: E501
        0x42010148: {'reg': None,                          'fmt': FMT_4_16BIT_VAL, 'const': (1, 0x7ae, 0x40f, 0x41)},  # noqa: E501
        0x42010150: {'reg': None,                          'fmt': FMT_4_16BIT_VAL, 'const': (0xf, 0xa64, 0xa64, 0x6)},  # noqa: E501
        0x42010158: {'reg': None,                          'fmt': FMT_4_16BIT_VAL, 'const': (0x6, 0x9f6, 0x128c, 0x128c)},  # noqa: E501
        0x42010160: {'reg': None,                          'fmt': FMT_4_16BIT_VAL, 'const': (0x10, 0x10, 0x1452, 0x1452)},  # noqa: E501
        0x42010168: {'reg': None,                          'fmt': FMT_4_16BIT_VAL, 'const': (0x10, 0x10, 0x151, 0x5)},  # noqa: E501
        0x42010170: {'reg': Register.OUTPUT_COEFFICIENT,   'fmt': '!H', 'ratio':  100/1024},  # noqa: E501
        0x42010172: {'reg': None,                          'fmt': FMT_3_16BIT_VAL, 'const':  (0x1, 0x139c, 0xfa0)},  # noqa: E501
        0x42010178: {'reg': None,                          'fmt': FMT_4_16BIT_VAL, 'const': (0x4e, 0x66, 0x3e8, 0x400)},  # noqa: E501
        0x42010180: {'reg': None,                          'fmt': FMT_4_16BIT_VAL, 'const': (0x9ce, 0x7a8, 0x139c, 0x1326)},  # noqa: E501
        0x42010188: {'reg': None,                          'fmt': FMT_4_16BIT_VAL, 'const': (0x0, 0x0, 0x0, 0)},  # noqa: E501
        0x42010190: {'reg': None,                          'fmt': FMT_4_16BIT_VAL, 'const': (0x0, 0x0, 1024, 1024)},  # noqa: E501
        0x42010198: {'reg': None,                          'fmt': FMT_4_16BIT_VAL, 'const': (0, 0, 0xffff, 0)},  # noqa: E501
        0x420101a0: {'reg': None,                          'fmt': FMT_2_16BIT_VAL, 'const': (0x0, 0x0)},  # noqa: E501

        0xffffff02: {'reg': Register.POLLING_INTERVAL},
        # 0x4281001c: {'reg': Register.POWER_ON_TIME,        'fmt': '<H', 'ratio':    1},  # noqa: E501
    }
    map_3026 = {
        0x4201000c: {'reg': Register.SENSOR_LIST,          'fmt': '<H', 'func': Fmt.hex4},   # noqa: E501
        0x4201001c: {'reg': Register.POWER_ON_TIME,        'fmt': '<H', 'ratio':    1, 'dep': ProxyMode.SERVER},  # noqa: E501, or packet number
        0x42010020: {'reg': Register.SERIAL_NUMBER,        'fmt': '!16s'},               # noqa: E501
        0x42010030: {'reg': Register.BATT_PV1_VOLT,        'fmt': '!H', 'ratio': 0.01},  # noqa: E501, DC Voltage PV1
        0x42010032: {'reg': Register.BATT_PV1_CUR,         'fmt': '!H', 'ratio': 0.01},  # noqa: E501, DC Current PV1
        0x42010034: {'reg': Register.BATT_PV2_VOLT,        'fmt': '!H', 'ratio': 0.01},  # noqa: E501, DC Voltage PV2
        0x42010036: {'reg': Register.BATT_PV2_CUR,         'fmt': '!H', 'ratio': 0.01},  # noqa: E501, DC Current PV2
        0x42010038: {'reg': Register.BATT_TOTAL_CHARG,     'fmt': '!L', 'ratio': 0.01},  # noqa: E501
        0x4201003c: {'reg': Register.BATT_PV1_STATUS,      'fmt': '!H'},                 # noqa: E501 MPTT-1 Operating Status: 0(Standby), 1(Work)
        0x4201003e: {'reg': Register.BATT_PV2_STATUS,      'fmt': '!H'},                 # noqa: E501 MPTT-2 Operating Status: 0(Standby), 1(Work)
        0x42010040: {'reg': Register.BATT_VOLT,            'fmt': '!h', 'ratio': 0.01},  # noqa: E501
        0x42010042: {'reg': Register.BATT_CUR,             'fmt': '!h', 'ratio': 0.01},  # noqa: E501 => Batterie Status: <0(Discharging), 0(Static), 0>(Loading)
        0x42010044: {'reg': Register.BATT_SOC,             'fmt': '!H', 'ratio': 0.01},  # noqa: E501, state of charge (SOC) in percent
        0x42010046: {'reg': Register.BATT_CELL1_VOLT,      'fmt': '!H', 'ratio': 0.001},  # noqa: E501
        0x42010048: {'reg': Register.BATT_CELL2_VOLT,      'fmt': '!H', 'ratio': 0.001},  # noqa: E501
        0x4201004a: {'reg': Register.BATT_CELL3_VOLT,      'fmt': '!H', 'ratio': 0.001},  # noqa: E501
        0x4201004c: {'reg': Register.BATT_CELL4_VOLT,      'fmt': '!H', 'ratio': 0.001},  # noqa: E501
        0x4201004e: {'reg': Register.BATT_CELL5_VOLT,      'fmt': '!H', 'ratio': 0.001},  # noqa: E501
        0x42010050: {'reg': Register.BATT_CELL6_VOLT,      'fmt': '!H', 'ratio': 0.001},  # noqa: E501
        0x42010052: {'reg': Register.BATT_CELL7_VOLT,      'fmt': '!H', 'ratio': 0.001},  # noqa: E501
        0x42010054: {'reg': Register.BATT_CELL8_VOLT,      'fmt': '!H', 'ratio': 0.001},  # noqa: E501
        0x42010056: {'reg': Register.BATT_CELL9_VOLT,      'fmt': '!H', 'ratio': 0.001},  # noqa: E501
        0x42010058: {'reg': Register.BATT_CELL10_VOLT,     'fmt': '!H', 'ratio': 0.001},  # noqa: E501
        0x4201005a: {'reg': Register.BATT_CELL11_VOLT,     'fmt': '!H', 'ratio': 0.001},  # noqa: E501
        0x4201005c: {'reg': Register.BATT_CELL12_VOLT,     'fmt': '!H', 'ratio': 0.001},  # noqa: E501
        0x4201005e: {'reg': Register.BATT_CELL13_VOLT,     'fmt': '!H', 'ratio': 0.001},  # noqa: E501
        0x42010060: {'reg': Register.BATT_CELL14_VOLT,     'fmt': '!H', 'ratio': 0.001},  # noqa: E501
        0x42010062: {'reg': Register.BATT_CELL15_VOLT,     'fmt': '!H', 'ratio': 0.001},  # noqa: E501
        0x42010064: {'reg': Register.BATT_CELL16_VOLT,     'fmt': '!H', 'ratio': 0.001},  # noqa: E501H
        0x42010066: {'reg': Register.BATT_TEMP_1,          'fmt': '!h'},                 # noqa: E501 Cell Temperture 1
        0x42010068: {'reg': Register.BATT_TEMP_2,          'fmt': '!h'},                 # noqa: E501 Cell Temperture 2
        0x4201006a: {'reg': Register.BATT_TEMP_3,          'fmt': '!h'},                 # noqa: E501 Cell Temperture 3
        0x4201006c: {'reg': Register.BATT_OUT_VOLT,        'fmt': '!H', 'ratio': 0.01},  # noqa: E501 Output Voltage
        0x4201006e: {'reg': Register.BATT_OUT_CUR,         'fmt': '!H', 'ratio': 0.01},  # noqa: E501 Output Current
        0x42010070: {'reg': Register.BATT_OUT_STATUS,      'fmt': '!H'},                 # noqa: E501 Output Working Status: 0(Standby), 1(Work)
        0x42010072: {'reg': Register.BATT_TEMP_4,          'fmt': '!h'},                 # noqa: E50, Environment temp
        0x42010074: {'reg': Register.BATT_ALARM,           'fmt': '!H'},                 # noqa: E501 Warning Alarmcode 1, Bit 0..15
        0x42010076: {'reg': Register.BATT_HW_VERS,         'fmt': '!h'},                 # noqa: E501 hardware version
        0x42010078: {'reg': Register.BATT_SW_VERS,         'fmt': '!h'},                 # noqa: E501 software main version
        'calc': {
            1: {'reg': Register.BATT_PV_PWR,               'func': RegisterFunc.prod_sum,    # noqa: E501 Generated Power
                'params': [[Register.BATT_PV1_VOLT, Register.BATT_PV1_CUR],
                           [Register.BATT_PV2_VOLT, Register.BATT_PV2_CUR]]},
            2: {'reg': Register.BATT_PWR,                  'func': RegisterFunc.prod_sum,    # noqa: E501
                'params': [[Register.BATT_VOLT, Register.BATT_CUR]]},
            3: {'reg': Register.BATT_OUT_PWR,              'func': RegisterFunc.prod_sum,    # noqa: E501 Supply Power => Power Supply State: 0(Idle), 0>(Power Supply)
                'params': [[Register.BATT_OUT_VOLT, Register.BATT_OUT_CUR]]},
            4: {'reg': Register.BATT_PWR_SUPL_STATE,       'func': RegisterFunc.cmp_values,  # noqa: E501
                'params': {'reg': Register.BATT_OUT_PWR, 'cmp_val': 0, 'res': [0, 0, 1]}},   # noqa: E501
            5: {'reg': Register.BATT_STATUS,               'func': RegisterFunc.cmp_values,  # noqa: E501
                'params': {'reg': Register.BATT_CUR,     'cmp_val': 0.0, 'res': [0, 1, 2]}}  # noqa: E501
        }
    }


class RegisterSel:
    __sensor_map = {
            0x02b0: RegisterMap.map_02b0,
            0x3026: RegisterMap.map_3026,
    }

    @classmethod
    def get(cls, sensor: int):
        return cls.__sensor_map.get(sensor, RegisterMap.map)


class InfosG3P(Infos):
    __slots__ = ('client_mode', )

    def __init__(self, client_mode: bool):
        super().__init__()
        self.client_mode = client_mode
        self.set_db_def_value(Register.MANUFACTURER, 'TSUN')
        self.set_db_def_value(Register.EQUIPMENT_MODEL, 'TSOL-MSxx00')
        self.set_db_def_value(Register.CHIP_TYPE, 'IGEN TECH')
        self.set_db_def_value(Register.NO_INPUTS, 4)

    def __hide_topic(self, row: dict) -> bool:
        if 'dep' in row:
            mode = row['dep']
            if self.client_mode:
                return mode != ProxyMode.CLIENT
            else:
                return mode != ProxyMode.SERVER
        return False

    def ha_confs(self, ha_prfx: str, node_id: str, snr: str,
                 sug_area: str = '') \
            -> Generator[tuple[dict, str], None, None]:
        '''Generator function yields a json register struct for home-assistant
        auto configuration and a unique entity string

        arguments:
        prfx:str     ==> MQTT prefix for the home assistant 'stat_t string
        snr:str      ==> serial number of the inverter, used to build unique
                         entity strings
        sug_area:str ==> suggested area string from the config file'''
        # iterate over RegisterMap.map and get the register values
        sensor = self.get_db_value(Register.SENSOR_LIST)
        if "3026" == sensor:
            reg_map = RegisterMap.map_3026
        elif "02b0" == sensor:
            reg_map = RegisterMap.map_02b0
        else:
            reg_map = {}
        items = reg_map.items()
        if 'calc' in reg_map:
            virt = reg_map['calc'].items()
        else:
            virt = {}

        for idx, row in chain(RegisterMap.map.items(), items, virt):
            if 'calc' == idx:
                continue
            info_id = row['reg']
            if self.__hide_topic(row):
                res = self.ha_remove(info_id, node_id, snr)  # noqa: E501
            else:
                res = self.ha_conf(info_id, ha_prfx, node_id, snr, False, sug_area)  # noqa: E501
            if res:
                yield res

    def parse(self, buf, msg_type: int, rcv_ftype: int,
              sensor: int = 0, node_id: str = '') \
            -> Generator[tuple[str, bool], None, None]:
        '''parse a data sequence received from the inverter and
        stores the values in Infos.db

        buf: buffer of the sequence to parse'''
        reg_map = RegisterSel.get(sensor)
        for idx, row in reg_map.items():
            if 'calc' == idx:
                continue
            addr = idx & 0xffff
            ftype = (idx >> 16) & 0xff
            mtype = (idx >> 24) & 0xff
            if ftype != rcv_ftype or mtype != msg_type:
                continue
            if not isinstance(row, dict):
                continue
            info_id = row['reg']
            result = Fmt.get_value(buf, addr, row)
            yield from self.__update_val(node_id, "GEN3PLUS", info_id, result)
        yield from self.calc(sensor, node_id)

    def calc(self, sensor: int = 0, node_id: str = '') \
            -> Generator[tuple[str, bool], None, None]:
        '''calculate meta values from the
        stored values in Infos.db

        sensor: sensor_list number
        node_id: id-string for the node'''

        reg_map = RegisterSel.get(sensor)
        if 'calc' in reg_map:
            for row in reg_map['calc'].values():
                info_id = row['reg']
                result = row['func'](self, row['params'])
                yield from self.__update_val(node_id, "CALC", info_id, result)

    def __update_val(self, node_id, source: str, info_id, result):
        keys, level, unit, must_incr = self._key_obj(info_id)
        if keys:
            name, update = self.update_db(keys, must_incr, result)
            yield keys[0], update
            if update:
                self.tracer.log(level, f'[{node_id}] {source}: {name}'
                                       f' : {result}{unit}')

    def build(self, len, msg_type: int, rcv_ftype: int, sensor: int = 0):
        buf = bytearray(len)
        for idx, row in RegisterSel.get(sensor).items():
            addr = idx & 0xffff
            ftype = (idx >> 16) & 0xff
            mtype = (idx >> 24) & 0xff
            if ftype != rcv_ftype or mtype != msg_type:
                continue
            if not isinstance(row, dict):
                continue
            if 'const' in row:
                val = row['const']
            else:
                info_id = row['reg']
                val = self.get_db_value(info_id)
            if not val:
                continue
            Fmt.set_value(buf, addr, row, val)
        return buf
