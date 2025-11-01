#
# Copyright (c) 2024 Cisco and/or its affiliates.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# pylint: disable=too-many-instance-attributes
"""
An injected dependency for `RestSend` which implements the
`sender` interface.  Responses are retrieved using Python
requests library.
"""
from __future__ import absolute_import, division, print_function

__metaclass__ = type  # pylint: disable=invalid-name
__author__ = "Allen Robel"

import copy
import inspect
import json
import logging
from collections import deque
from os import environ
from typing import Any

try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    import urllib3

    HAS_URLLIB3 = True
except ImportError:
    HAS_URLLIB3 = False

MESSAGE: str = ""
if HAS_REQUESTS is False:
    MESSAGE = "requests is not installed. "
    MESSAGE += "install with e.g. pip install requests"
    raise ImportError(MESSAGE)

if HAS_URLLIB3 is False:
    MESSAGE = "urllib3 is not installed. "
    MESSAGE += "install with e.g. pip install urllib3"
    raise ImportError(MESSAGE)


class Sender:
    """
    # Summary

    An injected dependency for `RestSend` which implements the
    `sender` interface.  Responses are retrieved using Python
    requests library.

    ## Raises

    -   `ValueError` if:
            -   `path` is not set.
            -   `password` is not set.
            -   `domain` is not set.
    -   `TypeError` if:
            -   `payload` is not a `dict`.
            -   `response` is not a `dict`.

    ## Default values

    -   `domain`: "local"
    -   `username`: "admin"

    ## Usage

    Credentials and NDFC controller IP can be set using environment
    variables.  For example:

    ```bash
    export ND_USERNAME=my_username
    export ND_PASSWORD=my_password
    export ND_DOMAIN=local
    export ND_IP4=10.1.1.1
    export ND_IP6=2001:db8::1
    ```

    Setting credentials through the following class properties overrides
    the environment variables:

    - domain
    - ip4
    - ip6
    - password
    - username

    ```python
    from ansible_collections.cisco.dcnm.plugins.module_utils.common.sender_requests import \
        Sender

    sender = Sender()
    # Uncomment to override environment variables
    # sender.domain = "local"
    # If both ip4 and ip6 are set, ip4 is used.
    # sender.ip4 = "10.1.1.1"
    # sender.ip6 = "2001:db8::1"
    # sender.password = "my_password"
    # sender.username = "my_username"
    sender.login()
    try:
        rest_send = RestSend()
        rest_send.sender = sender
    except (TypeError, ValueError) as error:
        handle_error(error)
    # etc...
    # See rest_send_v2.py for RestSend() usage.
    ```
    """

    def __init__(self) -> None:
        self.class_name: str = self.__class__.__name__
        self._implements: str = "sender_v1"

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.log: logging.Logger = logging.getLogger(f"dcnm.{self.class_name}")

        self._domain: str = environ.get("ND_DOMAIN", "local")
        self._headers: dict[str, str] = {}
        self._history_rc: deque = deque(maxlen=50)
        self._history_path: deque = deque(maxlen=50)
        self._ip4: str = environ.get("ND_IP4", "")
        self._ip6: str = environ.get("ND_IP6", "")
        self._jwttoken: str = ""
        self._last_rc: int = -1
        self._last_url: str = ""
        self._logged_in: bool = False
        self._password: str = environ.get("ND_PASSWORD", "")
        self._path: str = ""
        self._payload: dict[str, Any] = {}
        self._rbac: dict[str, Any] = {}
        self._return_code: int = -1
        self._response: dict[str, Any] = {}
        self._timeout: int = 30
        self._token: str = ""
        self._url: str = ""
        self._username: str = environ.get("ND_USERNAME", "admin")
        self._verb: str = ""

    def _verify_commit_parameters(self) -> None:
        """
        # Summary

        Verify that required parameters are set prior to calling ``commit()``

        ## Raises

        -   `ValueError` if `verb` is not set
        -   `ValueError` if `path` is not set
        """
        method_name: str = inspect.stack()[0][3]
        if not self._ip4 and not self._ip6:
            msg = f"{self.class_name}.{method_name}: "
            msg += "ip4 or ip6 must be set before calling commit()."
            raise ValueError(msg)
        if not self._path:
            msg = f"{self.class_name}.{method_name}: "
            msg += "path must be set before calling commit()."
            raise ValueError(msg)
        if not self._verb:
            msg = f"{self.class_name}.{method_name}: "
            msg += "verb must be set before calling commit()."
            raise ValueError(msg)

    def commit(self) -> None:
        """
        # Summary

        Send the REST request to the controller

        ## Raises

        -   `ValueError` if:
                -   `path` is not set.
                -   `verb` is not set.
        """
        method_name: str = inspect.stack()[0][3]
        caller: str = inspect.stack()[1][3]
        msg: str = f"{self.class_name}.{method_name}: "
        msg += f"Caller: {caller}, ENTERED"
        self.log.debug(msg)

        try:
            self._verify_commit_parameters()
        except ValueError as error:
            msg = f"{self.class_name}.{method_name}: "
            msg += "Not all mandatory parameters are set. "
            msg += f"Error detail: {error}"
            raise ValueError(msg) from error
        self._set_url()
        msg = f"{self.class_name}.{method_name}: "
        msg += f"caller: {caller}.  "
        msg += f"Calling requests: verb {self._verb}, "
        msg += f"path {self._path}, "
        msg += f"url {self._url}, "
        try:
            if self._payload is None:
                self.log.debug(msg)
                response = requests.request(
                    self._verb,
                    self._url,
                    headers=self._get_headers(),
                    verify=False,
                    timeout=self._timeout,
                )
            else:
                msg_payload = copy.deepcopy(self._payload)
                if "userPasswd" in msg_payload:
                    msg_payload["userPasswd"] = "********"
                msg += ", payload: "
                msg += f"{json.dumps(msg_payload, indent=4, sort_keys=True)}"
                self.log.debug(msg)
                response = requests.request(
                    self.verb,
                    self._url,
                    headers=self._get_headers(),
                    data=json.dumps(self.payload),
                    verify=False,
                    timeout=self._timeout,
                )
        except requests.exceptions.ConnectionError as error:
            msg = f"{self.class_name}.{method_name}: "
            msg = "Error connecting to the controller. "
            msg += f"Error detail: {error}"
            raise ValueError(msg) from error
        self._payload = {}
        self._gen_response(response)

    def _get_headers(self) -> dict[str, str]:
        """
        # Summary

        Returns the headers to use for the REST request.

        ## Raises

        None
        """
        headers: dict[str, str] = {}
        headers["Cookie"] = f"AuthCookie={self._token}"
        headers["AuthCookie"] = self._token
        headers["Content-Type"] = "application/json"
        headers["Authorization"] = self._token
        return copy.copy(headers)

    def _get_host(self) -> str:
        """
        # Summary

        Returns the server IP address to use based on the values
        of ip4 and ip6.

        ## Raises

        -   `ValueError` if neither `ip4` nor `ip6` is set.
        """
        method_name: str = inspect.stack()[0][3]
        if self._ip4:
            return self._ip4
        if self._ip6:
            return self._ip6
        msg = f"{self.class_name}.{method_name}: "
        msg += "ip4 or ip6 must be set before calling "
        msg += f"{self.class_name}.commit()"
        self.log.debug(msg)
        raise ValueError(msg)

    def _set_url(self) -> None:
        """
        # Summary

        Sets the full URL for the REST request based on the
        `path` and `ip4`/`ip6` properties.

        ## Raises

        -   `ValueError` if `path` is not set.
        """
        method_name: str = inspect.stack()[0][3]
        if self.path is None:
            msg = f"{self.class_name}.{method_name}: "
            msg += "call Sender.path before calling "
            msg += f"{self.class_name}.commit()"
            self.log.debug(msg)
            raise ValueError(msg)
        if self.path[0] == "/":
            self._url = f"https://{self._get_host()}{self.path}"
        else:
            self._url = f"https://{self._get_host()}/{self.path}"
        msg = f"{self.class_name}.{method_name}: "
        msg += f"Set url to {self._url}"
        self.log.debug(msg)

    def _add_history_rc(self, x):
        """
        # Summary

        Add a return code to the history deque.

        ## Raises

        None
        """
        self._history_rc.appendleft(x)

    def _add_history_path(self, path: str):
        """
        # Summary

        Add a path to the history deque.

        ## Raises

        None
        """
        self._history_path.appendleft(path)

    def _update_status(self):
        """
        # Summary

        Update the last return code and URL, and add to history.

        ## Raises

        None

        ## Notes

        Not using currently.
        """
        self._last_rc = self._return_code
        self._last_url = self._url
        self._add_history_rc(self._return_code)
        self._add_history_path(self._url)

    def _gen_response(self, response: requests.Response) -> None:
        """
        # Summary

        Generate a response dictionary from the requests response object.

        ## Raises

        None
        """
        method_name: str = inspect.stack()[0][3]
        # set the token to the value of Set-Cookie in the
        # response headers (if present)
        token = response.headers.get("Set-Cookie", None)
        if token is not None:
            token = token.split("=")[1]
            token = token.split(";")[0]
            self._token = token
            msg = f"{self.class_name}.{method_name}: "
            msg += f"Set new token to {self._token}"
            self.log.debug(msg)

        response_dict: dict[str, Any] = {}
        self._return_code = response.status_code
        response_dict["RETURN_CODE"] = response.status_code
        try:
            response_dict["DATA"] = json.loads(response.text)
        except json.JSONDecodeError:
            data: dict[str, Any] = {}
            data["INVALID_JSON"] = response.text
            response_dict["DATA"] = data
        response_dict["MESSAGE"] = response.reason
        response_dict["METHOD"] = response.request.method
        response_dict["REQUEST_PATH"] = response.url
        self.response = copy.deepcopy(response_dict)

    def login(self) -> None:
        """
        # Summary

        Login to the controller and retrieve a token.

        ## Raises

        -   `ValueError` if:
                -   `username` is not set.
                -   `password` is not set.
                -   `domain` is not set.
        """
        if self._logged_in is True:
            return
        _raise = False
        msg: str = ""
        if not self.username:
            msg = "call Sender.username before calling Sender.login()"
            _raise = True
        if not self.password:
            msg = "call Sender.password before calling Sender.login()"
            _raise = True
        if not self.domain:
            msg = "call Sender.domain before calling Sender.login()"
            _raise = True
        if _raise is True:
            self.log.debug(msg)
            raise ValueError(msg)
        self._logged_in = False
        self.path = "/login"
        self._set_url()
        payload: dict[str, Any] = {}
        payload["userName"] = self.username
        payload["userPasswd"] = self.password
        payload["domain"] = self.domain
        self.payload = copy.copy(payload)
        headers = {}
        headers["Content-Type"] = "application/json"
        self.headers = copy.copy(headers)
        self.verb = "POST"
        self.commit()
        self._update_token()
        self._logged_in = True

    def _update_token(self) -> None:
        """
        # Summary

        Update the token, jwttoken, and rbac from the response.

        ## Raises

        -   `ValueError` if:
                -   unable to parse token from response.
        """
        method_name: str = inspect.stack()[0][3]
        msg = f"{self.class_name}.{method_name}: "
        msg += "ENTERED"
        self.log.debug(msg)
        try:
            self._token = self.response["DATA"]["jwttoken"]
            self._jwttoken = self.response["DATA"]["jwttoken"]
            self._rbac = self.response["DATA"]["rbac"]
        except KeyError as error:
            msg = f"{self.class_name}.{method_name}: "
            msg += "Unable to parse token from response: "
            msg += f"{self.response}"
            self.log.debug(msg)
            raise ValueError(msg) from error

    def refresh_login(self) -> None:
        """
        # Summary

        Refresh the login token for the controller.

        ## Raises

        -   `ValueError` if:
                -   `username` is not set.
                -   `password` is not set.
                -   `domain` is not set.
        """
        method_name: str = inspect.stack()[0][3]
        msg = f"{self.class_name}.{method_name}: "
        msg += "ENTERED"
        self.log.debug(msg)

        if not self.username:
            msg = f"{self.class_name}.{method_name}: "
            msg += "call Sender.username before calling "
            msg += "Sender.refresh_login()"
            self.log.debug(msg)
            raise ValueError(msg)
        if not self.password:
            msg = f"{self.class_name}.{method_name}: "
            msg += "call Sender.password before calling "
            msg += "Sender.refresh_login()"
            self.log.debug(msg)
            raise ValueError(msg)
        if not self.domain:
            msg = f"{self.class_name}.{method_name}: "
            msg += "call Sender.domain before calling "
            msg += "Sender.refresh_login()"
            self.log.debug(msg)
            raise ValueError(msg)

        self.path = "/refresh"
        self._set_url()
        payload: dict[str, Any] = {}
        payload["userName"] = self.username
        payload["userPasswd"] = self.password
        payload["domain"] = self.domain
        self.payload = payload
        headers: dict[str, str] = {}
        headers["Content-Type"] = "application/json"
        headers["Cookie"] = f"AuthCookie={self._jwttoken}"
        headers["Authorization"] = self._token
        self._headers = headers
        self.commit()
        self._update_token()

    @property
    def domain(self):
        """
        # Summary

        The domain for controller login.

        ## Raises

        None
        """
        return self._domain

    @domain.setter
    def domain(self, value):
        self._domain = value

    @property
    def headers(self) -> dict[str, str]:
        """
        # Summary

        The headers to include in the REST request.

        ## Raises

        None
        """
        return self._headers

    @headers.setter
    def headers(self, value: dict[str, str]) -> None:
        self._headers = value

    @property
    def history_pretty_print(self) -> None:
        """
        # Summary

        Pretty print the history of REST calls made including
        return codes and paths.

        ## Raises

        None
        """
        msg: str = "History (last 50 calls, most recent on top)\n"
        msg += f"{'RESULT_CODE':<11} {'Path':<70}\n"
        msg += f"{'-' * 11:<11} {'-' * 70:<70}"
        self.log.debug(msg)
        for rc, path in zip(self.history_rc, self.history_path):
            msg = f"{rc:<11d} {path:<70}"
            self.log.debug(msg)

    @property
    def history_rc(self) -> list[int]:
        """
        # Summary

        The history of return codes from REST calls made.

        ## Raises

        None
        """
        return list(self._history_rc)

    @property
    def history_path(self) -> list[str]:
        """
        # Summary

        The history of paths from REST calls made.

        ## Raises

        None
        """
        return list(self._history_path)

    @property
    def implements(self) -> str:
        """
        # Summary

        The interface implemented by this class.

        ## Raises

        None
        """
        return self._implements

    @property
    def ip4(self) -> str:
        """
        # Summary

        The IPv4 address of the controller.

        ## Raises

        None
        """
        return self._ip4

    @ip4.setter
    def ip4(self, value: str) -> None:
        self._ip4 = value

    @property
    def ip6(self) -> str:
        """
        # Summary

        The IPv6 address of the controller.

        ## Raises

        None
        """
        return self._ip6

    @ip6.setter
    def ip6(self, value: str) -> None:
        self._ip6 = value

    @property
    def last_rc(self) -> int:
        """
        # Summary

        The last return code from a REST call.

        ## Raises

        None
        """
        return self._last_rc

    @property
    def password(self) -> str:
        """
        # Summary

        The password for controller login.

        ## Raises

        None
        """
        return self._password

    @password.setter
    def password(self, value: str) -> None:
        self._password = value

    @property
    def path(self) -> str:
        """
        # Summary

        Endpoint path for the REST request.

        ## Raises

        None
        """
        return self._path

    @path.setter
    def path(self, value: str) -> None:
        self._path = value

    @property
    def payload(self) -> dict[str, Any]:
        """
        # Summary

        The payload to send to the controller

        ## Raises

        -   `TypeError` if value is not a `dict`.
        """
        return self._payload

    @payload.setter
    def payload(self, value: dict[str, Any]) -> None:
        method_name: str = inspect.stack()[0][3]
        if not isinstance(value, dict):
            msg = f"{self.class_name}.{method_name}: "
            msg += f"{method_name} must be a dict. "
            msg += f"Got type {type(value).__name__}, "
            msg += f"value {value}."
            raise TypeError(msg)
        self._payload = value

    @property
    def rbac(self) -> dict[str, Any]:
        """
        # Summary

        The RBAC information for the controller.

        ## Raises

        None
        """
        return self._rbac

    @rbac.setter
    def rbac(self, value: dict[str, Any]) -> None:
        self._rbac = value

    @property
    def response(self) -> dict[str, Any]:
        """
        # Summary

        The response from the controller.

        ## Raises

        -   `TypeError` if value is not a `dict`.

        """
        return copy.deepcopy(self._response)

    @response.setter
    def response(self, value: dict[str, Any]) -> None:
        method_name: str = inspect.stack()[0][3]
        if not isinstance(value, dict):
            msg: str = f"{self.class_name}.{method_name}: "
            msg += f"{method_name} must be a dict. "
            msg += f"Got type {type(value).__name__}, "
            msg += f"value {value}."
            raise TypeError(msg)
        self._response = value

    @property
    def timeout(self) -> int:
        """
        # Summary

        The timeout (in seconds) for the REST request.

        ## Raises

        -  `TypeError` if value is not an `int`.
        """
        return self._timeout

    @timeout.setter
    def timeout(self, value: int) -> None:
        method_name: str = inspect.stack()[0][3]
        if not isinstance(value, int):
            msg: str = f"{self.class_name}.{method_name}: "
            msg += f"{method_name} must be an int. "
            msg += f"Got type {type(value).__name__}, "
            msg += f"value {value}."
            raise TypeError(msg)
        self._timeout = value

    @property
    def username(self) -> str:
        """
        # Summary

        The username for controller login.

        ## Raises

        None
        """
        return self._username

    @username.setter
    def username(self, value: str) -> None:
        self._username = value

    @property
    def verb(self) -> str:
        """
        # Summary

        The HTTP verb for the REST request.

        ## Raises

        None
        """
        return self._verb

    @verb.setter
    def verb(self, value: str) -> None:
        self._verb = value
