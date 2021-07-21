from typing import Union
import settings
import requests
import logging
import json

class ConnError(Exception):
    pass

class FMC:
    def __init__(self, login=settings.FMC_LOGIN, password=settings.FMC_PASSWORD, host=settings.FMC_HOST):
        self.login = login
        self.password = password
        self.host = host
        self.domain_uuid = None
        self._auth_token = None


    def connect(self):
        requests.packages.urllib3.disable_warnings()
        auth_url = f'https://{self.host}/api/fmc_platform/v1/auth/generatetoken'
        self.headers = {'Content-Type': 'application/json'}
        logging.info(f'Connecting to FMC {settings.FMC_HOST}...')
        try:
            r = requests.post(auth_url, headers=self.headers,
                              auth=requests.auth.HTTPBasicAuth(self.login, self.password), verify=False, timeout=5)
            logging.info('...Connected! Auth token collected successfully')
        except Exception as err:
            logging.error(f"Error in generating auth token --> {str(err)} !")
            raise ConnError('Cannot get auth token!')

        else:
            self._auth_token = r.headers['X-auth-access-token']
            self.domain_uuid = r.headers['DOMAIN_UUID']
            self.headers['X-auth-access-token'] = self._auth_token


    def post_objects(self, item: dict, item_type: str) -> Union[None,str]:

        # for item in items:
        api_path = f'/api/fmc_config/v1/domain/{self.domain_uuid}/object'

        if item['type'] == 'Host':
            api_path += "/hosts"
        elif item['type'] == 'Range':
            api_path += "/ranges"
        elif item['type'] == 'Network':
            api_path += "/networks"
        elif item['type'] == 'FQDN':
            api_path += "/fqdns"
        elif item['type'] == 'NetworkGroup':
            api_path += "/networkgroups"
        else:
            raise ValueError('Wrong item type provided!')

        url = f'https://{self.host}{api_path}'
        logging.info(f"Creating {item_type + item['name']}...")

        obj_id = None

        try:
            r = requests.post(url, data=json.dumps(item), headers=self.headers, verify=False)
            status_code = r.status_code
            resp = r.text
            if status_code == 201 or status_code == 202:
                obj_id = r.json()['id']
                logging.info(f"{item['name']} was successfully created!")
            elif status_code == 400:
                logging.warning(f"{item['name']} already exists!")
            else:
                r.raise_for_status()
                logging.error(f"{item['name']} encountered an error during POST --> {resp}")
        except requests.exceptions.HTTPError as err:
            logging.error(f"Error in connection --> {str(err)}")
            raise ConnError

        logging.info(f'POSTing of {item_type} is done!')
        return obj_id
