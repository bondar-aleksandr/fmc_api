import settings
import logging
import re
import ipaddress

class ConfigFileError(Exception):
    pass


class AsaConfig:
    def __init__(self, config_file = settings.ASA_CONFIG):
        self.config_file = config_file
        self.config = None


    def read(self):
        try:
            with open(self.config_file, 'rt') as f:
                self.config = f.readlines()
        except FileNotFoundError:
            logging.error('Config file not found!')
            raise ConfigFileError('Config file not found!')


    def network_obj_parsing(self) -> list:

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

        self._network_obj = tuple(network_obj)
        return network_obj


    def network_obj_group_parsing(self) -> list:

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
                    for i in self._network_obj:
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

        self._network_obj_groups = tuple(network_obj_groups)
        return network_obj_groups