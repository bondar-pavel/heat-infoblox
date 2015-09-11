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

import copy
import mock

from oslo_config import cfg

cfg.CONF.import_opt('plugin_dirs', 'heat.common.config')
cfg.CONF.set_override('plugin_dirs', '/opt/stack/heat-infoblox/heat_infoblox')

from heat.engine import stack
from heat.engine import template
from heat.tests import common
from heat.tests import utils
from heat_infoblox.resources import grid_member


grid_member_template = {
    'heat_template_version': '2013-05-23',
    'resources': {
        'my_member': {
            'type': 'Infoblox::Grid::Member',
            'properties': {
                'name': 'my-name',
                'wapi_url': 'https://127.0.0.1/wapi/v2.2/',
                'gm_ip': '10.1.1.2',
                'gm_certificate': 'testing',
                'LAN1': 'abc123'
            }
        }
    }
}


class GridMemberTest(common.HeatTestCase):
    def setUp(self):
        super(GridMemberTest, self).setUp()

        self.ctx = utils.dummy_context()
        self.set_stack(grid_member_template)

        self.base_member = {
            'host_name': 'host.name',
            'vip_setting': {
                'subnet_mask': '255.255.255.0',
                'address': '1.1.1.2',
                'gateway': '1.1.1.1'
            },
            'ipv6_setting': {
                'auto_router_config_enabled': False,
                'enabled': False
            }
        }

        self.ipv4_member = self.base_member.copy()
        self.ipv6_member = self.base_member.copy()
        self.ipv6_member.pop('vip_setting')

        self.ipv6_member['ipv6_setting'] = {
            'auto_router_config_enabled': False,
            'enabled': True,
            'cidr_prefix': 64,
            'gateway': '2001:db81::1',
            'virtual_ip': '2001:db81::4'
        }

        self.ipv4_6_member = self.base_member.copy()
        self.ipv4_6_member['ipv6_setting'] = self.ipv6_member['ipv6_setting']

    def set_stack(self, stack_template):
        self.stack = stack.Stack(
            self.ctx, 'grid_member_test_stack',
            template.Template(stack_template)
        )
        self.my_member = self.stack['my_member']
        self.my_member.infoblox_object = mock.MagicMock()
        self.my_member._get_member_tokens = mock.MagicMock()

    def set_member(self, mem):
        self.my_member.infoblox_object.get_member.return_value = [mem]

    def set_token(self, t):
        self.my_member._get_member_tokens.return_value = [
            {'token': t[0]},
            {'token': t[1]}
        ]

    def test_resource_mapping(self):
        mapping = grid_member.resource_mapping()
        self.assertEqual(1, len(mapping))
        self.assertEqual(grid_member.GridMember,
                         mapping['Infoblox::Grid::Member'])

    def test_user_data_lan1_ipv4(self):
        self.set_member(self.ipv4_member)
        self.set_token(['abcdefg', 'hijklmnop'])
        ud = self.my_member._resolve_attribute('user_data')
        self.assertEqual(
            '#infoblox-config\n\nlan1:\n'
            '  v4_addr: 1.1.1.2\n'
            '  v4_netmask: 255.255.255.0\n'
            '  v4_gw: 1.1.1.1\n'
            'gridmaster:\n'
            '  token: abcdefg\n'
            '  ip_addr: 10.1.1.2\n'
            '  certificate: testing\n',
            ud
        )

    def test_user_data_lan1_ipv6(self):
        self.set_member(self.ipv6_member)
        self.set_token(['abcdefg', 'hijklmnop'])
        ud = self.my_member._resolve_attribute('user_data')
        self.assertEqual(
            '#infoblox-config\n\nlan1:\n'
            '  v6_addr: 2001:db81::4\n'
            '  v6_cidr: 64\n'
            '  v6_gw: 2001:db81::1\n'
            'gridmaster:\n'
            '  token: abcdefg\n'
            '  ip_addr: 10.1.1.2\n'
            '  certificate: testing\n',
            ud
        )

    def test_user_data_lan1_ipv4_6(self):
        self.set_member(self.ipv4_6_member)
        self.set_token(['abcdefg', 'hijklmnop'])
        ud = self.my_member._resolve_attribute('user_data')
        self.assertEqual(
            '#infoblox-config\n\nlan1:\n'
            '  v4_addr: 1.1.1.2\n'
            '  v4_netmask: 255.255.255.0\n'
            '  v4_gw: 1.1.1.1\n'
            '  v6_addr: 2001:db81::4\n'
            '  v6_cidr: 64\n'
            '  v6_gw: 2001:db81::1\n'
            'gridmaster:\n'
            '  token: abcdefg\n'
            '  ip_addr: 10.1.1.2\n'
            '  certificate: testing\n',
            ud
        )

    def test_temp_licenses_none(self):
        self.set_member(self.base_member)
        self.set_token(['a', 'b'])
        ud = self.my_member._resolve_attribute('user_data')
        self.assertFalse('temp_license:' in ud)

    def test_temp_licenses_single(self):
        tmpl = copy.deepcopy(grid_member_template)
        props = tmpl['resources']['my_member']['properties']
        props['temp_licenses'] = ["vnios"]
        self.set_stack(tmpl)
        self.set_member(self.base_member)
        self.set_token(['a', 'b'])
        ud = self.my_member._resolve_attribute('user_data')
        self.assertTrue('temp_license: vnios\n' in ud)

    def test_temp_licenses_multiple(self):
        tmpl = copy.deepcopy(grid_member_template)
        props = tmpl['resources']['my_member']['properties']
        props['temp_licenses'] = ["vnios", "dns"]
        self.set_stack(tmpl)
        self.set_member(self.base_member)
        self.set_token(['a', 'b'])
        ud = self.my_member._resolve_attribute('user_data')
        self.assertTrue('temp_license: vnios,dns\n' in ud)

    def test_remote_console_enabled_none(self):
        self.set_member(self.base_member)
        self.set_token(['a', 'b'])
        ud = self.my_member._resolve_attribute('user_data')
        self.assertFalse('remote_console_enabled:' in ud)

    def test_remote_console_enabled_false(self):
        tmpl = copy.deepcopy(grid_member_template)
        props = tmpl['resources']['my_member']['properties']
        props['remote_console_enabled'] = False
        self.set_stack(tmpl)
        self.set_member(self.base_member)
        self.set_token(['a', 'b'])
        ud = self.my_member._resolve_attribute('user_data')
        self.assertTrue('remote_console_enabled: False\n' in ud)

    def test_remote_console_enabled_true(self):
        tmpl = copy.deepcopy(grid_member_template)
        props = tmpl['resources']['my_member']['properties']
        props['remote_console_enabled'] = True
        self.set_stack(tmpl)
        self.set_member(self.base_member)
        self.set_token(['a', 'b'])
        ud = self.my_member._resolve_attribute('user_data')
        self.assertTrue('remote_console_enabled: True\n' in ud)

    def test_admin_password_none(self):
        self.set_member(self.base_member)
        self.set_token(['a', 'b'])
        ud = self.my_member._resolve_attribute('user_data')
        self.assertFalse('default_admin_password:' in ud)

    def test_admin_password_set(self):
        tmpl = copy.deepcopy(grid_member_template)
        props = tmpl['resources']['my_member']['properties']
        props['admin_password'] = 'infoblox'
        self.set_stack(tmpl)
        self.set_member(self.base_member)
        self.set_token(['a', 'b'])
        ud = self.my_member._resolve_attribute('user_data')
        self.assertTrue('default_admin_password: infoblox\n' in ud)

    def test_handle_create(self):
        self.set_member(self.base_member)
        self.my_member.client = mock.MagicMock()
        self.my_member.resource_id = None
        self.my_member.handle_create()
        self.assertEqual('my-name', self.my_member.resource_id)

    def test_handle_delete_none(self):
        self.set_member(self.base_member)
        self.my_member.resource_id = None
        self.assertIsNone(self.my_member.handle_delete())

    def test_handle_delete(self):
        self.set_member(self.base_member)
        self.my_member.resource_id = 'myname'
        self.my_member.infoblox_object.delete_member.return_value = None
        self.assertIsNone(self.my_member.handle_delete())