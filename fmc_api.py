import settings
import requests
import logging
import json


class FMC:
    def __init__(self, login=settings.FMC_LOGIN, password=settings.FMC_PASSWORD, host=settings.FMC_HOST):
        self.login = login
        self.password = password
        self.host = host


    def connect(self):
        requests.packages.urllib3.disable_warnings()

        self.headers = {'Content-Type': 'application/json'}
        logging.info(f'Connecting to FMC {settings.FMC_HOST}...')
        try:
            r = requests.post(settings.AUTH_URL, headers=self.headers,
                              auth=requests.auth.HTTPBasicAuth(self.login, self.password), verify=False)
            logging.info('...Connected! Auth token collected successfully')
        except Exception as err:
            logging.error(f"Error in generating auth token --> {str(err)} !")
            raise ConnectionError('Cannot get auth token!')

        else:
            self._auth_token = r.headers['X-auth-access-token']
            self.domain_uuid = r.headers['DOMAIN_UUID']
            self.headers['X-auth-access-token'] = self._auth_token


    def post_objects(self, items: list, item_type: str) -> None:

        for item in items:
            if item['type'] == 'Host':
                api_path = "/api/fmc_config/v1/domain/{}/object/hosts".format(self.domain_uuid)
            elif item['type'] == 'Range':
                api_path = "/api/fmc_config/v1/domain/{}/object/ranges".format(self.domain_uuid)
            elif item['type'] == 'Network':
                api_path = "/api/fmc_config/v1/domain/{}/object/networks".format(self.domain_uuid)
            elif item['type'] == 'FQDN':
                api_path = "/api/fmc_config/v1/domain/{}/object/fqdns".format(self.domain_uuid)
            elif item['type'] == 'NetworkGroup':
                api_path = "/api/fmc_config/v1/domain/{}/object/networkgroups".format(self.domain_uuid)
            else:
                raise ValueError('Wrong item type provided!')

            url = f'https://{self.host}' + api_path
            logging.info(f"Creating {item_type + item['name']}...")

            try:
                r = requests.post(url, data=json.dumps(item), headers=self.headers, verify=False)
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