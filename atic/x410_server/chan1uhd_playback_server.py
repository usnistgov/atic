import socketserver
import socket
import time
from uhd_play_wv import read_wv_file
import uhd
from pathlib import Path
import threading
import logging
from subprocess import run


def play_wv(event, buff_addr, buff_size, usrp_obj):
    replay_block = usrp_obj["replay"]
    time_spec = uhd.libpyuhd.types.time_spec(0)
    replay_block.play(buff_addr, buff_size, 0, time_spec, True)
    event.wait()
    replay_block.stop(0)

def load_wv(iq, usrp_obj):
    replay_block = usrp_obj["replay"]
    tx_stream = usrp_obj["stream"]
    data_len = iq.shape[-1]
    sample_size = 4  # Complex signed 16-bit is 32 bits per sample
    replay_buff_addr = 0
    replay_buff_size = data_len * sample_size
    replay_word_size = replay_block.get_word_size()
    if replay_buff_size % replay_word_size != 0:
        replay_buff_size = replay_buff_size - (replay_buff_size % replay_word_size)
    replay_block.record(replay_buff_addr, replay_buff_size, 0)
    # Send iq data to replay block via tx stream
    tx_metadata = uhd.types.TXMetadata()
    # replay_buff_addr, replay_buff_size, replay_chan, time_spec, repeat
    num_sent = tx_stream.send(server.iq, tx_metadata)
    return replay_buff_addr, replay_buff_size


class UsrpTCPHandler(socketserver.StreamRequestHandler):
    def handle(self):
        while True:
            self.data = self.rfile.readline().strip()
            if self.data is None or self.data == "" or not self.data:
                break
            self.data = str(self.data, "utf-8")
            value = self.data.split("=")[-1]
            # X410 Python 3 version is 3.7(?), no switch statments
            ### Get general device status
            if self.data.startswith("temp=?"):
                logging.debug("Getting temp")
                response = str(server.usrp["mboard"].get_sensor("temp_fpga").value)
                response += " " + str(
                    server.usrp["radio"].get_tx_sensor("temperature", 1).value
                )
            elif self.data.startswith("rf out?"):
                logging.debug("Getting rf playback status")
                response = str(server.rf_output)
            ### Get/set rf parameters
            elif self.data.startswith("freq="):
                if value == "?":
                    logging.debug("Getting frequency")
                    response = server.usrp["radio"].get_tx_frequency(1)
                else:
                    logging.debug("Setting frequency")
                    server.usrp["radio"].set_tx_frequency(float(value), 1)
                    response = server.usrp["radio"].get_tx_frequency(1)
            elif self.data.startswith("power="):
                if value == "?":
                    logging.debug("Getting power")
                    response = server.usrp["radio"].get_tx_power_reference(1)
                else:
                    logging.debug("Setting power")
                    server.usrp["radio"].set_tx_power_reference(float(value), 1)
                    response = server.usrp["radio"].get_tx_power_reference(1)
            elif self.data.startswith("wv_file="):
                if value == "?":
                    logging.debug("Getting wv file")
                    if server.wv_file is None:
                        response = "None"
                    else:
                        response = str(server.wv_file)
                else:
                    logging.info("Loading wv file")
                    server.wv_file = Path(value)
                    if Path(server.wv_file).exists():
                        logging.debug("Setting wv file")
                        server.iq, server.data_rate = read_wv_file(server.wv_file)
                        logging.debug(f"Setting data rate to {server.data_rate}")
                        server.usrp["duc"].set_input_rate(server.data_rate, 1)
                        server.buf_adr, server.buf_sze = load_wv(server.iq, server.usrp)
                        response = server.wv_file
                    else:
                        response = "Error: file does not exist"
            ### Control device playback
            elif self.data.startswith("start"):
                logging.debug("Attempting to start playback")
                if server.iq is not None:
                    logging.info("Starting playback")
                    self.play_thread = threading.Thread(
                        target=play_wv,
                        args=(
                            server.event,
                            server.buf_adr,
                            server.buf_sze,
                            server.usrp,
                        ),
                    )
                    self.play_thread.start()
                    server.rf_output = True
                    response = "RF output started"
                else:
                    logging.error("IQ data not defined")
                    response = "Error: IQ data not defined"
            elif self.data.startswith("stop"):
                if not server.rf_output:
                    response = "RF output not enabled"
                else:
                    logging.debug("stopping playback")
                    server.event.set()
                    self.play_thread.join()
                    server.rf_output = False
                    server.event.clear()
                    response = "RF output stopped"
            else:
                response = "Error: Invalid command"

            self.wfile.write(bytes(str(response), "utf-8"))
            self.wfile.flush()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    ip_out = run('ifconfig eth0 | grep "inet addr:"', shell=True, capture_output=True)
    ip_addr = str(ip_out.stdout, "utf-8").strip().split("  ")[0].split(":")[1]

    HOST, PORT = (
        ip_addr,
        9999,
    )  # for now this is static base on x410 current configuration

    default_freq = 2.4e6
    default_power = -10
    default_rate = 30.72e6

    wv_file = None

    # UHD Setup
    graph = uhd.rfnoc.RfnocGraph("addr=127.0.0.1")
    mb = graph.get_mb_controller()

    radio_ctrl = uhd.rfnoc.RadioControl(graph.get_block("0/Radio#1"))
    replay_block = uhd.rfnoc.ReplayBlockControl(graph.get_block("0/Replay#0"))

    uhd.rfnoc.connect_through_blocks(
        graph, replay_block.get_unique_id(), 0, radio_ctrl.get_unique_id(), 1
    )

    stream_args = uhd.usrp.StreamArgs("sc16", "sc16")
    tx_stream = graph.create_tx_streamer(1, stream_args)
    duc_ctrl = uhd.rfnoc.DucBlockControl(graph.get_block("0/DUC#1"))
    graph.connect(tx_stream, 0, replay_block.get_unique_id(), 0)

    radio_ctrl.set_tx_frequency(default_freq, 1)
    radio_ctrl.set_tx_antenna("TX/RX0", 1)
    radio_ctrl.set_tx_power_reference(default_power, 1)

    duc_ctrl.set_input_rate(default_rate, 1)
    duc_ctrl.set_output_rate(radio_ctrl.get_rate(), 1)

    graph.commit()

    with socketserver.TCPServer((HOST, PORT), UsrpTCPHandler) as server:
        server.usrp = {
            "mboard": mb,
            "graph": graph,
            "radio": radio_ctrl,
            "replay": replay_block,
            "stream": tx_stream,
            "duc": duc_ctrl,
        }
        server.data_rate = default_rate
        server.wv_file = wv_file
        server.rf_output = False
        server.iq = None
        server.event = threading.Event()
        while True:
            received_data = server.handle_request()
