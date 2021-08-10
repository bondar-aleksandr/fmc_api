import json
import ipaddress

import ciscoconfparse
from ciscoconfparse import CiscoConfParse

parse = CiscoConfParse('asa_config.txt', syntax='asa')
config_elements = {}
config_elements['object_network'] = []
config_elements['object-group_network'] = []

for netw_obj in parse.find_objects(r'^object network'):
    netw_obj: ciscoconfparse.IOSCfgLine

    element = {}
    element['name'] = netw_obj.re_match_typed('^object network (\S+)')
    for child in netw_obj.children:
        child: ciscoconfparse.IOSCfgLine
        if child.re_match_typed('description (.*)'):
            element['description'] = child.re_match_typed('description (.*)')
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
    config_elements['object_network'].append(element)


for netw_obj_group in parse.find_objects(r'^object-group network'):
    netw_obj_group: ciscoconfparse.IOSCfgLine

    element = {}
    element['name'] = netw_obj_group.re_match_typed('^object-group network (\S+)')
    element['type'] = 'NetworkGroup'
    element['objects'] = []
    element['literals'] = []
    for child in netw_obj_group.children:
        child: ciscoconfparse.IOSCfgLine
        literal = {}
        object_ = {}
        if child.re_match_typed(r'description (\S+)'):
            element['description'] = child.re_match_typed(r'description (.*)')
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
    config_elements['object-group_network'].append(element)

print(json.dumps(config_elements, indent=4))





