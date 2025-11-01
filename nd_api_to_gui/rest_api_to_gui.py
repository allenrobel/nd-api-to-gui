#
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
# pylint: disable=too-many-instance-attributes, line-too-long
"""
Update fabric groups in bulk for replaced state
"""
from __future__ import absolute_import, division, print_function

__metaclass__ = type  # pylint: disable=invalid-name
__author__ = "Allen Robel"

import copy
import inspect
import logging
from typing import Any

from nd_api_to_gui.exceptions import ControllerResponseError
from nd_api_to_gui.operation_type import OperationType
from nd_api_to_gui.param_info_v2 import ParamInfo
from nd_api_to_gui.rest_send_v2 import RestSend
from nd_api_to_gui.results_v2 import Results
from nd_api_to_gui.template_get_v2 import TemplateGet


class RestApiToGui:
    """
    # Summary

    Build a translation mapping from REST API parameters to GUI field names
    for a template retrieved from the controller.

    ## Raises

    -   `ValueError` if:
        -   template_name is not set.
        -   `rest_send` is not set.
        -   `results` is not set.
        -   Unable to retrieve template from controller.

    ## Usage

    ```python
    from ansible_collections.cisco.dcnm.plugins.module_utils.common.rest_api_to_gui import RestApiToGui

    instance = RestApiToGui()
    instance.template_name = "my_template"
    instance.rest_send = rest_send  # An instance of RestSend with params set
    instance.results = Results()  # Optional: An instance of Results
    instance.commit()
    mapping = instance.mapping  # The mapping between REST API parameters and GUI field names (optional)
    for param_name in instance.parameter_names:
        instance.parameter_name = param_name
        display_name = instance.param_info.parameter_display_name  # Get display name for parameter
        section = instance.param_info.parameter_section  # Get section for parameter
    ```

    """

    def __init__(self) -> None:
        method_name = inspect.stack()[0][3]
        self.class_name = self.__class__.__name__
        self.log = logging.getLogger(f"dcnm.{self.class_name}")

        self.action = "rest_api_to_gui"
        self.operation_type: OperationType = OperationType.QUERY

        self._fabric_group_default_config: dict[str, Any] = {}
        self._fabric_group_name: str = ""
        self._parameter_name: str = ""
        self._parameter_names: list[str] = []
        self._param_info: ParamInfo = ParamInfo()
        self._refreshed: bool = False
        self._rest_api_parameter_to_gui_mapping: dict[str, dict[str, str]] = {}
        self._rest_send: RestSend = RestSend({})
        self._results: Results = Results()
        self._results.action = self.action
        self._results.operation_type = self.operation_type
        self._template: dict[str, Any] = {}
        self._template_get: TemplateGet = TemplateGet()
        self._template_name: str = ""

        msg = f"{self.class_name}.{method_name}: DONE"
        self.log.debug(msg)

    def commit(self) -> None:
        """
        # Summary

        Build the mapping between REST API parameters and GUI field names.

        ## Raises

        -   `ValueError` if:
            -   `template_name` is not set.
            -   `rest_send` is not set.
        """
        method_name = inspect.stack()[0][3]
        msg: str = ""
        if not self.template_name:
            msg = f"{self.class_name}.{method_name}: "
            msg += "template_name must be set."
            raise ValueError(msg)

        if not self.rest_send.params:
            msg = f"{self.class_name}.{method_name}: "
            msg += "rest_send must be set to an instance of RestSend with params set."
            raise ValueError(msg)

        self._build_rest_api_parameter_to_gui_mapping()
        self._parameter_names = list(self._rest_api_parameter_to_gui_mapping.keys())
        self._refreshed = True

    def _get_template(self) -> None:
        """
        # Summary

        Retrieve the template from the controller.

        ## Raises

        -   `ValueError` if unable to retrieve template from controller.
        """
        method_name = inspect.stack()[0][3]
        msg: str = f"{self.class_name}.{method_name}: "
        msg += f"Retrieving template: {self._template_name} from controller."
        self.log.debug(msg)

        self._template_get.rest_send = self.rest_send
        self._template_get.results = Results()
        self._template_get.template_name = self._template_name
        try:
            self._template_get.refresh()
        except ControllerResponseError as error:
            msg = f"{self.class_name}.{method_name}: "
            msg += f"Failed to retrieve template: {error}"
            self.log.error(msg)
            raise ValueError(msg) from error
        self._template = self._template_get.template

    def _set_parameter_names(self) -> None:
        """
        # Summary

        Build a list of parameter names from the template.

        ## Raises

        None
        """
        self._parameter_names = [
            param["name"] for param in self._template.get("parameters", [])
        ]

    def _parse_parameter_info(self) -> None:
        """
        Parse param info from the template.
        """
        self._param_info.template = copy.deepcopy(self._template)
        self._param_info.raise_on_missing = False
        self._param_info.refresh()

    def _skip(self, param_name: str) -> bool:
        """
        # Summary

        Determine if a parameter should be skipped.

        ## Raises

        None
        """
        if self._param_info.parameter_internal:
            return True
        if self._param_info.parameter_section == "Hidden":
            return True
        if "_PREV" in param_name:
            return True
        if "DCNM_ID" in param_name:
            return True
        return False

    def _build_mapping(self) -> None:
        """
        # Summary

        Build the mapping between REST API parameters and GUI field names.

        ## Raises

        None
        """
        self._rest_api_parameter_to_gui_mapping = {}
        for param_name in self._parameter_names:
            self._param_info.parameter_name = param_name
            if self._skip(param_name):
                continue
            if param_name not in self._rest_api_parameter_to_gui_mapping:
                self._rest_api_parameter_to_gui_mapping[param_name] = {}
            description = self._param_info.parameter_description
            display_name = self._param_info.parameter_display_name
            section = self._param_info.parameter_section
            if description:
                self._rest_api_parameter_to_gui_mapping[param_name][
                    "description"
                ] = description
            if display_name:
                self._rest_api_parameter_to_gui_mapping[param_name][
                    "display_name"
                ] = display_name
            if section:
                self._rest_api_parameter_to_gui_mapping[param_name]["section"] = section

    def _build_rest_api_parameter_to_gui_mapping(self) -> None:
        """
        # Summary

        Build the mapping between REST API parameters and GUI field names.

        ## Raises

        None
        """
        self._get_template()
        self._parse_parameter_info()
        self._set_parameter_names()
        self._build_mapping()

    @property
    def config(self) -> dict[str, Any]:
        """
        # Summary

        The fabric group default config.

        ## Raises

        None
        """
        return self._fabric_group_default_config

    @property
    def parameter_description(self) -> str:
        """
        # Summary

        Return the description of the current parameter.

        ## Raises

        None
        """
        method_name: str = inspect.stack()[0][3]
        if not self._refreshed:
            msg = f"{self.class_name}.{method_name}: "
            msg += f"Call {self.class_name}.commit before accessing {method_name}."
            raise ValueError(msg)
        if not self._parameter_name:
            msg = f"{self.class_name}.{method_name}: "
            msg += f"parameter_name must be set before accessing {method_name}."
            raise ValueError(msg)
        return (
            self._rest_api_parameter_to_gui_mapping.get(self._parameter_name, {}).get(
                "description"
            )
            or ""
        )

    @property
    def parameter_display_name(self) -> str:
        """
        # Summary

        Return the display name of the current parameter.

        ## Raises

        None
        """
        method_name: str = inspect.stack()[0][3]
        if not self._refreshed:
            msg = f"{self.class_name}.{method_name}: "
            msg += f"Call {self.class_name}.commit before accessing {method_name}."
            raise ValueError(msg)
        if not self._parameter_name:
            msg = f"{self.class_name}.{method_name}: "
            msg += f"parameter_name must be set before accessing {method_name}."
            raise ValueError(msg)
        return (
            self._rest_api_parameter_to_gui_mapping.get(self._parameter_name, {}).get(
                "display_name"
            )
            or ""
        )

    @property
    def parameter_name(self) -> str:
        """
        # Summary

        - getter: Return the parameter name to query.
        - setter: Set the parameter name to query.

        ## Raises

        None
        """
        return self._parameter_name

    @parameter_name.setter
    def parameter_name(self, value: str) -> None:
        self._parameter_name = value

    @property
    def parameter_names(self) -> list[str]:
        """
        # Summary

        Return a list of parameter names found in the mapping.

        ## Raises

        `ValueError` if:
            - commit has not been called (self._refreshed is False).
        """
        method_name: str = inspect.stack()[0][3]  # pylint: disable=unused-variable
        if not self._refreshed:
            msg = f"{self.class_name}.{method_name}: "
            msg += f"Call {self.class_name}.commit before accessing parameter_names."
            raise ValueError(msg)
        return sorted(list(self._parameter_names))

    @property
    def parameter_section(self) -> str:
        """
        # Summary

        Return the section (tab) in the GUI where the current parameter_name is located.

        ## Raises

        -  `ValueError` if:
            -   commit has not been called (self._refreshed is False).
            -   parameter_name is not set.
        """
        method_name: str = inspect.stack()[0][3]
        if not self._refreshed:
            msg = f"{self.class_name}.{method_name}: "
            msg += f"Call {self.class_name}.commit before accessing {method_name}."
            raise ValueError(msg)
        if not self._parameter_name:
            msg = f"{self.class_name}.{method_name}: "
            msg += f"parameter_name must be set before accessing {method_name}."
            raise ValueError(msg)
        return (
            self._rest_api_parameter_to_gui_mapping.get(self._parameter_name, {}).get(
                "section"
            )
            or ""
        )

    @property
    def rest_send(self) -> RestSend:
        """
        # Summary

        An instance of the RestSend class.

        ## Raises

        -   `ValueError` if `params` is not set on the RestSend instance.
        """
        return self._rest_send

    @rest_send.setter
    def rest_send(self, value: RestSend) -> None:
        if not value.params:
            msg = f"{self.class_name}.rest_send must be set to an "
            msg += "instance of RestSend with params set."
            raise ValueError(msg)
        self._rest_send = value

    @property
    def results(self) -> Results:
        """
        # Summary

        An instance of the Results class.

        ## Raises

        -  `ValueError` if the value passed to the setter is not an instance of Results.
        """
        return self._results

    @results.setter
    def results(self, value: Results) -> None:
        if not isinstance(value, Results):
            msg = f"{self.class_name}.results must be set to an "
            msg += "instance of Results."
            raise ValueError(msg)
        self._results = value
        self._results.action = self.action
        self._results.changed.add(False)
        self._results.operation_type = self.operation_type

    @property
    def template_name(self) -> str:
        """
        # Summary

        The name of the template to retrieve and translate.

        ## Raises

        None
        """
        return self._template_name

    @template_name.setter
    def template_name(self, value: str) -> None:
        self._template_name = value
