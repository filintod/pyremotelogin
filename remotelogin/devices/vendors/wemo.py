from remotelogin.devices.base import DeviceBase

__author__ = 'filinto'
"""
Berklin WeMo power switch. WeMos are controlled via WiFi and Plug&Play protocol (soap based). We are using a Miranda-based library
for simple On/Off operations.

This file is based on https://github.com/issackelly/wemo with some modifications

We expect the WiFi on the controller to have a connection to the WeMo network
"""

# TODO: this only implements a single device in an UP&P network


class WeMo(DeviceBase):

    def __init__(self, host, fqdn):
        super(WeMo, self).__init__(host, fqdn)

    def turn_on(self, conn=None):
        """
        Turns on the first switch that it finds.

        BinaryState is set to 'Error' in the case that it was already on.
        """
        resp = self.send_command('SetBinaryState', {'BinaryState': (1, 'Boolean')}, conn)
        tagValue = conn.client.extractSingleTag(resp, 'BinaryState')
        return True if tagValue in ['1', 'Error'] else False

    def turn_off(self, conn=None):
        """
        Turns off the first switch that it finds.

        BinaryState is set to 'Error' in the case that it was already off.
        """
        resp = self.send_command('SetBinaryState', {'BinaryState': (0, 'Boolean')}, conn)
        tagValue = conn.client.extractSingleTag(resp, 'BinaryState')
        return True if tagValue in ['0', 'Error'] else False