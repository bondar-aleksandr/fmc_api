import re
import ipaddress
import json
import typing
import requests
import os
import settings
import logging
from logging.handlers import RotatingFileHandler


rotating_file_handler = RotatingFileHandler(
    filename='./log/app.log',
    mode='a',
    maxBytes=settings.LOG_FILE_SIZE,
    backupCount=2,
    encoding='utf-8'
)
rotating_file_handler.setLevel(logging.DEBUG)

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)


logging.basicConfig(format=u'%(filename)s [LINE:%(lineno)d] #%(levelname)-8s [%(asctime)s]  %(message)s',
                    level=settings.LOGGING_LEVEL, handlers = [rotating_file_handler, stream_handler])



def get_id(obj_list:list[dict], obj_type: str) -> None:
    api_host = f"/api/fmc_config/v1/domain/{DOMAIN_UUID}/object/{obj_type}"
    url = settings.SERVER + api_host
    r = requests.get(url, headers=headers, verify=False)
    obj_amount = r.json()['paging']['count']
    params = {'limit': obj_amount}
    r = requests.get(url, headers=headers, verify=False, params=params)
    try:
        for i in r.json()['items']:
            for j in obj_list:
                if j['name'] == i['name']:
                    j['id'] = i['id']
                    break
    except KeyError:
        pass


def post_data(items: list, item_type: str) -> None:
    if not items:
        logging.info(f'No {item_type} found in configuration file!')
    for item in items:
        if item['type'] == 'Host':
            api_path = "/api/fmc_config/v1/domain/{}/object/hosts".format(DOMAIN_UUID)
        elif item['type'] == 'Range':
            api_path = "/api/fmc_config/v1/domain/{}/object/ranges".format(DOMAIN_UUID)
        elif item['type'] == 'Network':
            api_path = "/api/fmc_config/v1/domain/{}/object/networks".format(DOMAIN_UUID)
        elif item['type'] == 'FQDN':
            api_path = "/api/fmc_config/v1/domain/{}/object/fqdns".format(DOMAIN_UUID)
        elif item['type'] == 'NetworkGroup':
            api_path = "/api/fmc_config/v1/domain/{}/object/networkgroups".format(DOMAIN_UUID)
        else:
            raise ValueError('Wrong item type provided!')

        url = settings.FMC_HOST + api_path
        logging.info(f"Creating {item_type + item['name']}...")

        try:
            r = requests.post(url, data=json.dumps(item), headers=headers, verify=False)
            status_code = r.status_code
            resp = r.text

            if status_code == 201 or status_code == 202:
                obj_id = r.json()['id']
                item['id'] = obj_id
                logging.info(f"{item['name']} was successfully created!")
            elif status_code == 400:
                logging.warning(f"{item['name']} already exists!")
            else:
                r.raise_for_status()
                logging.error(f"{item['name']} encountered an error during POST --> {resp}")

        except requests.exceptions.HTTPError as err:
            logging.error(f"Error in connection --> {str(err)}")
    logging.info(f'POSTing of {item_type} is done!')


#========================================== ARGUMENTS ===========================================

print('!!! Nested object-groups are not supported (group-object command inside object-group is ignored). Please add it manually!!!\n')


#=========================Config-parsing, getting network objects=======================

def network_obj_parsing(configuration: list) -> typing.Union[list, None]:

    network_obj_list = []

    # switch variable used in order to distinguish between network and service objects in config
    switch = ''

    logging.info('Parsing network objects...')
    for line in configuration:

        if re.match(r'object network \S+', line):
            # assign switch to type "network"
            switch = 'n'
            element = {}
            match = re.match(r'object network (?P<name>\S+)', line)
            element['name'] =  match.group('name')
            element["overridable"] = True
            network_obj_list.append(element)

        elif (line.startswith(' host') or line.startswith(' subnet') or line.startswith(' range') or line.startswith(' fqdn')) and network_obj_list:
            if line.startswith(' subnet '):
                match = re.match(r' subnet (?P<network>\S+) (?P<mask>\S+)',line)
                network_obj_list[-1]['type'] = 'Network'
                network_obj_list[-1]['value'] = ipaddress.ip_network(f"{match.group('network')}/{match.group('mask')}").exploded
            elif line.startswith(' host '):
                match = re.match(r' host (?P<host>\S+)', line)
                network_obj_list[-1]['type'] = 'Host'
                network_obj_list[-1]['value'] = match.group('host')
            elif line.startswith(' range '):
                match = re.match(r' range (?P<start>\S+) (?P<stop>\S+)', line)
                network_obj_list[-1]['type'] = 'Range'
                network_obj_list[-1]['value'] = match.group('start') + '-' + match.group('stop')
            elif line.startswith(' fqdn '):
                match = re.match(r' fqdn \S+ (?P<fqdn>\S+)', line)
                network_obj_list[-1]['type'] = 'FQDN'
                network_obj_list[-1]['value'] = match.group('fqdn')
                network_obj_list[-1]['dnsResolution'] = 'IPV4_ONLY'

        #dummy rule only for switching object-type
        elif re.match(r'object service \S+', line):
            #assign switch to type "service"
            switch = 's'
        elif line.startswith(' description '):
            match = re.match(r' description (?P<desc>.+)$', line)
            if switch == 'n':
                network_obj_list[-1]['description'] = match.group('desc')
            elif switch == 's':
                pass
        elif re.match(r'object-group', line) and network_obj_list:
            break

    if network_obj_list:
        logging.info('Parsing network objects DONE')
        return network_obj_list
    else:
        logging.info('No network objects found in config!')


