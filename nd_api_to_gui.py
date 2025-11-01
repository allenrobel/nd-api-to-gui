#!/usr/bin/env python
# pylint: disable=line-too-long
"""
# Summary

Print mapping between Nexus Dashboard (ND) REST API keys
for a ND template and ND GUI field names associated
with the keys in the template.

## Usage example

```bash
export ND_IP4="192.168.1.1"
export ND_DOMAIN=local
export ND_PASSWORD=MySecretPassword
export ND_USERNAME=admin
python3 nd_api_to_gui.py --template-name MSD_Fabric
```

Some template names to try:

- Default_Network_Universal (Network configuration)
- Default_VRF_Universal (VRF configuration)
- Easy_Fabric (VXLAN/EVPN fabrics)
- Easy_Fabric_Classic (Classic LAN fabric with Nexus switches)
- ERSPAN (Encapsulated Remote Switch Port Analyzer)
- MSD_Fabric (Multi-Site fabrics)


"""
from argparse import ArgumentParser
from os import environ
from sys import exit as sys_exit
from typing import Any

from nd_api_to_gui.log_v2 import Log
from nd_api_to_gui.response_handler import ResponseHandler
from nd_api_to_gui.rest_api_to_gui import RestApiToGui
from nd_api_to_gui.rest_send_v2 import RestSend
from nd_api_to_gui.results_v2 import Results
from nd_api_to_gui.sender_requests import Sender

# Logging setup
try:
    log = Log()
    log.commit()
except ValueError as error:
    print(f"Failed to initialize logging: {error}")
    sys_exit(1)

nd_ip4 = environ.get("ND_IP4")
nd_password = environ.get("ND_PASSWORD")
nd_username = environ.get("ND_USERNAME", "admin")

if nd_ip4 is None or nd_password is None or nd_username is None:
    raise ValueError("ND_IP4, ND_PASSWORD, and ND_USERNAME must be set")

parser = ArgumentParser(
    description="Build a translation mapping from REST API keys to GUI names."
)
parser.add_argument(
    "--template-name",
    default="MSD_Fabric",
    help="Template name to query (default: MSD_Fabric)",
)
args = parser.parse_args()

sender = Sender()
sender.ip4 = nd_ip4
sender.username = nd_username
sender.password = nd_password
sender.login()

params: dict[str, Any] = {}
params["state"] = "query"
params["config"] = {}
rest_send = RestSend(params)
rest_send.response_handler = ResponseHandler()
rest_send.sender = sender
instance = RestApiToGui()
instance.template_name = args.template_name
instance.rest_send = rest_send
instance.results = Results()
try:
    instance.commit()
except ValueError as error:
    print(f"Error occurred: {error}")
    sys_exit(1)

print("If GUI Section is blank, the parameter is likely located in General Parameters.")
for param_name in instance.parameter_names:
    instance.parameter_name = param_name
    display_name = instance.parameter_display_name
    section = instance.parameter_section
    if display_name in ["", None]:
        continue
    MESSAGE = f"API Key: {instance.parameter_name}:\n"
    MESSAGE += f"  Description: {instance.parameter_description}\n"
    MESSAGE += f"  GUI Section: {section}\n"
    MESSAGE += f"  GUI Field Name: {display_name}\n"
    print(MESSAGE)
