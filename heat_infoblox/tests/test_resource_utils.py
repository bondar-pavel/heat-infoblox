# Copyright 2015 Infoblox Inc.
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

import mock

from heat.tests import common

from heat_infoblox import config as cfg
from heat_infoblox import connector
from heat_infoblox import resource_utils


class ResourceUtilsTest(common.HeatTestCase):
    def setUp(self):
        super(ResourceUtilsTest, self).setUp()

    def test_wapi_config_file(self):

        for opt in ['wapi_url', 'username', 'password']:
            cfg.CONF.set_override(name=opt,
                                  override='test_%s' % opt,
                                  group='infoblox')

        cfg.CONF.set_override(name='sslverify',
                              override=False,
                              group='infoblox')
        connector.Infoblox = mock.MagicMock()
        resource_utils.connect_to_infoblox()
        connector.Infoblox.assert_called_with({'url': 'test_wapi_url',
                                               'username': 'test_username',
                                               'password': 'test_password',
                                               'sslverify': False})
