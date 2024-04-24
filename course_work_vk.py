import requests
from datetime import datetime
import json
from tqdm import tqdm
import configparser

IDENTIFIER = input('Введите идентификатор или короткое имя пользователя: ')
COUNT_PHOTOS = int(input('Введите количество фотографий для загрузки: '))


class VKRecoveryService:  # Класс API VK для получения URL фотографий и формирования их имён
    def __init__(self):
        config = configparser.ConfigParser()
        config.read('access.ini')
        self.vk_token = config['VK']['vk_token']
        self.count_photos = COUNT_PHOTOS
        self.identifier = IDENTIFIER

    def get_id(self):  # Получаем ID пользователя по короткому имени или самому ID
        params = {
            'access_token': self.vk_token,
            'v': '5.199',
            'user_ids': self.identifier
        }
        response = requests.get('https://api.vk.com/method/users.get', params=params)
        if len(response.json()['response']) == 0:
            print('Пользователь не найден')
        else:
            return response.json()['response'][0]['id']

    def get_photos(self):
        params = {
            'access_token': self.vk_token,
            'v': '5.199',
            'album_id': 'profile',
            'owner_id': self.get_id(),
            'extended': 1,
            'count': self.count_photos,
        }
        response = requests.get('https://api.vk.com/method/photos.get', params=params)
        return response.json()['response']['items']

    def get_max_photo_urls(self):  # Создание списка с URL фотографий максимального качества
        url_list = []
        for photo in self.get_photos():
            if photo['sizes'][-1]['height'] == 0:  # Если фото загружены до 2012 года
                url_list.append(photo['sizes'][-1]['url'])
            else:  # Если фото загружены после 2012 года
                url_list.append(max(photo['sizes'], key=lambda x: x['height'] * x['width'])['url'])
        return url_list

    def get_photo_names(self):  # Создание имён фото с указанием количества лайков и даты загрузки
        name_list = []
        for photo_name in self.get_photos():
            name_list.append(f'{photo_name['likes']['count']}_'
                             f'{datetime.fromtimestamp(photo_name['date']).strftime('%d-%m-%Y')}')
        return name_list


vk_photos = VKRecoveryService().get_photos()
vk_photos_max_q = VKRecoveryService().get_max_photo_urls()
vk_photos_name = VKRecoveryService().get_photo_names()


class YADiskUploader:  # Класс Яндекс.Диска для загрузки фотографий в облачное хранилище
    def __init__(self):
        config = configparser.ConfigParser()
        config.read('access.ini')
        self.ya_oauth = config['Yandex']['ya_oauth']

    def upload_photos(self):
        headers = {
            'Authorization': f'OAuth {self.ya_oauth}'
        }
        for url, name in tqdm(zip(vk_photos_max_q, vk_photos_name),
                              total=len(vk_photos_max_q),
                              desc='Загрузка фотографий на Яндекс.Диск'):
            requests.put('https://cloud-api.yandex.net/v1/disk/resources',
                         headers=headers,
                         params={'path': 'VK_Images',
                                 'overwrite': 'true'})
            response = requests.get('https://cloud-api.yandex.net/v1/disk/resources/upload',
                                    headers=headers,
                                    params={'path': f'VK_Images/{name}.jpg',
                                            'overwrite': 'true'})
            url_for_upload = response.json()['href']
            data = requests.get(url)
            requests.put(url_for_upload, data=data.content)

        print('Фото загружены')


class MakeJSON:  # Класс формирования JSON-файла в соответствии с заданием
    def __init__(self):
        pass

    def get_json_report(self):
        result_list = []
        sizes_list = []
        for photo in vk_photos:
            if photo['sizes'][-1]['height'] == 0:
                sizes_list.append(photo['sizes'][-1]['type'])
            else:
                sizes_list.append(max(photo['sizes'], key=lambda x: x['height'] * x['width'])['type'])
        for url, name in zip(vk_photos_max_q, vk_photos_name):
            result_list.append({'file_name': f'{name}.jpg', 'size': f'{sizes_list[vk_photos_max_q.index(url)]}'})
        with open('result.json', 'w') as f:
            json.dump(result_list, f, indent=4)

        print('JSON-файл создан')


if __name__ == '__main__':
    YADiskUploader().upload_photos()
    MakeJSON().get_json_report()
