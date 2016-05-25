# Copyright (c) 2015 Infoblox Inc.
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

import logging
import netaddr

from heat.common.i18n import _
from heat.engine import attributes
from heat.engine import constraints
from heat.engine import properties
from heat.engine import resource
from heat.engine import support

from heat_infoblox import constants
from heat_infoblox import resource_utils


LOG = logging.getLogger(__name__)


class GridMember(resource.Resource):
    '''A resource which represents an Infoblox Grid Member.

    This is used to provision new grid members on an existing grid. See the
    Grid Master resource to create a new grid.
    '''

    PROPERTIES = (
        NAME, MODEL, LICENSES, TEMP_LICENSES,
        REMOTE_CONSOLE, ADMIN_PASSWORD,
        MGMT_PORT, LAN1_PORT, LAN2_PORT, HA_PORT,
        GM_IP, GM_CERTIFICATE,
        NAT_IP,
        # only 'enable' supported for now
        DNS_SETTINGS, DNS_ENABLE, DNS_RECURSIVE_RESOLVER, DNS_PORTS,
        DNS_ENABLE_FIXED_RRSET_ORDER_FQDNS, DNS_FIXED_RRSET_ORDER_FQDNS,
        DNS_USE_FIXED_RRSET_ORDER_FQDNS,
        DNS_DTC_HEALTH_SOURCE, DNS_DTC_HEALTH_SOURCE_ADDRESS,
        DNS_RPZ_QNAME_WAIT_RECURSE, DNS_USE_RPZ_QNAME_WAIT_RECURSE,
        DNS_LOG_DTC_GSLB, DNS_LOG_DTC_HEALTH, DNS_UNBOUND_LOGGING_LEVEL,
        ADDITIONAL_IP_LIST,
    ) = (
        'name', 'model', 'licenses', 'temp_licenses',
        'remote_console_enabled', 'admin_password',
        'MGMT', 'LAN1', 'LAN2', 'HA',
        'gm_ip', 'gm_certificate',
        'nat_ip',
        'dns', 'enable', 'recursive_resolver', 'ports',
        'enable_fixed_rrset_order_fqdns', 'fixed_rrset_order_fqdns',
        'use_fixed_rrset_order_fqdns',
        'dtc_health_source', 'dtc_health_source_address',
        'rpz_qname_wait_recurse', 'use_rpz_qname_wait_recurse',
        'log_dtc_glsb', 'log_dtc_health', 'unbound_logging_level',
        'additional_ip_list',
    )

    ATTRIBUTES = (
        USER_DATA,
        NAME_ATTR,
        DNS_UNBOUND_CAPABLE
    ) = (
        'user_data',
        'name',
        'is_unbound_capable'
    )

    ALLOWED_MODELS = (
        'CP-V1400',
        'CP-V2200',
        'CP-V800',
        'IB-VM-100',
        'IB-VM-1410',
        'IB-VM-1420',
        'IB-VM-2210',
        'IB-VM-2220',
        'IB-VM-4010',
        'IB-VM-810',
        'IB-VM-820',
        'IB-VM-RSP',
        'Rev1',
        'Rev2'
    )

    ALLOWED_LICENSES_PRE_PROVISION = (
        'cloud_api',
        'dhcp',
        'dns',
        'dtc',
        'enterprise',
        'fireeye',
        'ms_management',
        'rpz',
        'vnios')

    ALLOWED_LICENSES_TEMP = (
        'dns',
        'rpz',
        'cloud',
        'cloud_api',
        'enterprise',
        'ipam',
        'vnios',
        'reporting')

    support_status = support.SupportStatus(
        support.UNSUPPORTED,
        _('See support.infoblox.com for support.'))

    properties_schema = {
        constants.CONNECTION:
            resource_utils.connection_schema(constants.DDI),
        NAME: properties.Schema(
            properties.Schema.STRING,
            _('Member name.')),
        MODEL: properties.Schema(
            properties.Schema.STRING,
            _('Infoblox model name.'),
            constraints=[
                constraints.AllowedValues(ALLOWED_MODELS)
            ]),
        LICENSES: properties.Schema(
            properties.Schema.LIST,
            _('List of licenses to pre-provision.'),
            schema=properties.Schema(
                properties.Schema.STRING
            ),
            constraints=[
                constraints.AllowedValues(ALLOWED_LICENSES_PRE_PROVISION)
            ]),
        TEMP_LICENSES: properties.Schema(
            properties.Schema.LIST,
            _('List of temporary licenses to apply to the member.'),
            schema=properties.Schema(
                properties.Schema.STRING
            ),
            constraints=[
                constraints.AllowedValues(ALLOWED_LICENSES_TEMP)
            ]),
        REMOTE_CONSOLE: properties.Schema(
            properties.Schema.BOOLEAN,
            _('Enable the remote console.')),
        ADMIN_PASSWORD: properties.Schema(
            properties.Schema.STRING,
            _('The password to use for the admin user.')),
        GM_IP: properties.Schema(
            properties.Schema.STRING,
            _('The Gridmaster IP address.'),
            required=True),
        GM_CERTIFICATE: properties.Schema(
            properties.Schema.STRING,
            _('The Gridmaster SSL certificate for verification.'),
            required=False),
        NAT_IP: properties.Schema(
            properties.Schema.STRING,
            _('If the GM will see this member as a NATed address, enter that '
              'address here.'),
            required=False),
        MGMT_PORT: resource_utils.port_schema(MGMT_PORT, False),
        LAN1_PORT: resource_utils.port_schema(LAN1_PORT, True),
        LAN2_PORT: resource_utils.port_schema(LAN2_PORT, False),
        DNS_SETTINGS: properties.Schema(
            properties.Schema.MAP,
            _('The DNS settings for this member.'),
            required=False,
            schema={
                DNS_ENABLE: properties.Schema(
                    properties.Schema.BOOLEAN,
                    _('If true, enable DNS on this member.'),
                    default=False
                ),
                ADDITIONAL_IP_LIST: properties.Schema(
                    properties.Schema.LIST,
                    _('List of additional IP addresses on which DNS is '
                      'enabled for a Grid member.'),
                    schema=properties.Schema(
                        properties.Schema.STRING
                    ),
                    default=[]
                ),
            })
    }

    attributes_schema = {
        USER_DATA: attributes.Schema(
            _('User data for the Nova boot process.'),
            attributes.Schema.STRING),
        NAME_ATTR: attributes.Schema(
            _('The member name.'),
            attributes.Schema.STRING)
    }

    def _make_network_settings(self, ip):
        subnet = self.client('neutron').show_subnet(ip['subnet_id'])['subnet']
        ipnet = netaddr.IPNetwork(subnet['cidr'])
        return {
            'address': ip['ip_address'],
            'subnet_mask': str(ipnet.netmask),
            'gateway': subnet['gateway_ip']
        }

    def _make_ipv6_settings(self, ip):
        subnet = self.client('neutron').show_subnet(ip['subnet_id'])['subnet']
        prefix = netaddr.IPNetwork(subnet['cidr'])
        autocfg = subnet['ipv6_ra_mode'] == "slaac"
        return {
            'virtual_ip': ip['ip_address'],
            'cidr_prefix': int(prefix.prefixlen),
            'gateway': subnet['gateway_ip'], 'enabled': True,
            'auto_router_config_enabled': autocfg
        }

    def infoblox(self):
        if not getattr(self, 'infoblox_object', None):
            conn = self.properties[constants.CONNECTION]
            self.infoblox_object = resource_utils.connect_to_infoblox(conn)
        return self.infoblox_object

    def _make_port_network_settings(self, port_name):
        if self.properties[port_name] is None:
            return None

        port = self.client('neutron').show_port(
            self.properties[port_name])['port']

        if port is None:
            return None

        ipv4 = None
        ipv6 = None
        for ip in port['fixed_ips']:
            if ':' in ip['ip_address'] and ipv6 is None:
                ipv6 = self._make_ipv6_settings(ip)
            else:
                if ipv4 is None:
                    ipv4 = self._make_network_settings(ip)
        return {'ipv4': ipv4, 'ipv6': ipv6}

    def handle_create(self):
        mgmt = self._make_port_network_settings(self.MGMT_PORT)
        lan1 = self._make_port_network_settings(self.LAN1_PORT)
        lan2 = self._make_port_network_settings(self.LAN2_PORT)

        name = self.properties[self.NAME]
        nat = self.properties[self.NAT_IP]

        self.infoblox().create_member(name=name, mgmt=mgmt, lan1=lan1,
                                      lan2=lan2, nat_ip=nat)
        self.infoblox().pre_provision_member(
            name,
            hwmodel=self.properties[self.MODEL], hwtype='IB-VNIOS',
            licenses=self.properties[self.LICENSES])

        dns = self.properties[self.DNS_SETTINGS]
        if dns:
            self.infoblox().configure_member_dns(
                name,
                enable_dns=dns['enable'],
                additional_ip_list=dns[self.ADDITIONAL_IP_LIST],
            )

        self.resource_id_set(name)

    def _remove_from_all_ns_groups(self):
        # This is a workaround needed because Juno Heat does not honor
        # dependencies in nested autoscale group stacks.
        fields = {'name', 'grid_primary', 'grid_secondaries'}
        groups = self.infoblox().get_all_ns_groups(return_fields=fields)
        for group in groups:
            new_list = {}
            changed = False
            for field in ('grid_primary', 'grid_secondaries'):
                new_list[field] = []
                for member in group[field]:
                    if member['name'] != self.resource_id:
                        new_list[field].append(member)
                    else:
                        changed = True
            if changed:
                self.infoblox().update_ns_group(group['name'], new_list)

    def handle_delete(self):
        if self.resource_id is not None:
            self._remove_from_all_ns_groups()
            self.infoblox().delete_member(self.resource_id)

    def _make_user_data(self, member, token):
        user_data = '#infoblox-config\n\n'

        temp_licenses = self.properties[self.TEMP_LICENSES]
        if temp_licenses and len(temp_licenses) > 0:
            user_data += 'temp_license: %s\n' % ','.join(temp_licenses)

        remote_console = self.properties[self.REMOTE_CONSOLE]
        if remote_console is not None:
            user_data += 'remote_console_enabled: %s\n' % remote_console

        admin_password = self.properties[self.ADMIN_PASSWORD]
        if admin_password is not None:
            user_data += 'default_admin_password: %s\n' % admin_password

        vip = member.get('vip_setting', None)
        ipv6 = member.get('ipv6_setting', None)
        if ipv6 and not ipv6.get('enabled', False):
            ipv6 = None

        if vip or ipv6:
            user_data += 'lan1:\n'

        if vip:
            user_data += '  v4_addr: %s\n' % vip['address']
            user_data += '  v4_netmask: %s\n' % vip['subnet_mask']
            user_data += '  v4_gw: %s\n' % vip['gateway']

        if ipv6:
            user_data += '  v6_addr: %s\n' % ipv6['virtual_ip']
            user_data += '  v6_cidr: %s\n' % ipv6['cidr_prefix']
            if not ipv6['auto_router_config_enabled']:
                user_data += '  v6_gw: %s\n' % ipv6['gateway']

        if token and len(token) > 0:
            user_data += 'gridmaster:\n'
            user_data += '  token: %s\n' % token[0]['token']
            user_data += '  ip_addr: %s\n' % self.properties[self.GM_IP]
            user_data += '  certificate: |\n    %s\n' % self.properties[
                self.GM_CERTIFICATE
            ].replace('\n', '\n    ')

        LOG.debug('user_data: %s' % user_data)

        return user_data

    def _get_member_tokens(self, member):
        token = self.infoblox().connector.call_func(
            'read_token',
            member['_ref'], {})['pnode_tokens']
        if len(token) == 0:
            self.infoblox().connector.call_func(
                'create_token',
                member['_ref'], {})['pnode_tokens']
            token = self.infoblox().connector.call_func(
                'read_token',
                member['_ref'], {})['pnode_tokens']
        return token

    def _resolve_attribute(self, name):
        member_name = self.resource_id
        member = self.infoblox().get_member(
            member_name,
            return_fields=['host_name', 'vip_setting', 'ipv6_setting'])[0]
        token = self._get_member_tokens(member)
        LOG.debug("MEMBER for %s = %s" % (name, member))
        if name == self.USER_DATA:
            return self._make_user_data(member, token)
        if name == self.NAME_ATTR:
            return member['host_name']
        return None


def resource_mapping():
    return {
        'Infoblox::Grid::Member': GridMember,
    }
