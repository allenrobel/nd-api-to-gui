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
# pylint: disable=line-too-long, too-many-instance-attributes
"""
Implement the response handler interface for injection into RestSend().
"""
from __future__ import absolute_import, division, print_function

__metaclass__ = type  # pylint: disable=invalid-name
__author__ = "Allen Robel"

import copy
import inspect
import logging
from typing import Any


class ResponseHandler:
    """
    # Summary

    Implement the response handler interface for injection into RestSend().

    ## Raises

    -   ``TypeError`` if:
            -   ``response`` is not a dict.
    -   ``ValueError`` if:
            -   ``response`` is missing any fields required by the handler
                to calculate the result.
                -   Required fields:
                        -   ``RETURN_CODE``
                        -   ``MESSAGE``
            -   ``verb`` is not valid.
            -   ``response`` is not set prior to calling ``commit()``.
            -   ``verb`` is not set prior to calling ``commit()``.

    ## Interface specification

    -   setter property: `response`
            -   Accepts a dict containing the controller response.
            -   Raises `TypeError` if:
                    -   `response` is not a dict.
            -   Raises `ValueError` if:
                    -   `response` is missing any fields required by the handler
                        to calculate the result, for example `RETURN_CODE` and
                        `MESSAGE`.
    -   getter property: `result`
            -   Returns a dict containing the calculated result based on the
                controller response and the request verb.
    -   setter property: `verb`
            -   Accepts a string containing the request verb.
            -   Valid verb: One of "DELETE", "GET", "POST", "PUT".
            -   Raises `ValueError` if verb is not valid.
    -   method: `commit()`
            -   Parse `response` and set `result`.
            -   Raise `ValueError` if:
                    -   `response` is not set.
                    -   `verb` is not set.

    ## Usage example

    ```python
    # import and instantiate the class
    from nd_api_do_gui.response_handler import ResponseHandler
    response_handler = ResponseHandler()

    try:
        # Set the response from the controller
        response_handler.response = controller_response

        # Set the request verb
        response_handler.verb = "GET"

        # Call commit to parse the response
        response_handler.commit()

        # Access the result
        result = response_handler.result
    except (TypeError, ValueError) as error:
        handle_error(error)
    ```

    """

    def __init__(self) -> None:
        self.class_name: str = self.__class__.__name__
        method_name: str = inspect.stack()[0][3]
        self._implements: str = "response_handler_v1"

        self.log: logging.Logger = logging.getLogger(f"dcnm.{self.class_name}")

        self._response: dict[str, Any] = {}
        self._result: dict[str, bool] = {}
        self._return_codes_success: set[int] = {200, 404}
        self._valid_verbs: set[str] = {"DELETE", "GET", "POST", "PUT"}
        self._verb: str = ""

        msg: str = f"ENTERED {self.class_name}.{method_name}"
        self.log.debug(msg)

    def _handle_response(self) -> None:
        """
        # Summary

        Call the appropriate handler for response based on verb
        """
        if self._verb == "":
            msg = f"{self.class_name}._handle_response: "
            msg += "verb must be set prior to calling "
            msg += f"{self.class_name}._handle_response"
            self.log.error(msg)
            raise ValueError(msg)
        if self.verb == "GET":
            self._get_response()
        else:
            self._post_put_delete_response()

    def _get_response(self) -> None:
        """
        ### Summary
        Handle GET responses from the controller and set self._result.
        -	self._result is a dict containing:
            -   found:
                    -   False, if response:
                            - MESSAGE == "Not found" and
                            - RETURN_CODE == 404
                    -   True otherwise
            -   success:
                    -   False if response:
                            - RETURN_CODE != 200 or
                            - MESSAGE != "OK"
                    -   True otherwise
        """
        result: dict[str, bool] = {}
        if self.response is None:
            msg = f"{self.class_name}._get_response: "
            msg += "response must be set prior to calling "
            msg += f"{self.class_name}._get_response"
            self.log.error(msg)
            raise ValueError(msg)

        if (
            self.response.get("RETURN_CODE") == 404
            and self.response.get("MESSAGE") == "Not Found"
        ):
            result["found"] = False
            result["success"] = True
        elif (
            self.response.get("RETURN_CODE") not in self._return_codes_success
            or self.response.get("MESSAGE") != "OK"
        ):
            result["found"] = False
            result["success"] = False
        else:
            result["found"] = True
            result["success"] = True
        self._result = copy.copy(result)

    def _post_put_delete_response(self) -> None:
        """
        ### Summary
        Handle POST, PUT, DELETE responses from the controller and set
        self._result.
        -	self._result is a dict containing:
            -   changed:
                - True if changes were made by the controller
                    - ERROR key is not present
                    - MESSAGE == "OK"
                - False otherwise
            -   success:
                -   False if response:
                    - MESSAGE != "OK" or
                    - ERROR key is present
                -   True otherwise
        """
        method_name: str = inspect.stack()[0][3]
        result: dict[str, bool] = {}
        if self.response is None:
            msg = f"{self.class_name}.{method_name}: "
            msg += "response must be set prior to calling "
            msg += f"{self.class_name}.{method_name}"
            self.log.error(msg)
            raise ValueError(msg)
        if self.response.get("ERROR") is not None:
            result["success"] = False
            result["changed"] = False
        elif (
            self.response.get("MESSAGE") != "OK"
            and self.response.get("MESSAGE") is not None
        ):
            result["success"] = False
            result["changed"] = False
        else:
            result["success"] = True
            result["changed"] = True
        self._result = copy.copy(result)

    def commit(self) -> None:
        """
        # Summary

        Parse the response from the controller and set self._result
        based on the response.

        ## Raises

        -   ``ValueError`` if:
                -   ``response`` is not set.
                -   ``verb`` is not set.
        """
        method_name: str = inspect.stack()[0][3]
        msg = f"{self.class_name}.{method_name}: "
        msg += f"verb: {self.verb}, "
        msg += f"response {self.response}"
        self.log.debug(msg)
        if not self.response:
            msg = f"{self.class_name}.{method_name}: "
            msg += f"{self.class_name}.response must be set prior to calling "
            msg += f"{self.class_name}.{method_name}"
            raise ValueError(msg)
        if not self.verb:
            msg = f"{self.class_name}.{method_name}: "
            msg += f"{self.class_name}.verb must be set prior to calling "
            msg += f"{self.class_name}.{method_name}"
            raise ValueError(msg)
        self._handle_response()

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
    def response(self) -> dict[str, Any]:
        """
        # Summary

        The controller response.

        ## Raises

        -   setter: ``TypeError`` if:
                -   ``response`` is not a dict.
        -   setter: ``ValueError`` if:
                -   ``response`` is missing any fields required by the handler
                    to calculate the result.
                -   Required fields:
                        -   ``RETURN_CODE``
                        -   ``MESSAGE``

        """
        return self._response

    @response.setter
    def response(self, value: dict[str, Any]) -> None:
        method_name: str = inspect.stack()[0][3]
        if not isinstance(value, dict):
            msg = f"{self.class_name}.{method_name}: "
            msg += f"{self.class_name}.{method_name} must be a dict. "
            msg += f"Got {value}."
            raise TypeError(msg)
        if value.get("MESSAGE", None) is None:
            msg = f"{self.class_name}.{method_name}: "
            msg += "response must have a MESSAGE key. "
            msg += f"Got: {value}."
            raise ValueError(msg)
        if value.get("RETURN_CODE", None) is None:
            msg = f"{self.class_name}.{method_name}: "
            msg += "response must have a RETURN_CODE key. "
            msg += f"Got: {value}."
            raise ValueError(msg)
        self._response = value

    @property
    def result(self) -> dict[str, bool]:
        """
        -   getter: Return result.
        -   setter: Set result.
        -   setter: Raise ``TypeError`` if result is not a dict.
        """
        return self._result

    @property
    def verb(self) -> str:
        """
        ### Summary
        The request verb.

        ### Raises
        -   setter: ``ValueError`` if:
                -   ``verb`` is not valid.
                -   Valid verbs: "DELETE", "GET", "POST", "PUT".

        ### getter
        Internal interface that returns the request verb.

        ### setter
        External interface to set the request verb.
        """
        return self._verb

    @verb.setter
    def verb(self, value: str) -> None:
        method_name: str = inspect.stack()[0][3]
        if value not in self._valid_verbs:
            msg = f"{self.class_name}.{method_name}: "
            msg += "verb must be one of "
            msg += f"{', '.join(sorted(self._valid_verbs))}. "
            msg += f"Got {value}."
            raise ValueError(msg)
        self._verb = value
