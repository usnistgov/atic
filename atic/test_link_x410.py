"""Functions taken from the p2p_testbed class of testbed one that allows 
the hardware to be checked out and rudimentary performance tests to be 
performed."""

import time
import datetime
import shutil
import json
from copy import deepcopy
from pathlib import Path

import pandas as pd
import labbench as lb
from ssmdevices.instruments import MiniCircuitsRCDAT
from ssmdevices.instruments import RigolDP800Series
from p2p_link import P2PLink
from config import testbed_config
from logs import Log
from x410_driver import UsrpX410

def write_log(event, config_number):
    """Write log with meta information of attenuators
    Args:
        event (String): a description of when the logging occured
        config_number (Int): the configuration number when the logging occured

    Returns:
        None
    """
    log.add_entry(
        {
            "event": f"{event}",
            "config_number": config_number,
            "p2p_parent_attn": p2p_parent_attn.attenuation_setting,
            "p2p_child_attn": p2p_child_attn.attenuation_setting,
            "noise_diode_attn": noise_diode_attn.attenuation_setting,
            "interferer_attn": interferer_attn.attenuation_setting,
        }
    )


def write_x410_log(config_number):
    """Write log with meta information of X410

    Args: 
        config_number (Int): the configuration number when the logging occured

    Returns:
        None
    """
    log.add_entry(
            {
            "event": "X410 Ouput parameters",
            "config_number": config_number,
            "RF Output": usrp.query_rf(),
            "Playback WV": usrp.playback_wv_file,
            "Set power output": set_power,
            "Reported power output": usrp.rf_output_power,
            "Center Freq": usrp.center_freq,
            "x410 temp": usrp.get_temp(),
            }
    )


def shell_run_mcs_iperf(test_config, run_directory, local_directory):
    """Use the labbench concurrently functionality to run the MCS acquisition script
    and the iperf acquisition script
    
    Args:
        test_config (String):  the configuration number of the test
        run_directory (String):  the remote directory where the files are stored
        local_directory (Path):  the local directory to store the files
    
    Returns:
        None
    """
    #Look for and kill stale servers
    p2p_link.find_kill_iperf_server()
    #Start a new server
    p2p_link.start_child_iperf_server(interval=test_config["interval"])
    #create a configuration for the settle time, and run it.
    settle_config = deepcopy(test_config)
    settle_config["test_time"] = settle_config["start_settle_time"]
    settle_config["config"] = str(settle_config["config"]) + "s"
    set_channel_attenuation(settle_config, test_config)
    #call the iperf and mcs measurements on the remote device.
    lb.concurrently(
        lb.Call(p2p_link.run_mcsloop, test_config, run_directory),
        lb.Call(p2p_link.run_iperf, test_config, run_directory),
    )
    #if there was a settle measurement move that data, move the remainder of the data
    if settle_config["start_settle_time"] != 0:
        print("moving settle")
        move_data_files("iperf", settle_config, run_directory, local_directory)
    print("moving mcs")
    move_data_files("mcs", test_config, run_directory, local_directory)
    print("moving test")
    move_data_files("iperf", test_config, run_directory, local_directory)


def set_channel_attenuation(settle_conf, in_config):
    """Set attenuator levels for the testbed based on the various inputs
    from the testbed_runner.  

    Args:
        settle_conf (dict):  a dictionary for running the settling test
        in_config (dict):  a dictionary for the primary test
    """

    write_log("before_start_settle", settle_conf["config"])
    p2p_parent_attn.attenuation_setting = settle_conf["start_p2p_parent_attn"]
    noise_diode_attn.attenuation_setting = settle_conf["start_noise_diode_attn"]
    interferer_attn.attenuation_setting = settle_conf["start_interferer_attn"]
    p2p_child_attn.attenuation_setting = settle_conf["start_p2p_child_attn"]
    if settle_conf["test_time"] != 0:
        p2p_link.run_iperf(settle_conf, run_directory)
    write_log("after_start_settle", in_config["config"])
    p2p_parent_attn.attenuation_setting = in_config["test_p2p_parent_attn"]
    noise_diode_attn.attenuation_setting = in_config["test_noise_diode_attn"]
    interferer_attn.attenuation_setting = in_config["test_interferer_attn"]
    p2p_child_attn.attenuation_setting = in_config["test_p2p_child_attn"]
    settle_conf["test_time"] = settle_conf["test_settle_time"]
    if settle_conf["test_time"] != 0:
        p2p_link.run_iperf(settle_conf, run_directory)
    write_log("after_test_settle", in_config["config"])


def move_data_files(datastream, test_config, run_directory, local_directory):
    """Uses paramiko ssh connection to move data files generated on the p2p link to a local directory
    
    Args:
        datastream (String):  the data stream that generated the file, ie mcs/iperf
        test_config (String):  the configuration number of the test
        run_directory (String):  the remote directory where the files are stored
        local_directory (Path):  the local directory to store the files

    Returns:
        None.
    """
    remote_file = run_directory + rf'/{test_config["config"]}_{datastream}.json'
    local_file = str(local_directory) + rf'\{test_config["config"]}_{datastream}.json'
    p2p_link.sftp_p2p_parent.get(remote_file, local_file)
    print(remote_file + " moved.")
    stdin, stdout, stderr = p2p_link.ssh_p2p_parent.exec_command(f"rm -f {remote_file}")
    # prematurely stopped files will be malformed json, clean up.
    with open(local_file, "r") as fh:
        print(f"reading {local_file}")
        file_contents = fh.read()
        new_file_contents = file_contents
        if file_contents.strip()[-1] == ",":
            new_file_contents = file_contents.strip()[:-1] + "\n]"
            with open(local_file, "w") as nfh:
                nfh.write(new_file_contents)
                print(f"writing nfh {local_file}")


