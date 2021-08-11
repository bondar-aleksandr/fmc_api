import json
import ipaddress
from ciscoconfparse import CiscoConfParse, IOSCfgLine
import settings


def parse_serv_obj(config)->dict:
    result = {}
    for serv_obj in config.find_objects(r'object service'):
        serv_obj: IOSCfgLine
        element = {}
        name = serv_obj.re_match_typed('^object service (\S+)')
        for child in serv_obj.children:
            if child.re_match_typed('service (\S+)'):
                protocol_raw = child.re_match_typed('service (\S+)')
                protocol = settings.protocol_mapping[protocol_raw]
                element['protocol'] = protocol
                if child.re_match_typed('service \S+ (\S+)'):
                    direction_raw = child.re_match_typed('service \S+ (\S+)')
                    if direction_raw == 'destination':
                        direction = 'dst'
                    elif direction_raw == 'source':
                        direction = 'src'
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
    return result


def parse_serv_obj_group(config):
    result = {}
    for serv_obj_group in config.find_objects(r'object-group service'):
        serv_obj_group: IOSCfgLine
        element = {}
        name = serv_obj_group.re_match_typed('^object-group service (\S+)')
        #for tcp/udp service-groups
        if serv_obj_group.re_match_typed('^object-group service \S+ (\S+)'):
            pass
        else:
            for child in serv_obj_group.children:
                child: IOSCfgLine
                if child.re_match_typed('service-object object (\S+)'):
                    pass



def parse_netw_obj(config)->dict:
    result = {}
    for netw_obj in config.find_objects(r'^object network'):
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
    return result


def parse_netw_obj_groups(config)->dict:
    result = {}
    for netw_obj_group in config.find_objects(r'^object-group network'):
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
    return result


def main():
    try:
        with open(settings.ASA_CONFIG, 'r') as f:
            config = f.readlines()
    except FileNotFoundError:
        print('No config file!')
        exit()
    else:
        config_elements = {}
        config_elements['object_network'] = []
        config_elements['object-group_network'] = []
        config_elements['object_service'] = {}
        config_elements['object-group_service'] = {}
        parsed_config = CiscoConfParse(config, syntax='asa')
        config_elements['object_service'] = parse_serv_obj(config=parsed_config)
        config_elements['object_network'] = parse_netw_obj(config=parsed_config)
        config_elements['object-group_network'] = parse_netw_obj_groups(config=parsed_config)
        print(json.dumps(config_elements, indent=4))


if __name__ == '__main__':
    main()
