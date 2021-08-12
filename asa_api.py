import json

import settings
import logging
import re
import ipaddress
from ciscoconfparse import CiscoConfParse, IOSCfgLine


class ConfigFileError(Exception):
    pass


class Asa:
    def __init__(self, config_file = settings.ASA_CONFIG):
        self.config_file = config_file
        self.config = None
        self.config_elements = {}

    def read(self):
        try:
            with open(self.config_file, 'rt') as f:
                self.config = CiscoConfParse(f.readlines(), syntax='asa')
        except FileNotFoundError:
            logging.error('Config file not found!')
            raise ConfigFileError('Config file not found!')

    def print_(self):
        print(json.dumps(self.config_elements, indent=4))

    def parse_serv_obj(self) -> dict:
        result = {}
        for serv_obj in self.config.find_objects(r'object service'):
            serv_obj: IOSCfgLine
            element = {}
            name = serv_obj.re_match_typed('^object service (\S+)')
            for child in serv_obj.children:
                if child.re_match_typed('description (\S+)'):
                    continue
                protocol = child.re_match_typed('service (\S+)')
                if not protocol.isdigit():
                    protocol = settings.protocol_mapping[protocol]
                element['protocol'] = protocol
                if protocol == '1':
                    element['type'] = 'ICMPv4PortLiteral'
                    if child.re_match_typed('service \S+ (\S+)'):
                        icmp_type = child.re_match_typed('service \S+ (\S+)')
                        if not icmp_type.isdigit():
                            icmp_type = settings.imcp_codes[icmp_type]
                        element['icmpType'] = icmp_type
                else:
                    element['type'] = 'PortLiteral'
                    if child.re_match_typed('service \S+ (\S+)'):
                        direction = child.re_match_typed('service \S+ (\S+)')
                        element['direction'] = direction
                        operator_ = child.re_match_typed('service \S+ \S+ (\S+)')
                        port = child.re_match_typed('service \S+ \S+ \S+ (\S+)')
                        if not port.isdigit():
                            port = settings.port_mapping[port]
                        elif operator_ == 'gt':
                            port = f'{port}-65535'
                        elif operator_ == 'lt':
                            port = f'0-{port}'
                        elif operator_ == 'range':
                            port_start = port
                            port_stop = child.re_match_typed('service \S+ \S+ \S+ \S+ (\S+)')
                            if not port_stop.isdigit():
                                port_stop = settings.port_mapping[port_stop]
                            port = f'{port_start}-{port_stop}'
                        element['port'] = port
            result[name] = element
        self.config_elements['object_service'] = result
        return result

    def parse_serv_obj_group(self):
        result = {}

        for serv_obj_group in self.config.find_objects(r'object-group service'):
            serv_obj_group: IOSCfgLine
            # for tcp/udp service-groups
            serv_obj_gr_type = serv_obj_group.re_match_typed('^object-group service \S+ (\S+)')
            if serv_obj_gr_type in ['tcp', 'udp', 'tcp-udp']:
                pass
            # for regular service-groups
            else:
                name = serv_obj_group.re_match_typed('^object-group service (\S+)')
                result[name] = {}
                result[name]['destinationPorts'] = {}
                result[name]['destinationPorts']['literals'] = []
                result[name]['sourcePorts'] = {}
                result[name]['sourcePorts']['literals'] = []

                for child in serv_obj_group.children:
                    child: IOSCfgLine
                    if child.re_match_typed('description (\S+)'):
                        continue
                    if child.re_match_typed('service-object object (\S+)'):
                        serv_obj = child.re_match_typed('service-object object (\S+)')
                        element = {}
                        element['type'] = self.config_elements['object_service'][serv_obj]['type']
                        element['protocol'] = self.config_elements['object_service'][serv_obj]['protocol']
                        element['port'] = self.config_elements['object_service'][serv_obj]['port']
                        if self.config_elements['object_service'][serv_obj]['direction'] == 'destination':
                            result[name]['destinationPorts']['literals'].append(element)
                        elif self.config_elements['object_service'][serv_obj]['direction'] == 'source':
                            result[name]['sourcePorts']['literals'].append(element)
                    elif child.re_match_typed('service-object (\S+)'):
                        element = {}
                        protocol = child.re_match_typed('-object (\S+)')
                        if not protocol.isdigit():
                            protocol = settings.protocol_mapping[protocol]
                        element['protocol'] = protocol
                        if protocol == '1':
                            element['type'] = 'ICMPv4PortLiteral'
                            if child.re_match_typed('-object \S+ (\S+)'):
                                icmp_type = child.re_match_typed('-object \S+ (\S+)')
                                if not icmp_type.isdigit():
                                    icmp_type = settings.imcp_codes[icmp_type]
                                element['icmpType'] = icmp_type
                        else:
                            element['type'] = 'PortLiteral'
                            element['protocol'] = protocol
                            if child.re_match_typed('-object \S+ (\S+)'):
                                direction = child.re_match_typed('-object \S+ (\S+)')
                                operator_ = child.re_match_typed('-object \S+ \S+ (\S+)')
                                port = child.re_match_typed('-object \S+ \S+ \S+ (\S+)')
                                if not port.isdigit():
                                    port = settings.port_mapping[port]
                                elif operator_ == 'gt':
                                    port = f'{port}-65535'
                                elif operator_ == 'lt':
                                    port = f'0-{port}'
                                elif operator_ == 'range':
                                    port_start = port
                                    port_stop = child.re_match_typed('-object \S+ \S+ \S+ \S+ (\S+)')
                                    if not port_stop.isdigit():
                                        port_stop = settings.port_mapping[port_stop]
                                    port = f'{port_start}-{port_stop}'
                                element['port'] = port
                                if direction == 'destination':
                                    result[name]['destinationPorts']['literals'].append(element)
                                elif direction == 'source':
                                    result[name]['sourcePorts']['literals'].append(element)
                                else:
                                    result[name]['destinationPorts']['literals'].append(element)
        self.config_elements['object-group_service'] = result
        return result

    def parse_netw_obj(self) -> dict:
        result = {}
        for netw_obj in self.config.find_objects(r'^object network'):
            netw_obj: IOSCfgLine
            element = {}
            name = netw_obj.re_match_typed('^object network (\S+)')
            element['name'] = name
            for child in netw_obj.children:
                child: IOSCfgLine
                if child.re_match_typed('description (.*)'):
                    element['description'] = child.re_match_typed('description (.*)').strip()
                elif child.re_match_typed('subnet (\S+)'):
                    element['type'] = 'subnet'
                    ip = child.re_match_typed(r' subnet (\S+) ')
                    mask = child.re_match_typed(r' subnet \S+ (\S+)')
                    element['value'] = ipaddress.ip_network(f'{ip}/{mask}').exploded
                elif child.re_match_typed('host (\S+)'):
                    element['type'] = 'host'
                    element['value'] = child.re_match_typed('host (\S+)')
                elif child.re_match_typed('range (\S+)'):
                    element['type'] = 'range'
                    start_val = child.re_match_typed('range (\S+)')
                    stop_val = child.re_match_typed('range \S+ (\S+)')
                    element['value'] = f'{start_val}-{stop_val}'
                elif child.re_match_typed('fqdn (\S+)'):
                    element['type'] = 'fqdn'
                    element['value'] = child.re_match_typed('fqdn (\S+)')
                    element['dnsResolution'] = 'IPV4_ONLY'
            result[name] = element
        self.config_elements['object_network'] = result
        return result

    def parse_netw_obj_groups(self) -> dict:
        result = {}
        for netw_obj_group in self.config.find_objects(r'^object-group network'):
            netw_obj_group: IOSCfgLine
            element = {}
            name = netw_obj_group.re_match_typed('^object-group network (\S+)')
            element['name'] = name
            element['type'] = 'NetworkGroup'
            element['objects'] = []
            element['literals'] = []
            for child in netw_obj_group.children:
                child: IOSCfgLine
                literal = {}
                object_ = {}
                if child.re_match_typed(r'description (\S+)'):
                    element['description'] = child.re_match_typed(r'description (.*)').strip()
                elif child.re_match_typed(r'^ network-object object (\S+)'):
                    object_['name'] = child.re_match_typed(r' object (\S+)')
                    element['objects'].append(object_)
                elif child.re_match_typed(r' network-object (\d+\.)'):
                    literal['type'] = 'Network'
                    ip = child.re_match_typed(r' network-object (\S+) ')
                    mask = child.re_match_typed(r' network-object \S+ (\S+)')
                    literal['value'] = ipaddress.ip_network(f'{ip}/{mask}').exploded
                    element['literals'].append(literal)
                elif child.re_match_typed(r' network-object host (\S+)'):
                    literal['type'] = 'Host'
                    literal['value'] = child.re_match_typed(r' network-object host (\S+)')
                    element['literals'].append(literal)
            result[name] = element
        self.config_elements['object-group_network'] = result
        return result



