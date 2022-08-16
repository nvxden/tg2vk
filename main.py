#!python3
# Errors:
# - max 50 posts per day
import config
import copy
import os
import requests
import telebot
import threading
import time

from vk import Vk



vk = Vk()
tg = telebot.TeleBot(config.TG_TOKEN)

update_counter = config.TG_UPDATE_COUNT
mediagroups    = {}



# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
# ~~~~~                           DECORATORS                           ~~~~~ #
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

# Ну надо же что-то вывести, когда бот стартует?
@tg.message_handler(commands=['start'])
def start(m, res=False):
  tg.send_message(m.chat.id, 'Started!')


# Текстовые сообщения просто пересылаем без всяких хитростей
@tg.channel_post_handler(content_types=['text'])
def handle_channel_post_text(m):
  vk.post_text(message=insert_links(m.text, m.json.get('entities')))


# Обработка постов с изображениями: получаем id файла, устанавливаем приписку
@tg.channel_post_handler(content_types=['photo'])
def handle_channel_post_photo(m):
  global update_counter
  update_counter = config.TG_UPDATE_COUNT
  file_id = list(map(lambda p: p.file_id, m.photo))[-1]
  group = mediagroups.setdefault(m.media_group_id, {})
  group.setdefault('files', []).append(file_id)
  if m.caption is not None:
    group['caption'] = insert_links(m.caption, m.json.get('caption_entities'))



# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
# ~~~~~                           ACCESSORY                            ~~~~~ #
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

# Находит ссылки в телегпрамме и добавляет после них пробел и в скобках
# саму ссылку; не очень красиво, но лучшего решения сложно найти
def insert_links(text, entities):
  if entities is None:
    return text

  entities = sorted(entities, key=lambda e: e['offset'])
  pos = 0
  strings = []
  for e in entities:
    if e['type'] == 'text_link':
      s, text = copy_bytes(text, e['offset'] + e['length'] - pos)
      strings.append(s)
      strings.append(' (%s)' % shorten_url(e['url']))
      pos = e['offset'] + e['length']

    elif e['type'] == 'mention':
      s, text = copy_bytes(text, e['offset'] - pos)
      strings.append(s)
      s, text = copy_bytes(text[1:], e['length']-1)
      strings.append('t.me/%s' % s)
      pos = e['offset'] + e['length']

  strings.append(text)
  return ''.join(strings)


def copy_bytes(text, count):
  pos, i, result = 0, 0, []
  while i < len(text):
    if pos >= count:
      break
    result.append(text[i])
    pos += 1 if len(bytes(text[i], encoding='utf-8')) < 4 else 2
    i += 1
  return ''.join(result), text[i:]


def shorten_url(url: str):
  discard_prefixes = ['https://', 'http://']
  for prefix in discard_prefixes:
    if url.startswith(prefix):
      return url[len(prefix):]
  return url



# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
# ~~~~~                           THREADING                            ~~~~~ #
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

# Загружает и сохраняет на диск файл по его идентификатору в телеграмме
def save_file(file_id):
  file_info = tg.get_file(file_id=file_id)
  file_data = tg.download_file(file_info.file_path)
  file_name = os.path.basename(file_info.file_path)
  with open(file_name, 'wb') as file:
    file.write(file_data)
  return file_name


# Загружает файлы из тг по айдишникам и выкладывает одним постом с припиской
def post_mediagroup(file_ids, caption=None):
  file_names = list(map(lambda id: save_file(id), file_ids))

  vk.post_photo(
    message = caption,
    photos  = file_names,
  )

  for file_name in file_names:
    os.remove(file_name)


# Каждые несколько секунд проверяет, есть ли какая-либо медиагруппа,
# которую нужно запостить. Если есть, постит и удаляет
def check_mediagroup():
  global update_counter

  while True:
    time.sleep(config.TG_UPDATE_DELAY / 1000)
    update_counter -= 1
    if update_counter != 0:
      continue
    group_ids = list(mediagroups.keys())
    update_counter = config.TG_UPDATE_COUNT

    for id in group_ids:
      post_mediagroup(mediagroups[id]['files'], mediagroups[id].get('caption'))
      del mediagroups[id]



# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
# ~~~~~                              MAIN                              ~~~~~ #
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
def main():
  threading.Thread(target=check_mediagroup).start()
  tg.polling(none_stop=True, interval=0)
  exit(0)



if __name__ == '__main__':
  main()



# END
