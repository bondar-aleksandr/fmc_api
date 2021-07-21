import asa_api
import settings
import logging
from logging.handlers import RotatingFileHandler
import fmc_api


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



# def get_id(obj_list:list[dict], obj_type: str) -> None:
#     api_host = f"/api/fmc_config/v1/domain/{fmc.domain_uuid}/object/{obj_type}"
#     url = settings.SERVER + api_host
#     r = requests.get(url, headers=fmc.headers, verify=False)
#     obj_amount = r.json()['paging']['count']
#     params = {'limit': obj_amount}
#     r = requests.get(url, headers=fmc.headers, verify=False, params=params)
#     try:
#         for i in r.json()['items']:
#             for j in obj_list:
#                 if j['name'] == i['name']:
#                     j['id'] = i['id']
#                     break
#     except KeyError:
#         pass


def main():
    logging.info('!!! Nested object-groups are not supported (group-object command inside object-group is ignored). Please add it manually!!!\n')

    fmc = fmc_api.FMC()
    try:
        fmc.connect()
    except fmc_api.ConnError:
        exit()

    asa = asa_api.Asa()
    try:
        asa.read()
    except asa_api.ConfigFileError:
        exit()

    network_obj_list = asa.parse_netw_obj()

    for obj in network_obj_list:
        obj['id'] = fmc.post_objects(item=obj, item_type='object')

    # TODO: create model class, where data for posting is stored

    network_obj_group_list = asa.parse_netw_obj_groups()

    for obj_group in network_obj_group_list:
        fmc.post_objects(item=obj_group, item_type='object-group')
    logging.info('Done!')

if __name__ == '__main__':
    main()