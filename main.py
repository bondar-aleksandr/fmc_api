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

    asa_config = asa_api.AsaConfig()
    try:
        asa_config.read()
    except asa_api.ConfigFileError:
        exit()

    network_obj_list = asa_config.network_obj_parsing()

    # TODO: what for?
    # for obj_type in ['hosts', 'ranges', 'networks', 'fqdns']:
    #     get_id(obj_list=network_obj_list, obj_type=obj_type)

    fmc.post_objects(items=network_obj_list, item_type='object')
    network_obj_group_list = asa_config.network_obj_group_parsing()
    fmc.post_objects(items=network_obj_group_list, item_type='object-group')
    logging.info('Done!')

if __name__ == '__main__':
    main()