def network_obj_group_parsing(configuration: list) -> list:

    network_obj_group_list = []
    logging.info('Parsing network objects-groups...')

    for line in configuration:
        element = {}
        if re.match(r'object-group network \S+', line):
            match = re.match(r'object-group network (?P<name>\S+)', line)
            element['name'] =  match.group('name')
            element["overridable"] = True
            element['type'] = 'NetworkGroup'
            element['literals'] = []
            element['objects'] = []

            network_obj_group_list.append(element)

        elif line.startswith(' network-object') and network_obj_group_list:
            if re.match(r' network-object \d+\.',line):
                match = re.match(r' network-object (?P<network>\S+) (?P<mask>\S+)', line)
                literal = {}
                literal['type'] = 'Network'
                literal['value'] = ipaddress.ip_network(f"{match.group('network')}/{match.group('mask')}").exploded
                network_obj_group_list[-1]['literals'].append(literal)
            elif re.match(r' network-object host',line):
                match = re.match(r' network-object host (?P<host>\S+)', line)
                literal = {}
                literal['type'] = 'Host'
                literal['value'] = match.group('host')
                network_obj_group_list[-1]['literals'].append(literal)
            elif re.match(r' network-object object',line):
                match = re.match(r' network-object object (?P<obj_name>\S+)', line)
                obj_name = match.group('obj_name')
                for i in network_obj_list:
                    if i['name'] == obj_name:
                        obj_id = i['id']
                        obj_type = i['type']
                        break
                obj = {}
                obj['id'] = obj_id
                obj['type'] = obj_type
                network_obj_group_list[-1]['objects'].append(obj)
        elif re.match(r'access-list', line) and network_obj_group_list:
            break

    if network_obj_group_list:
        logging.info('Parsing network object-groups DONE')
        return network_obj_group_list
    else:
        print('No object-groups found in config!')


#=====================================API AUTH=========================================


# server = 'https://{}'.format(config.FMC_HOST)

# api_auth_path = "/api/fmc_platform/v1/auth/generatetoken"
# auth_url = config.SERVER + config.API_AUTH_PATH
headers = {'Content-Type': 'application/json'}

# To avoid SSL warning errors shown
requests.packages.urllib3.disable_warnings()
logging.info(f'Attempting connection to FMC {settings.FMC_HOST}...')
try:
    r = requests.post(settings.AUTH_URL, headers=headers, auth=requests.auth.HTTPBasicAuth(settings.FMC_LOGIN, settings.FMC_PASSWORD), verify=False)
    logging.info('...Connected! Auth token collected successfully')
except Exception as err:
    logging.error(f"Error in generating auth token --> {str(err)} !")
    exit()

AUTH_TOKEN = r.headers['X-auth-access-token']
DOMAIN_UUID = r.headers['DOMAIN_UUID']

#Add access-token header to headers
headers['X-auth-access-token'] = AUTH_TOKEN

try:
    with open(f'{settings.ASA_CONFIG}', 'rt') as f:
        asa_config = f.readlines()
except FileNotFoundError:
    logging.error('Config file not found!')
    exit()

network_obj_list = network_obj_parsing(configuration=asa_config)

#=====================================GET Objects if they exist=========================================

for obj_type in ['hosts', 'ranges', 'networks', 'fqdns']:
    get_id(obj_list=network_obj_list, obj_type=obj_type)

#=====================================Oject network POSTing=========================================

post_data(items=network_obj_list, item_type='object')

#=========================Config-parsing, getting network objects-groups=====================

network_obj_group_list = network_obj_group_parsing(configuration=asa_config)

#=====================================Network oject-groups POSTing=========================================

post_data(items=network_obj_group_list, item_type='object-group')
os.system('pause')
