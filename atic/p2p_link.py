# -*- coding: utf-8 -*-
"""
Created on Tue Jul 19 08:47:18 2022

Class to communicate with a pair of microwave comms links
Relies heavily on the paramiko library for SSHClient.


@author: mkf3
"""

import paramiko
from paramiko import SSHClient
import time

class P2PLink:
    """Point to Point link pair class with one parent and one child
    Requires the configuration of the devices with ip address and target
    RF information
    
    Args:
        options["p2p_parent_address]
    """
    def __init__(self, **options):
        self.p2p_parent_address = options["p2p_parent_address"]
        self.p2p_child_address = options["p2p_child_address"]

        self.ssh_p2p_parent = SSHClient()
        self.ssh_p2p_parent.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh_p2p_parent.connect(
            self.p2p_parent_address, username="admin", password="password"
        )
        self.sftp_p2p_parent = self.ssh_p2p_parent.open_sftp()

        self.ssh_p2p_child = SSHClient()
        self.ssh_p2p_child.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh_p2p_child.connect(
            self.p2p_child_address, username="admin", password="password"
        )

    def check_stderr(self, stderr):
        """Function to check whether stderr is populated and raise
        an exception if it is
        
        Args:
            stderr (Bytes):  The error output from the remote execution
        """
        msg = bytearray(stderr.read().decode(), 'utf-8')
        if len(msg) > 0: 
            print("stderr read", msg)
            raise Exception("StdErr reported from the remote device")

    def start_child_iperf_server(self, interval=1):
        """Function that will start an iperf server on the remote device
        
        Args: 
            interval (Int): the interval that the iperf server should report
        """
        #start server
        stdin, stdout, stderr = self.ssh_p2p_child.exec_command(
            f"/data/iperf3-arm32v7 -s -i {interval} --rcv-timeout 5000"
            )
        self.check_stderr(stderr)
        #check if server has a pid
        stdin, stdout, stderr = self.ssh_p2p_child.exec_command(
            "pidof iperf3-arm32v7"
        )
        self.check_stderr(stderr)
        iperf_pid = stdout.read().decode().strip()
        #if no iperf_pid then server isn't started
        if not iperf_pid:
            raise Exception("Remote iperf server not started.")

    def find_kill_iperf_server(self):
        """Function to find and kill any stale iperf servers"""
        #get pid of iperf
        stdin, stdout, stderr = self.ssh_p2p_child.exec_command(
            "pidof iperf3-arm32v7"
        )
        #get pid
        iperf_pid = stdout.read().decode().strip()
        #if there's no pid then no need to kill it
        if iperf_pid:
            stdin, stdout, stderr = self.ssh_p2p_child.exec_command(f"kill {iperf_pid}")
            self.check_stderr(stderr)
            return {"event": "kill iperf3-arm32v7", "pid": iperf_pid}
        else:
            return {"event": "kill iperf3-arm32v7", "pid": None}

    def copy_p2p_config(self, run_directory, meta_directory):
        """copies the json link config file from the p2p into the run directory remote & local
        
        Args:
            run_directory (String): remote path to files
            meta_directory (String): local path to the meta data
        
        Returns:
            log_dict (dict):  Dictionary compatible with AWS log class
        """
        #copy the configuration to the run directory
        stdin, stdout, stderr = self.ssh_p2p_parent.exec_command(
            f"cp /tmp/config.json {run_directory}/p2p_config.json"
        )
        self.check_stderr(stderr)
        #move the file over
        remote_file = f"{run_directory}/p2p_config.json"
        local_file = str(meta_directory) + r"\p2p_link_config.json"
        self.sftp_p2p_parent.get(remote_file, local_file)
        print(f"copied p2p config to {run_directory}")
        log_dict =  {"event": "copy_p2p_config", "path": f"{run_directory}"}
        return log_dict

    def run_mcsloop(self, test_input, run_directory):
        """
        Function that will run the mcs_loop.sh terminal command on the remote machine

        Args:
            test_input (Dict): dictionary that contains the input to the remote script
            run_directory (String): the remote directory where data is temporarily stored.

        Returns:
            stdout (String): stdout response from the remote machine
        """
        
        mcs_cmd = f"/data/mcs_loop.sh {test_input['test_time']} {run_directory} {test_input['config']} {test_input['interval']}" 
        print(mcs_cmd)
        stdin, stdout, stderr = self.ssh_p2p_parent.exec_command(mcs_cmd)
        self.check_stderr(stderr)
        return stdout.read().decode()

    def run_iperf(self, test_input, run_directory):
        """
        Function that will run an iperf terminal command on the remote machine

        Args:
            test_input (Dict): dictionary that contains the input to the remote script
            run_directory (String): the remote directory where data is temporarily stored.

        Returns:
            stdout (String): stdout response from the remote machine
        """
        iperf_remote_file = run_directory + fr'/{test_input["config"]}_iperf.json'
        remaining_time = test_input['test_time']
        for attempt in range(3):
            try:
                self.ssh_p2p_parent.exec_command(f"echo \"[\" >> {iperf_remote_file}")
            except paramiko.ssh_exception.SSHException:
                time.sleep(2)
                continue
            else:
                break
        start_time = time.time()
        end_time = start_time + remaining_time
        while time.time() <= start_time + test_input['test_time']:
            print('entering')
            iperf_command = f"/data/iperf3-arm32v7 -c {self.p2p_child_address} -i {test_input['interval']} -t {remaining_time} -l {test_input['packet_size']} --snd-timeout 3000 -J >> {iperf_remote_file}"
            print(iperf_command)
            stdin, stdout, stderr = self.ssh_p2p_parent.exec_command(iperf_command)
            self.check_stderr(stderr)
            output=stdout.read().decode()
            if time.time() <= start_time + test_input['test_time'] and "unable to connect to server" in output:
                # change run time, restart, repeat until time is up
                print("restarting iperf")
                self.ssh_p2p_parent.exec_command(f"echo \",\" | tee -a {iperf_remote_file}")
                remaining_time = int(end_time - time.time())
                if remaining_time <= 0:
                    break
        for attempt in range(3):
            try:
                self.ssh_p2p_parent.exec_command(f"echo \"]\" >> {iperf_remote_file}")
            except paramiko.ssh_exception.SSHException:
                time.sleep(2)
                if attempt != 2:
                    continue
                else:
                    raise
            else:
                break
        return stdout.read().decode()
