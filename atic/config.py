# -*- coding: utf-8 -*-
"""
Created on Tue May 31 15:48:15 2022

A dictionary that defines the attributes of instruments and 
filepaths to be used in the testbed.  For this particular 
testbed the equipment used is:
    Ligowave point to point microwave link pair
    Minicircuits 4 channel programmable attenuator
    Rigol 3 channel power supply

@author: mkf3
"""

testbed_config = {
    "test_input": {
        "config": None,
    },
    "link_config": {"p2p_child_address": "10.0.1.66", "p2p_parent_address": "10.0.0.65",},
    "p2p_parent_attn_config": {
        "resource": "12208250156",
        "frequency": 5910e6,
        "channel":1
    },
    "p2p_child_attn_config": {
        "resource": "12208250156",
        "frequency": 5910e6,
        "channel":4
    },
    "noise_diode_attn_config": {
        "resource": "12208250156",
        "frequency": 5910e6,
        "channel":2
    },
    "interferer_attn_config": {
        "resource": "12208250156",
        "frequency": 5910e6,
        "channel":3
    },
    "power_supply_config": {
        "resource": "USB0::0x1AB1::0x0E11::DP8C240800631::INSTR",
        "voltage_setting1": 28,
        "voltage_setting2": 5,
        "voltage_setting3": 5,
        "current1_max": 0.150,
        "current2_max": 0.300,
        "current3_max": 0.300,
    },
    "filepaths": { 
        "local_data_root": r"C:\Users\Public\Documents\Local_Data"
    },
}