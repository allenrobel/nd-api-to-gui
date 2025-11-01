#!/usr/bin/env python
"""
# Summary

Print the names for all default templates supported by Nexus Dashboard (ND).

## Usage example

```bash
export ND_IP4="192.168.1.1"
export ND_DOMAIN=local
export ND_PASSWORD=MySecretPassword
export ND_USERNAME=admin
python3 nd_template_names.py
```
"""
from os import environ
from sys import exit as sys_exit
from typing import Any

from nd_api_to_gui.log_v2 import Log
from nd_api_to_gui.response_handler import ResponseHandler
from nd_api_to_gui.rest_send_v2 import RestSend
from nd_api_to_gui.results_v2 import Results
from nd_api_to_gui.sender_requests import Sender
from nd_api_to_gui.template_names import TemplateNames

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
instance = TemplateNames()
instance.rest_send = rest_send
instance.results = Results()
try:
    instance.refresh()
except ValueError as error:
    print(f"Error occurred: {error}")
    sys_exit(1)

for template_name in instance.template_names:
    print(f"- {template_name}")