"""
    def parse_netw_obj(self) -> list:

        network_obj = []
        # switch variable used in order to distinguish between network and service objects in config
        switch = ''
        logging.info('Parsing network objects...')

        for line in self.config:

            if re.match(r'object network \S+', line):
                # assign switch to type "network"
                switch = 'n'
                element = {}
                match = re.match(r'object network (?P<name>\S+)', line)
                element['name'] = match.group('name')
                element["overridable"] = True
                network_obj.append(element)

            elif (line.startswith(' host') or line.startswith(' subnet') or line.startswith(
                    ' range') or line.startswith(' fqdn')) and network_obj:
                if line.startswith(' subnet '):
                    match = re.match(r' subnet (?P<network>\S+) (?P<mask>\S+)', line)
                    network_obj[-1]['type'] = 'Network'
                    network_obj[-1]['value'] = ipaddress.ip_network(
                        f"{match.group('network')}/{match.group('mask')}").exploded
                elif line.startswith(' host '):
                    match = re.match(r' host (?P<host>\S+)', line)
                    network_obj[-1]['type'] = 'Host'
                    network_obj[-1]['value'] = match.group('host')
                elif line.startswith(' range '):
                    match = re.match(r' range (?P<start>\S+) (?P<stop>\S+)', line)
                    network_obj[-1]['type'] = 'Range'
                    network_obj[-1]['value'] = match.group('start') + '-' + match.group('stop')
                elif line.startswith(' fqdn '):
                    match = re.match(r' fqdn \S+ (?P<fqdn>\S+)', line)
                    network_obj[-1]['type'] = 'FQDN'
                    network_obj[-1]['value'] = match.group('fqdn')
                    network_obj[-1]['dnsResolution'] = 'IPV4_ONLY'

            # dummy rule only for switching object-type
            elif re.match(r'object service \S+', line):
                # assign switch to type "service"
                switch = 's'
            elif line.startswith(' description '):
                match = re.match(r' description (?P<desc>.+)$', line)
                if switch == 'n':
                    network_obj[-1]['description'] = match.group('desc')
                elif switch == 's':
                    pass
            elif re.match(r'object-group', line) and network_obj:
                break
        self.network_obj = network_obj
        return network_obj


    def parse_netw_obj_groups(self) -> list:

        network_obj_groups = []
        logging.info('Parsing network objects-groups...')

        for line in self.config:
            element = {}
            if re.match(r'object-group network \S+', line):
                match = re.match(r'object-group network (?P<name>\S+)', line)
                element['name'] = match.group('name')
                element["overridable"] = True
                element['type'] = 'NetworkGroup'
                element['literals'] = []
                element['objects'] = []

                network_obj_groups.append(element)

            elif line.startswith(' network-object') and network_obj_groups:
                if re.match(r' network-object \d+\.', line):
                    match = re.match(r' network-object (?P<network>\S+) (?P<mask>\S+)', line)
                    literal = {}
                    literal['type'] = 'Network'
                    literal['value'] = ipaddress.ip_network(f"{match.group('network')}/{match.group('mask')}").exploded
                    network_obj_groups[-1]['literals'].append(literal)
                elif re.match(r' network-object host', line):
                    match = re.match(r' network-object host (?P<host>\S+)', line)
                    literal = {}
                    literal['type'] = 'Host'
                    literal['value'] = match.group('host')
                    network_obj_groups[-1]['literals'].append(literal)
                elif re.match(r' network-object object', line):
                    match = re.match(r' network-object object (?P<obj_name>\S+)', line)
                    obj_name = match.group('obj_name')
                    for i in self.network_obj:
                        if i['name'] == obj_name:
                            obj_id = i['id']
                            obj_type = i['type']
                            break
                    obj = {}
                    obj['id'] = obj_id
                    obj['type'] = obj_type
                    network_obj_groups[-1]['objects'].append(obj)
            elif re.match(r'access-list', line) and network_obj_groups:
                break

        return network_obj_groups
"""

asa = Asa()
asa.read()
asa.parse_netw_obj()
asa.parse_netw_obj_groups()
asa.parse_serv_obj()
asa.parse_serv_obj_group()
asa.print_()