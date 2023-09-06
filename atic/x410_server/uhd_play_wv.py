import argparse
import uhd
import numpy as np
import re
import time

def parse_args():
    """Parse the command line arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--args", default="", type=str)
    parser.add_argument("--tx_args", default="", type=str)
    parser.add_argument("-n", "--infile", default="", type=str)
    parser.add_argument("-f", "--freq", type=float, required=True)
    parser.add_argument("-r", "--rate", default=1e6, type=float)
    parser.add_argument("-d", "--duration", default=5.0, type=float)
    parser.add_argument("-c", "--channels", default=0, nargs="+", type=int)
    parser.add_argument("-p", "--power", type=int, default=10)
    parser.add_argument("-t", "--trigger", action="store_true")
    return parser.parse_args()

# Numpy complex helpers
cplx_int = np.dtype([('re', np.int16), ('im', np.int16)])
def npsc16_to_cplx(cplx, float_out=False):
    if float_out:
        int_min = -32768
        int_max = 32767
        out_arr = cplx.view(np.int16).astype(np.float32).view(np.complex64)
        out_arr = 2 * ((out_arr - int_min) / (int_max - int_min)) - 1
    else:
        out_arr = cplx.view(np.int16).astype(np.float32).view(np.complex64)
    return out_arr

# Read file
def read_wv_file(fname):
    WV_TYPE_PATTERN = rb".*{TYPE:\s+(?P<type_info_1>[^,]+),\s+(?P<type_info_2>[^}]+)}"
    ORIGIN_INFO_PATTERN = rb".*{ORIGIN INFO:\s*(?P<origin_info>[^}]+)}"
    LEVEL_OFFSET_PATTERN = rb".*{LEVEL OFFS:\s*(?P<level_offset_1>[^,]+),\s+(?P<level_offset_2>[^}]+)}"
    DATE_PATTERN = rb".*{DATE:\s*(?P<wv_date>[^;]+);(?P<wv_time>[^}]+)}"
    CLOCK_PATTERN = rb".*{CLOCK:\s*(?P<sampling_frequency>[^}]+)}"
    SAMPLES_PATTERN = rb".*{SAMPLES:\s*(?P<number_of_samples>[^}]+)}"
    IQ_PATTERN = rb".*{WAVEFORM-(?P<iq_bytes>.\d*):\s*#"
    PATTERNS = [WV_TYPE_PATTERN, ORIGIN_INFO_PATTERN, LEVEL_OFFSET_PATTERN,
                DATE_PATTERN, CLOCK_PATTERN, SAMPLES_PATTERN, IQ_PATTERN]

    with open(fname, 'rb') as infile:
        data = infile.read()
    wv_data = {}
    for pattern in PATTERNS:
        match = re.match(pattern, data)
        if match is not None:
            wv_data.update(match.groupdict())
    iq = data.split(b'#', 1)[1][0:int(wv_data['iq_bytes'])-1]
    iq_ar = np.zeros(int(len(iq) / 4), dtype=complex)
    iq_ar = np.frombuffer(iq, dtype=cplx_int)
    return iq_ar, float(wv_data['sampling_frequency'])

def main():
    """TX samples based on input arguments"""
    args = parse_args()
    fname = args.infile
    iq, data_rate = read_wv_file(fname)
    # complex_iq = npsc16_to_cplx(iq)
    data_len = iq.shape[-1]

    graph = uhd.rfnoc.RfnocGraph("addr=127.0.0.1")

    # tx stream -> replay -> (DUC) -> radio
    radio_ctrl = uhd.rfnoc.RadioControl(graph.get_block("0/Radio#0"))
    replay_block = uhd.rfnoc.ReplayBlockControl(graph.get_block("0/Replay#0"))

    uhd.rfnoc.connect_through_blocks(graph, replay_block.get_unique_id(), 0, radio_ctrl.get_unique_id(), 0)  # This connects the replay through the DUC block (implied)

    stream_args = uhd.usrp.StreamArgs("sc16", "sc16")
    tx_stream = graph.create_tx_streamer(1, stream_args)
    duc_ctrl = uhd.rfnoc.DucBlockControl(graph.get_block("0/DUC#0"))

    graph.connect(tx_stream, 0, replay_block.get_unique_id(), 0)

    graph.commit()

    # DUC block params
    duc_ctrl.set_input_rate(data_rate, 0)
    duc_ctrl.set_output_rate(radio_ctrl.get_rate(), 0)  # Radio block has a fixed rate

    # Radio tx params
    radio_ctrl.set_tx_frequency(args.freq, 0)
    radio_ctrl.set_tx_antenna("TX/RX0", 0)
    radio_ctrl.set_tx_power_reference(args.power, 0)

    if args.trigger:
        # Radio GPIO control
        pin_mask = 1 << 0  # output pin number goes here, includes both gpio ports so need to make sure bit mask is configured correctly
        radio_ctrl.set_gpio_attr("GPIO", "CTRL", 0, pin_mask)  # Non-ATR mode
        radio_ctrl.set_gpio_attr("GPIO", "DDR", pin_mask, pin_mask)  # Output
    else:
        pass

    replay_word_size = replay_block.get_word_size()
    sample_size = 4  # Complex signed 16-bit is 32 bits per sample

    replay_buff_addr = 0
    replay_buff_size = data_len * sample_size
    replay_block.record(replay_buff_addr, replay_buff_size, 0)
    # Example restarts record, should have been overwritten with record command

    tx_metadata = uhd.types.TXMetadata()
    # replay_buff_addr, replay_buff_size, replay_chan, time_spec, repeat
    num_sent = tx_stream.send(iq, tx_metadata)
    if replay_block.get_record_fullness(0) != replay_buff_size:
        print("record fullness", replay_block.get_record_fullness(0), data_len)
        exit(1)

    time_spec = uhd.libpyuhd.types.time_spec(0)
    if args.duration <= 0:
        try:
            replay_block.play(replay_buff_addr, replay_buff_size, 0, time_spec, True)
            if args.trigger:
                radio_ctrl.set_gpio_attr("GPIO", "OUT", pin_mask, pin_mask) # Set value high
            while True:
                pass
        except KeyboardInterrupt:
            replay_block.stop(0)
    else:
        start_time = time.time()
        if args.trigger:
            radio_ctrl.set_gpio_attr("GPIO", "OUT", pin_mask, pin_mask) # Set value high
            radio_ctrl.set_gpio_attr("GPIO", "OUT", 0, pin_mask) # Set value low
        replay_block.play(replay_buff_addr, replay_buff_size, 0, time_spec, True)
        while time.time() < start_time + args.duration:
            pass
        replay_block.stop(0)

    # Send EOB to terminate Tx
    tx_metadata.end_of_burst = True
    tx_stream.send(np.zeros(8, dtype=np.complex64), tx_metadata)

if __name__ == "__main__":
    main()
