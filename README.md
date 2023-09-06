## <u>**atic: Software for Automated Interference Testing**</u>
*atic* is a python implementation of an interference testbed that allows
injection of an interference waveform at various ranging from either end of
a point to point microwave link. While this code is mature enough to stand up a
testbed, the software is under continuous development and is subject to change.

## Reference
Michelle Pirrone, M. Keith Forsyth, Jordan Bernhardt, Daniel Kuester, Aric Sanders, Duncan McGillivray, Adam Wunderlich
"ATIC: Automated Testbed for Interference Testing in Communications Systems" to appear in Proc. 2023 IEEE Military Communications Conference


## Getting started with `atic`
### Installation
1. Ensure python 3.11 or newer is installed
2. In a command prompt environment for this python interpreter, run
    ```sh
    pip install git+https://github.com/usnistgov/atic
    ```

## Quick file descriptions
The main test code is found in the file *test_link_x410.py*.  To run the software
the user changes the test_conditions_filepath in the file runner to point to a
csv file that acts as a runner, there should be a similarly named  yaml file in that
same directory.  The csv runner file describes the conditions to be run by the testbed
and the yaml file describes the owner of the experiment and the overarching reason for
running the test.  The supporting file *config.py* describes the attributes of the physical
components of the testbed such as IP address and serial number.

Supporting files *p2p_link.py*, *x410_driver.py* are instrument drivers:
- *p2p_link.py* is a class that communicates via 
ssh and sftp to a pair of microwave point to point links.
- *x410_driver.py* is a class that communicates to an Ettus
USRP device over ssh and depends on the server elements found
in *./x410_server* to be running on the remote device to accept
the commands.

Supporting file *logs.py* is a custom logging class that serializes logs into
various file formats, though the yaml output format is chosen here.

The testbed RF circuitry is described in the circuit diagram below

<img src=circuit_diagram.png alt="RF Circuit" width="500" />

_Note: Certain commercial equipment, instruments, and software are identified here in order to help specify experimental procedures.  Such identification is not intended to imply recommendation or endorsement of any product or service by NIST, nor is it intended to imply that the materials or equipment identified are necessarily the best available for the purpose._

## Contributors
| Name  | Contact Info |
|---|---|
| Jordan Bernhardt  | <jordan.bernhardt@nist.gov>  |
| Keith Forsyth  | <keith.forsyth@nist.gov>  |
| Aric Sanders  | <aric.sanders@nist.gov>  |
