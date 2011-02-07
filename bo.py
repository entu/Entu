import os
from types import ListType
from google.appengine.api import mail
from google.appengine.api import users
from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp import util
from django.core.validators import email_re

from datetime import timedelta

from settings import *


def Route(url_mapping):
    application = webapp.WSGIApplication(url_mapping, debug=True)
    util.run_wsgi_app(application)


class boRequestHandler(webapp.RequestHandler):
    def authorize(self, controller=None):
        from database.person import *
        from database.feedback import *

        if db.Query(QuestionaryPerson).filter('person', Person().current).filter('is_completed', False).filter('is_obsolete', False).get():
            path = str(self.request.url)
            Cache().set('redirect_after_feedback', path)
            self.redirect('/feedback')
            return False
            #return True
        else:
            if controller and users.is_current_user_admin() == False:
                rights = []
                for role in Person().current.roles:
                    rights = rights + role.role.rights
                if controller in rights:
                    return True
                else:
                    return False
            else:
                return True

    def view(self, page_title, templatefile, values={}):
        from database.person import *

        browser = str(self.request.headers['User-Agent'])
        if browser.find('MSIE 5') > -1 or browser.find('MSIE 6') > -1 or browser.find('MSIE 7') > -1:
            path = os.path.join(os.path.dirname(__file__), 'templates', 'brausererror.html')
            self.response.out.write(template.render(path, {}))
        else:
            values['str'] = Translate()
            values['system_title'] = SYSTEM_TITLE.decode('utf8')
            values['system_logo'] = SYSTEM_LOGO_URL.decode('utf8')
            if page_title:
                values['site_name'] = SYSTEM_TITLE.decode('utf8') + ' - ' + Translate(page_title)
                values['page_title'] = Translate(page_title)
            else:
                values['site_name'] = SYSTEM_TITLE.decode('utf8')
                values['page_title'] = '&nbsp;'
            values['site_url'] = self.request.headers.get('host')
            values['user'] = Person().current
            values['loginurl'] = users.create_login_url('/')
            values['logouturl'] = users.create_logout_url('/')
            path = os.path.join(os.path.dirname(__file__), 'templates', templatefile)
            self.response.out.write(template.render(path, values))


class UserPreferences(db.Model):
    language = db.StringProperty(default=SYSTEM_LANGUAGE)
    timezone = db.IntegerProperty(default=SYSTEM_TIMEZONE)

    @property
    def current(self):
        user = users.get_current_user()
        if user:
            user_id = user.user_id()
        else:
            user_id = 'guest'

        u = UserPreferences().get_by_key_name(user_id)
        if not u:
            u = UserPreferences(key_name=user_id)
            u.put()
        return u

    def set_language(self, language):
        user = users.get_current_user()
        if user and language in ['estonian', 'english']:
            u = UserPreferences().get_by_key_name(user.user_id())
            if u:
                u.language = language
                u.put()


def Translate(key = None):
    if users.get_current_user():
        languagefile = 'translations.' + UserPreferences().current.language
    else:
        languagefile = 'translations.' + SYSTEM_LANGUAGE

    l = __import__(languagefile, globals(), locals(), ['translation'], -1)

    if key:
        if key in l.translation():
            return l.translation()[key].decode('utf8')
        else:
            return key
    else:
        return l.translation()


class Cache:
    def set(self, key, value=None, user_specific=True, time=1209600):
        if user_specific == True:
            user = users.get_current_user()
            if user:
                key = key + '_' + user.user_id()
            else:
                return False
        if value:
            memcache.delete(key)
            memcache.add(
                key = key,
                value = value,
                time = time
            )
        else:
            memcache.delete(key)
        return value

    def get(self, key, user_specific=True):
        user = users.get_current_user()
        if user_specific == True and user:
            key = key + '_' + user.user_id()
        return memcache.get(key)


def SendMail(to, subject, message, html=True):
    valid_to = []
    if isinstance(to, ListType):
        for t in to:
            if email_re.match(t):
                valid_to.append(t)
    else:
        if email_re.match(to):
            valid_to.append(to)
    if len(valid_to) > 0:
        m = mail.EmailMessage()
        m.sender = SYSTEM_EMAIL
        m.bcc = SYSTEM_EMAIL
        m.to = valid_to
        m.subject = SYSTEM_EMAIL_PREFIX + subject
        if html == True:
            m.html = message
        else:
            m.body = message
        m.send()

        return True


def StrToList(string):
    return [x.strip() for x in string.strip().replace('\n', ' ').replace(',', ' ').replace(';', ' ').split(' ') if len(x.strip()) > 0]

def StrToKeyList(string):
    strlist = StrToList(string)
    keylist = []
    for key in strlist:
        keylist.append(db.Key(key))
    return keylist


def UtcToLocalDateTime(utc_time):
    return utc_time + timedelta(minutes=UserPreferences().current.timezone)


def AddToList(s_value, s_list=[], unique=True):
    s_list.append(s_value)
    if unique==True:
        return list(set(s_list))
    else:
        return s_list

def ImageRescale(img_data, width, height, halign='middle', valign='middle'):
    image = images.Image(img_data)

    desired_wh_ratio = float(width) / float(height)
    wh_ratio = float(image.width) / float(image.height)

    if desired_wh_ratio > wh_ratio:
        image.resize(width=width)
        image.execute_transforms()
        trim_y = (float(image.height - height) / 2) / image.height
        if valign == 'top':
            image.crop(0.0, 0.0, 1.0, 1 - (2 * trim_y))
        elif valign == 'bottom':
            image.crop(0.0, (2 * trim_y), 1.0, 1.0)
        else:
            image.crop(0.0, trim_y, 1.0, 1 - trim_y)
    else:
        image.resize(height=height)
        image.execute_transforms()
        trim_x = (float(image.width - width) / 2) / image.width
        if halign == 'left':
            image.crop(0.0, 0.0, 1 - (2 * trim_x), 1.0)
        elif halign == 'right':
            image.crop((2 * trim_x), 0.0, 1.0, 1.0)
        else:
            image.crop(trim_x, 0.0, 1 - trim_x, 1.0)

    return image.execute_transforms()