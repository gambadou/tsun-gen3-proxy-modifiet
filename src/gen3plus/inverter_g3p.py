from asyncio import StreamReader, StreamWriter

from inverter_base import InverterBase
from gen3plus.solarman_v5 import SolarmanV5
from gen3plus.solarman_emu import SolarmanEmu


class InverterG3P(InverterBase):
    def __init__(self, reader: StreamReader, writer: StreamWriter,
                 client_mode: bool = False):
        # shared value between both inverter connections
        self.forward_at_cmd_resp = False
        '''Flag if response for the last at command must be send to the cloud.

           False: send result only to the MQTT broker, cause the AT+ command
                  came from there
           True: send response packet to the cloud, cause the AT+ command
                 came from the cloud'''

        remote_prot = None
        if client_mode:
            remote_prot = SolarmanEmu
        super().__init__(reader, writer, 'solarman',
                         SolarmanV5, client_mode, remote_prot)
