# Copyright (c) 2016 Infoblox Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from heat.common.i18n import _
from heat.engine import constraints
from heat.engine import properties

from heat_infoblox import connector
from heat_infoblox import constants
from heat_infoblox import object_manipulator

"""Utilities for specifying resources."""


def port_schema(port_name, is_required):
    return properties.Schema(
        properties.Schema.STRING,
        _('ID of an existing port to associate with the %s port.')
        % port_name,
        constraints=[
            constraints.CustomConstraint('neutron.port')
        ],
        required=is_required
    )

CONN_DESCR = {
    constants.NETMRI: {
        constants.URL: "The URL to the NetMRI API (example: "
                       "'https://netmri/api/3.0')",
        constants.USERNAME: 'The username for NetMRI.',
        constants.PASSWORD: 'The password for NetMRI.'
    },
    constants.DDI: {
        constants.URL: "The URL to the Infoblox WAPI (example: "
                       "'https://infoblox/wapi/v2.3')",
        constants.USERNAME: 'The username for Infoblox.',
        constants.PASSWORD: 'The password for Infoblox.'
    }
}


def connection_schema(conn_type):
    return properties.Schema(
        properties.Schema.MAP,
        required=True,
        schema={
            constants.URL: properties.Schema(
                properties.Schema.STRING,
                CONN_DESCR[conn_type][constants.URL],
                required=True
            ),
            constants.USERNAME: properties.Schema(
                properties.Schema.STRING,
                CONN_DESCR[conn_type][constants.USERNAME],
                required=True
            ),
            constants.PASSWORD: properties.Schema(
                properties.Schema.STRING,
                CONN_DESCR[conn_type][constants.PASSWORD],
                required=True
            ),
            constants.SSLVERIFY: properties.Schema(
                properties.Schema.BOOLEAN,
                _('If True, the SSL certificate will be validated.'),
                default=True
            )
        }
    )


def connect_to_infoblox(conn_params):
    return object_manipulator.InfobloxObjectManipulator(
        connector.Infoblox({'url': conn_params[constants.URL],
                            'username': conn_params[constants.USERNAME],
                            'password': conn_params[constants.PASSWORD],
                            'sslverify': conn_params[constants.SSLVERIFY]}))
