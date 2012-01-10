from google.appengine.api import users
from datetime import *
import time

from bo import *
from database.bubble import *
from database.person import *
from database.zimport.zoin import *
from database.zimport.zbubble import *


class Dokumendid(boRequestHandler):
    def get(self):
        taskqueue.Task(url='/update/docs').add()

    def post(self):
        csv = []
        for c in db.Query(Counter).order('__key__').fetch(1000):
            for b in db.Query(Bubble).filter('registry_number_counter', c.key()).fetch(1000):
                if len(getattr(b, 'optional_bubbles', [])) > 0:
                    for sb in Bubble().get(b.optional_bubbles):
                        if sb:
                            csv.append('%s;%s;%s;%s;%s' % (c.displayname, sb.type, sb.key().id(), getattr(sb, 'registry_number', ''), sb.displayname))

        SendMail(
            to = 'argo.roots@artun.ee',
            subject = 'Docs',
            message = 'jee',
            attachments = [('Docs.csv', '\n'.join(csv))],
        )

class FixStuff(boRequestHandler):
    def get(self):
        b = Bubble().get('agpzfmJ1YmJsZWR1cg8LEgZCdWJibGUYjcmwAgw')
        b.optional_bubbles = AddToList(db.Key('agpzfmJ1YmJsZWR1cg8LEgZCdWJibGUYy4S1Agw'), b.optional_bubbles)
        b.put()

        b = Bubble().get('agpzfmJ1YmJsZWR1cg8LEgZCdWJibGUYrNuyAgw')
        b.optional_bubbles = AddToList(db.Key('agpzfmJ1YmJsZWR1cg8LEgZCdWJibGUYnP20Agw'), b.optional_bubbles)
        b.optional_bubbles = AddToList(db.Key('agpzfmJ1YmJsZWR1cg8LEgZCdWJibGUYwKe0Agw'), b.optional_bubbles)
        b.put()


class AddUser(boRequestHandler):
    def get(self, type):
        for b in db.Query(Bubble).filter('type', type).fetch(1000):
            if hasattr(b, 'viewers'):
                b.viewers = AddToList(db.Key('agpzfmJ1YmJsZWR1cg8LEgZQZXJzb24Ykf2yAgw'), b.viewers)
            else:
                b.viewers = [db.Key('agpzfmJ1YmJsZWR1cg8LEgZQZXJzb24Ykf2yAgw')]
                self.echo(str(b.key()))
            b.put()


def main():
    Route([
            ('/update/docs', Dokumendid),
            ('/update/stuff', FixStuff),
            (r'/update/user/(.*)', AddUser),
        ])


if __name__ == '__main__':
    main()
