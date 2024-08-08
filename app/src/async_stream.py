import asyncio
import logging
import traceback
import time
from asyncio import StreamReader, StreamWriter
from messages import hex_dump_memory, State
from typing import Self
from itertools import count

import gc
logger = logging.getLogger('conn')


class AsyncStream():
    _ids = count(0)
    MAX_PROC_TIME = 2
    '''maximum processing time for a received msg in sec'''
    MAX_START_TIME = 400
    '''maximum time without a received msg in sec'''
    MAX_INV_IDLE_TIME = 120
    '''maximum time without a received msg from the inverter in sec'''
    MAX_DEF_IDLE_TIME = 360
    '''maximum default time without a received msg in sec'''

    def __init__(self, reader: StreamReader, writer: StreamWriter,
                 addr) -> None:
        logger.debug('AsyncStream.__init__')
        self.reader = reader
        self.writer = writer
        self.addr = addr
        self.r_addr = ''
        self.l_addr = ''
        self.conn_no = next(self._ids)
        self.proc_start = None  # start processing start timestamp
        self.proc_max = 0

    def __timeout(self) -> int:
        if self.state == State.init or self.state == State.received:
            to = self.MAX_START_TIME
        elif self.state == State.up and \
                self.server_side and self.modbus_polling:
            to = self.MAX_INV_IDLE_TIME
        else:
            to = self.MAX_DEF_IDLE_TIME
        return to

    async def publish_outstanding_mqtt(self):
        '''Publish all outstanding MQTT topics'''
        try:
            if self.unique_id:
                await self.async_publ_mqtt()
            await self._async_publ_mqtt_proxy_stat('proxy')
        except Exception:
            pass

    async def server_loop(self, addr: str) -> None:
        '''Loop for receiving messages from the inverter (server-side)'''
        logger.info(f'[{self.node_id}:{self.conn_no}] '
                    f'Accept connection from {addr}')
        self.inc_counter('Inverter_Cnt')
        await self.publish_outstanding_mqtt()
        await self.loop()
        self.dec_counter('Inverter_Cnt')
        await self.publish_outstanding_mqtt()
        logger.info(f'[{self.node_id}:{self.conn_no}] Server loop stopped for'
                    f' r{self.r_addr}')

        # if the server connection closes, we also have to disconnect
        # the connection to te TSUN cloud
        if self.remote_stream:
            logger.info(f'[{self.node_id}:{self.conn_no}] disc client '
                        f'connection: [{self.remote_stream.node_id}:'
                        f'{self.remote_stream.conn_no}]')
            await self.remote_stream.disc()

    async def client_loop(self, _: str) -> None:
        '''Loop for receiving messages from the TSUN cloud (client-side)'''
        client_stream = await self.remote_stream.loop()
        logger.info(f'[{client_stream.node_id}:{client_stream.conn_no}] '
                    'Client loop stopped for'
                    f' l{client_stream.l_addr}')

        # if the client connection closes, we don't touch the server
        # connection. Instead we erase the client connection stream,
        # thus on the next received packet from the inverter, we can
        # establish a new connection to the TSUN cloud

        # erase backlink to inverter
        client_stream.remote_stream = None

        if self.remote_stream == client_stream:
            # logging.debug(f'Client l{client_stream.l_addr} refs:'
            #               f' {gc.get_referrers(client_stream)}')
            # than erase client connection
            self.remote_stream = None

    async def loop(self) -> Self:
        """Async loop handler for precessing all received messages"""
        self.r_addr = self.writer.get_extra_info('peername')
        self.l_addr = self.writer.get_extra_info('sockname')
        self.proc_start = time.time()
        while True:
            try:
                proc = time.time() - self.proc_start
                if proc > self.proc_max:
                    self.proc_max = proc
                self.proc_start = None
                dead_conn_to = self.__timeout()
                await asyncio.wait_for(self.__async_read(),
                                       dead_conn_to)

                if self.unique_id:
                    await self.async_write()
                    await self.__async_forward()
                    await self.async_publ_mqtt()

            except asyncio.TimeoutError:
                logger.warning(f'[{self.node_id}:{self.conn_no}] Dead '
                               f'connection timeout ({dead_conn_to}s) '
                               f'for {self.l_addr}')
                await self.disc()
                self.close()
                return self

            except OSError as error:
                logger.error(f'[{self.node_id}:{self.conn_no}] '
                             f'{error} for l{self.l_addr} | '
                             f'r{self.r_addr}')
                await self.disc()
                self.close()
                return self

            except RuntimeError as error:
                logger.info(f'[{self.node_id}:{self.conn_no}] '
                            f'{error} for {self.l_addr}')
                await self.disc()
                self.close()
                return self

            except Exception:
                self.inc_counter('SW_Exception')
                logger.error(
                    f"Exception for {self.addr}:\n"
                    f"{traceback.format_exc()}")

    async def async_write(self, headline: str = 'Transmit to ') -> None:
        """Async write handler to transmit the send_buffer"""
        if self._send_buffer:
            hex_dump_memory(logging.INFO, f'{headline}{self.addr}:',
                            self._send_buffer, len(self._send_buffer))
            self.writer.write(self._send_buffer)
            await self.writer.drain()
            self._send_buffer = bytearray(0)  # self._send_buffer[sent:]

    async def disc(self) -> None:
        """Async disc handler for graceful disconnect"""
        if self.writer.is_closing():
            return
        logger.debug(f'AsyncStream.disc() l{self.l_addr} | r{self.r_addr}')
        self.writer.close()
        await self.writer.wait_closed()

    def close(self) -> None:
        """close handler for a no waiting disconnect

           hint: must be called before releasing the connection instance
        """
        self.reader.feed_eof()          # abort awaited read
        if self.writer.is_closing():
            return
        logger.debug(f'AsyncStream.close() l{self.l_addr} | r{self.r_addr}')
        self.writer.close()

    def healthy(self) -> bool:
        elapsed = 0
        if self.proc_start is not None:
            elapsed = time.time() - self.proc_start
        if self.state == State.closed or elapsed > self.MAX_PROC_TIME:
            logging.debug(f'[{self.node_id}:{self.conn_no}:'
                          f'{type(self).__name__}]'
                          f' act:{round(1000*elapsed)}ms'
                          f' max:{round(1000*self.proc_max)}ms')
            logging.debug(f'Healthy()) refs: {gc.get_referrers(self)}')
        return elapsed < 5

    '''
    Our private methods
    '''
    async def __async_read(self) -> None:
        """Async read handler to read received data from TCP stream"""
        data = await self.reader.read(4096)
        if data:
            self.proc_start = time.time()
            self._recv_buffer += data
            wait = self.read()                # call read in parent class
            if wait > 0:
                await asyncio.sleep(wait)
        else:
            raise RuntimeError("Peer closed.")

    async def __async_forward(self) -> None:
        """forward handler transmits data over the remote connection"""
        if not self._forward_buffer:
            return
        try:
            if not self.remote_stream:
                await self.async_create_remote()
                if self.remote_stream:
                    if self.remote_stream._init_new_client_conn():
                        await self.remote_stream.async_write()

            if self.remote_stream:
                self.remote_stream._update_header(self._forward_buffer)
                hex_dump_memory(logging.INFO,
                                f'Forward to {self.remote_stream.addr}:',
                                self._forward_buffer,
                                len(self._forward_buffer))
                self.remote_stream.writer.write(self._forward_buffer)
                await self.remote_stream.writer.drain()
                self._forward_buffer = bytearray(0)

        except OSError as error:
            if self.remote_stream:
                rmt = self.remote_stream
                self.remote_stream = None
                logger.error(f'[{rmt.node_id}:{rmt.conn_no}] Fwd: {error} for '
                             f'l{rmt.l_addr} | r{rmt.r_addr}')
                await rmt.disc()
                rmt.close()

        except RuntimeError as error:
            if self.remote_stream:
                rmt = self.remote_stream
                self.remote_stream = None
                logger.info(f'[{rmt.node_id}:{rmt.conn_no}] '
                            f'Fwd: {error} for {rmt.l_addr}')
                await rmt.disc()
                rmt.close()

        except Exception:
            self.inc_counter('SW_Exception')
            logger.error(
                f"Fwd Exception for {self.addr}:\n"
                f"{traceback.format_exc()}")

    def __del__(self):
        logger.debug(
            f"AsyncStream.__del__  l{self.l_addr} | r{self.r_addr}")