def initiate_run(test_conditions_filepath):
    """
    Initiate a run by:
    - Pulling the name of the run from the input file
    - Creating a run directory
    - Copying the csv & yaml & config to the meta directory
    - Pulling in the test runner as a dataframe
    - Creating a 'remaining' tests frame
    - Logging that the run was initiated

    Args:
        test_conditions_filepath (Path): *.csv file containing test conditions

    Returns:
        test_runner (List): List of test condition dictionaries
        run_directory (Path): filepath on the DUT
        local_directory (Path): data storage path on the local system
    """
    #getting the name of the run based on the testconditions .csv file
    run_name = Path(test_conditions_filepath).stem
    local_directory, meta_directory, run_directory = create_run_directory(run_name)
    #Copying the run sheet to the meta folder
    shutil.copy(test_conditions_filepath, str(meta_directory) + "\\test_conditions.csv")
    #capturing the experimental metadata file and moving it to the data folder
    yaml_file = Path(test_conditions_filepath).with_suffix(".yaml")
    shutil.copy(yaml_file, str(meta_directory) + "\\experiment_metadata.yaml")
    #capturing the testbed physical component configurations
    with open(str(meta_directory) + "\\testbed_config.py", "w") as dict_file:
        json.dump(testbed_config, dict_file, indent=4)
    #reading the runsheet into memory as a list of dictionaries
    test_runner = pd.read_csv(test_conditions_filepath, keep_default_na=False).to_dict(
        "records"
    )
    return test_runner, run_directory, local_directory


def create_run_directory(run_name):
    """Creates a remote and local mirrored run directory that is timestamped
    
    Args:
        run_name (String): the name of the run used to create folders

    Returns:
        local_directory:  where the data is stored on the local machine
        meta_directory:  where the meta information for the experiment is stored
        run_directory:  where the data is stored on the remote machine (DUT)
    """
    #grab timestamp and format it
    folder_ts = datetime.datetime.now()
    ts_str = folder_ts.strftime("%Y_%m_%d-%H_%M_%S")
    #make a sub directory under /data/ on the embedded device
    run_directory = "/data/" + run_name + "-" + ts_str
    stdin, stdout, stderr = p2p_link.ssh_p2p_parent.exec_command(
        f"mkdir {run_directory}"
    )
    p2p_link.check_stderr(stderr)
    #make local data and meta directories.
    local_directory = Path(local_data_root,f"{run_name}-{ts_str}")
    meta_directory = Path( local_directory,"meta")
    local_directory.mkdir(parents=True, exist_ok=False)
    meta_directory.mkdir(parents=True, exist_ok=False)
    return local_directory, meta_directory, run_directory


def set_x410_playback(enable, usrp_obj, power_set):
    """Setup x410 for playback"""
    if enable:
        usrp.center_freq = 6.02e9
        usrp.rf_output_power = power_set
        usrp.playback_wv_file = "/data/wv_files/pulsedWN_100mson_100msoff.wv"
        usrp.start_wv()
        print("x410 enabled")
    else:
        usrp.stop_wv()
        print("X410 disabled")


if __name__ == "__main__":
    log = Log()
    #User input of the test to run
    test_conditions_filepath = (
        r"C:\Users\Public\Documents\Local_Queue\test_conditions_WNpulse100ms_equal.csv"
    )     
    #User input to the power of the X410
    set_power = 5
    #pulling in root directory for data storage
    local_data_root = testbed_config["filepaths"]["local_data_root"]
    #instantiating instruments
    p2p_link = P2PLink(**testbed_config["link_config"])
    p2p_parent_attn = MiniCircuitsRCDAT(**testbed_config["p2p_parent_attn_config"])
    p2p_child_attn = MiniCircuitsRCDAT(**testbed_config["p2p_child_attn_config"])
    interferer_attn = MiniCircuitsRCDAT(**testbed_config["interferer_attn_config"])
    noise_diode_attn = MiniCircuitsRCDAT(**testbed_config["noise_diode_attn_config"])
    power_supply = RigolDP800Series(testbed_config["power_supply_config"]["resource"])
    usrp = UsrpX410(freq=6.02e9, rf_power=5)
    #opening instruments
    power_supply.open()
    p2p_parent_attn.open()
    p2p_child_attn.open()
    noise_diode_attn.open()
    interferer_attn.open()
    test_runner, run_directory, local_directory = initiate_run(test_conditions_filepath)
    #setting up X410 USRP for playback
    set_x410_playback(True, usrp, set_power)
    #pointing log to meta directory
    log.file_path = Path(local_directory, "meta", "log.yaml")
    #logging the information for the interferer
    previous_wv = usrp.playback_wv_file
    write_x410_log(0)
    #running the test configs
    for test_config in test_runner:
        before = time.time()
        #if the wv_file is in the test config make sure correct waveform is playing
        if 'wv_file' in test_config:
            current_wv = test_config['wv_file']
            if current_wv != previous_wv:
                usrp.playback_wv_file = current_wv
                previous_wv = current_wv
                write_x410_log(test_config['config'])
        #make sure the power is on
        if not usrp.query_rf():
            raise Exception("RF output is not on, check interferer")
        print('starting next config')
        #running the performance test 
        shell_run_mcs_iperf(test_config, run_directory, local_directory)
        write_log("after_test", test_config["config"])
        print(f"test config took {int(time.time()-before)} seconds")
    #closing all the instruments once the test is over
    p2p_parent_attn.close()
    p2p_child_attn.close()
    noise_diode_attn.close()
    interferer_attn.close()
    set_x410_playback(False, usrp, set_power)
