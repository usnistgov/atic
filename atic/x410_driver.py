"""
Driver class for the USRP X410. Similar to the RohdeScharzSMW200A driver class
used by the p2p interference testbed.
"""

__author__ = "jlb20"

import socket
from time import sleep


class UsrpX410:
    """
    Class for USRP X410 .wv file playback

    Requires setup on X410, seen here on this repository https://github.com/jordanbe-nist/uhd-wv-playback
    """

    def __init__(self, usrp_ip_addr="10.0.0.47", freq=2.4e6, rf_power=-40):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((usrp_ip_addr, 9999))  # TODO consider port as variable

        self.rf_output_power = rf_power
        self.center_freq = freq
        self.wv_file = None

    @property
    def center_freq(self):
        """Getter for center frequency

        Returns:
            float: center frequency in Hz
        """
        self.sock.sendall(bytes("freq=?\n", "utf-8"))
        self._center_freq = float(str(self.sock.recv(1024), "utf-8"))
        return self._center_freq

    @center_freq.setter
    def center_freq(self, frequency):
        """Setter for center frequency of the wv file playback

        Args:
            frequency (float): Frequency to set playback at
        Returns:
            None.
        """
        self._center_freq = frequency
        self.sock.sendall(bytes(f"freq={frequency}\n", "utf-8"))
        # TODO if _center_frequency != frequency: warn
        self._center_freq = float(str(self.sock.recv(1024), "utf-8"))

    @property
    def rf_output_power(self):
        """Getter for"""
        self.sock.sendall(bytes("power=?\n", "utf-8"))
        self._rf_power = float(str(self.sock.recv(1024), "utf-8"))
        return self._rf_power

    @rf_output_power.setter
    def rf_output_power(self, power):
        self._rf_power = power
        self.sock.sendall(bytes(f"power={power}\n", "utf-8"))
        # TODO if received power != sent power: warn or whatever
        self._rf_power = float(str(self.sock.recv(1024), "utf-8"))

    # TODO add class methods for peak power (PEP), requires math on x410

    @property
    def playback_wv_file(self):
        self.sock.sendall(bytes("wv_file=?\n", "utf-8"))
        self._wv_file = str(self.sock.recv(1024), "utf-8")
        return self._wv_file

    @playback_wv_file.setter
    def playback_wv_file(self, wv_file):
        self.sock.sendall(bytes(f"wv_file={wv_file}\n", "utf-8"))
        # TODO handle bad file
        self._wv_file = str(self.sock.recv(1024), "utf-8")

    def start_wv(self, duty=None):
        if duty is None:
            self.sock.sendall(bytes("start\n", "utf-8"))
        else:
             self.sock.sendall(bytes(f"start duty={duty}\n", "utf-8"))
        print(str(self.sock.recv(1024), "utf-8"))

    def stop_wv(self):
        self.sock.sendall(bytes("stop\n", "utf-8"))
        print(str(self.sock.recv(1024), "utf-8"))

    def query_rf(self):
        self.sock.sendall(bytes("rf out?\n", "utf-8"))
        recv = str(self.sock.recv(1024), "utf-8")
        if recv == "True":
            return True
        elif recv == "False":
            return False
        else:
            raise ValueError

    def get_temp(self):
        self.sock.sendall(bytes("temp=?\n", "utf-8"))
        return str(self.sock.recv(1024), "utf-8")

    def __del__(self):
        # TODO: consider check on this
        self.stop_wv()


if __name__ == "__main__":
    usrp = UsrpX410(usrp_ip_addr="10.0.0.47", freq=2.4e9, rf_power=-30)

    print("test getters")
    print("temp=", usrp.get_temp())
    print("fc=", usrp.center_freq)
    print("power=", usrp.rf_output_power)
    print("file=", usrp.playback_wv_file)

    print("test setters")
    usrp.center_freq = 6.02e9
    usrp.rf_output_power = -40
    usrp.playback_wv_file = "/data/wv_files/whiteNoise122mhz.wv"

    print("temp=", usrp.get_temp())
    print("fc=", usrp.center_freq)
    print("power=", usrp.rf_output_power)
    print("file=", usrp.playback_wv_file)

    usrp.start_wv()
    for i in range(-3, 5, 1):
        usrp.rf_output_power = i
        print("temp=", usrp.get_temp())
        print("rf playback check:", usrp.query_rf())
        sleep(60)
        usrp.stop_wv()
        print("rf playback check:", usrp.query_rf())
        sleep(3)
        usrp.start_wv()
    usrp.stop_wv()
