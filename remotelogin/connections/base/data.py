import time
import datetime
import io

from remotelogin.connections import settings

control = """SOH	Start of heading, console interrupt
STX	Start of text
ETX	End of text
CTRL+C	Control C
ENQ Enquiry
ACK	Acknowledgement
BEL	Bell
BS	Backspace
TAB	Tab
HT	Horizontal tab
LF	Line feed
NL	New line
VT	Vertical tab
FF	Form feed
CR	Carriage return
SO	Shift-out, begin alternate character set
SI	Shift-in, resume default character set
DLE	Data-link escape
DC1	XON, for flow control
DC2	Device control 2, block-mode flow control
DC3	XOFF, for flow control
DC4	Device control 4
NAK	Negative acknowledgement
SYN	Synchronous idle
ETB	End transmission block
CAN	Cancel
EM	End of medium
SUB	Substitute
ESC	Escape
FS	File separator
GS	Group separator
RS	Record separator, block-mode terminator
US	Unit separator
SP	Space
DEL	Delete"""

control_list = [v.split(maxsplit=1)[1] for v in control.splitlines()]


class DataExchange:

    def __init__(self, unbuffered=False):
        self._data_sent_timer_meta = []
        self._data_sent = []
        self._data_recv = []
        self._recording = True
        self._duplicate_on = False
        self._new_received = self.new_received
        self._unbuffered = unbuffered

    def _write(self, stream, data, force=False):
        if self._recording or force:
            stream.write(data)
            if self._unbuffered:
                stream.flush()

    def new_sent(self, data, metadata=None, data_stream=None, record=True,  title='',
                 send_msg_format='\n>>> sending "{title}" >>>{data}', echo_off=False, hide=False):
        if record:
            self._data_sent_timer_meta.append((time.time(), metadata))
            self._data_sent.append(data if not hide else settings.HIDDEN_DATA_MSG)
            self._stream_is_text = False
            self.new_received = self._new_received

            if data_stream and data:

                if isinstance(data_stream, io.TextIOBase):  # checks for StringIO and Text Files
                    stream_is_text = True
                else:
                    stream_is_text = False
                    self.new_received = self.new_received_bytes

                is_ctrl = False

                if data != '\n' and len(data) == 1 and ord(data) < 36:
                    data = control_list[ord(data)]
                    is_ctrl = True

                if echo_off or is_ctrl:
                    send_msg_format = send_msg_format.format(title=title, data=data)
                    if not stream_is_text:
                        send_msg_format = send_msg_format.encode(encoding=settings.ENCODE_ENCODING_TYPE,
                                                                 errors=settings.ENCODE_ERROR_ARGUMENT_VALUE)
                    self._write(data_stream, send_msg_format, True)
            self._data_recv.append(data_stream or io.StringIO())

        self._recording = record

    def new_received(self, data):
        self._write(self._data_recv[-1], data)

    def new_received_bytes(self, data):
        self._write(self._data_recv[-1], data.encode(encoding=settings.ENCODE_ENCODING_TYPE,
                                                     errors=settings.ENCODE_ERROR_ARGUMENT_VALUE))

    def get_last_recv(self):
        try:
            return self._data_recv[-1].getvalue()
        except (ValueError, AttributeError):
            return 'A stream was recorded for this command'
        except IndexError:
            return 'Nothing was recorded (nothing sent/received)'

    def get_conversation_list(self, with_sent_time=False):
        conversation = []
        for i, s in enumerate(self._data_sent):
            try:
                send_recv = (s, self._data_recv[i].getvalue())
            except (ValueError, AttributeError):
                send_recv = (s, 'a stream was recorded for this command')

            if with_sent_time:
                send_recv += self._data_sent_timer_meta[i]
            conversation.append(send_recv)
        return conversation

    def get_timed_conversation_list(self, time_format='%Y-%m-%d %H:%M:%S'):
        conversation = self.get_conversation_list(True)
        timed_conversation = []
        for exchange in conversation:
            sent, received, ts, meta = exchange
            timed_conversation.append(dict(time=datetime.datetime.fromtimestamp(ts).strftime(time_format),
                                           meta=meta or '',
                                           sent=sent,
                                           received=received))
        return timed_conversation

    def flush(self):
        self._data_sent_timer_meta = []
        self._data_sent = []
        self._data_recv = []
