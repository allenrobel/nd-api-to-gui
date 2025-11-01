# Copyright (c) 2025 Cisco and/or its affiliates.
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
Retrieve from the controller a template's parameter list.
"""
from __future__ import absolute_import, division, print_function

__metaclass__ = type  # pylint: disable=invalid-name
__author__ = "Allen Robel"

import copy
import inspect
import logging
from typing import Any

from nd_api_to_gui.ep_templates import EpTemplates
from nd_api_to_gui.exceptions import ControllerResponseError
from nd_api_to_gui.rest_send_v2 import RestSend
from nd_api_to_gui.results_v2 import Results


class TemplateNames:
    """
    # Summary

    Retrieve from the controller a list of template names supported by the controller.

    ## Usage

    ```python
    instance = TemplateNames()
    instance.rest_send = rest_send_instance
    instance.refresh()
    template_names = instance.template_names
    ```

    `instance.template_names` will be a list of template names.

    ## Example instance.template_names

    ```json
    [
        "Easy_Fabric",
        "MSD_Fabric",
        ...
    ]
    ```

    ## Endpoint

    ### Path

    `/appcenter/cisco/ndfc/api/v1/configtemplate/rest/config/templates`

    ### Verb

    `GET`
    """

    def __init__(self) -> None:
        self.class_name: str = self.__class__.__name__

        self.log: logging.Logger = logging.getLogger(f"dcnm.{self.class_name}")

        msg = "ENTERED TemplateNames(): "
        self.log.debug(msg)

        self.ep_templates: EpTemplates = EpTemplates()

        self._response: list[dict[str, Any]] = []
        self.response_current: dict[str, Any] = {}
        self._result: list[dict[str, Any]] = []
        self.result_current: dict[str, Any] = {}

        self._rest_send: RestSend = RestSend({})
        self._results: Results = Results()
        self._template_names: list[str] = []

    def refresh(self) -> None:
        """
        # Summary

        -   Retrieve the template names from the controller.
        -   Populate the instance.template_names property.

        # Raises

        -   `ControllerResponseError` if the controller `RETURN_CODE` != 200
        """
        method_name: str = inspect.stack()[0][3]

        if self.rest_send is None:
            msg = f"{self.class_name}.{method_name}: "
            msg += "Set instance.rest_send property before calling instance.refresh()"
            self.log.debug(msg)
            raise ValueError(msg)

        self.rest_send.path = self.ep_templates.path
        self.rest_send.verb = self.ep_templates.verb
        self.rest_send.check_mode = False
        self.rest_send.timeout = 2
        self.rest_send.commit()

        self.response_current = copy.deepcopy(self.rest_send.response_current)
        self.result_current = copy.deepcopy(self.rest_send.result_current)
        self._response.append(copy.deepcopy(self.rest_send.response_current))
        self._result.append(copy.deepcopy(self.rest_send.result_current))

        controller_return_code = self.response_current.get("RETURN_CODE", None)
        controller_message = self.response_current.get("MESSAGE", None)
        if controller_return_code != 200:
            msg = f"{self.class_name}.{method_name}: "
            msg += "Failed to retrieve template_names. "
            msg += f"RETURN_CODE: {controller_return_code}. "
            msg += f"MESSAGE: {controller_message}."
            self.log.error(msg)
            raise ControllerResponseError(msg)

        self._template_names = [
            item.get("name") for item in self.response_current.get("DATA", [])
        ]

    @property
    def rest_send(self) -> RestSend:
        """
        # Summary

        An instance of the RestSend class.

        ## Raises

        -   setter: `ValueError` if RestSend.params is not set.
        """
        return self._rest_send

    @rest_send.setter
    def rest_send(self, value: RestSend) -> None:
        method_name: str = inspect.stack()[0][3]
        if not value.params:
            msg = f"{self.class_name}.{method_name}: "
            msg += "rest_send must have params set."
            raise ValueError(msg)
        self._rest_send = value

    @property
    def results(self) -> Results:
        """
        # Summary

        An instance of the Results class.
        """
        return self._results

    @results.setter
    def results(self, value: Results) -> None:
        self._results = value

    @property
    def template_names(self) -> list[str]:
        """
        # Summary

        Return the template names retrieved from the controller.

        ## Raises

        None
        """
        return self._template_names
