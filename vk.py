import config
import requests

from vk_api.vk_api import VkApi
from vk_api.upload import VkUpload



class Vk:
  def __init__(self):
    print('По этой ссылке нужно перейти, если бот вылетает с ошибкой прав доступа:')
    print(
      'https://oauth.vk.com/oauth/authorize?client_id=%s&redirect_uri=%s&display=%s&scope=%s' %
      (
        config.VK_APPLICATION_ID,
        config.VK_AUTH_REDIRECT_URI,
        config.VK_AUTH_DISPLAY_PARAM,
        config.VK_AUTH_SCOPE,
      )
    )

    self.vk = VkApi(
      login         = config.VK_LOGIN,
      password      = config.VK_PASSWORD,
      token         = config.VK_CLIENT_SECRET,
      scope         = config.VK_AUTH_SCOPE,
    )
    self.vk.auth()
    self.api = self.vk.get_api()
    self.upload = VkUpload(self.api)


  def post_text(self, message: str):
    self.api.wall.post(
      owner_id    = config.VK_GROUP_ID,
      message     = message,
      from_group  = 1,
    )


  def post_photo(self, message: str, photos):
    info = self.upload.photo_wall(photos, group_id=-config.VK_GROUP_ID)
    self.api.wall.post(
      owner_id    = config.VK_GROUP_ID,
      message     = message,
      from_group  = 1,
      attachments = self._info2attachments('photo', info),
    )


  def _info2attachments(self, prefix, info):
    return ','.join(map(
      lambda i: '%s%s_%s' % (prefix, i['owner_id'], i['id']),
      info,
    ))



# END
