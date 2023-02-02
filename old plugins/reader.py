import urllib.parse
from os import listdir
from os.path import isfile, join
import glob

class TextReader():
    def __init__(self, server):
        self.server = server

    def stop(self):
        pass

    def get_notes(self):
        html = self.server.get_body() + '<style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;}</style><div>'
        html += '<div class="elem"><a href="/">Back</a><br><a href="/newnote">New</a></div>'
        for i in range(len(self.notes)):
            html += '<div class="elem">'+self.notes[i]+'<br><br><a href="/editnote?id={}">Edit</a> # <a href="/delnote?id={}">Delete</a></div>'.format(i, i)
        return html

    def get_files(self):
        try: fs = glob.glob('reader/**/*', recursive=True)
        except: fs = []
        html = self.server.get_body() + '<style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;}</style><div>'
        html += '<div class="elem"><a href="/">Back</a></div>'
        html += '<div class="elem">'
        for f in fs:
            if f.endswith(".txt"):
                html += '<a href="/readfile?target={}">{}</a><br>'.format(f.replace('reader\\', ''), f.replace('reader\\', ''))
        html += '</div>'
        return html

    def open_file(self, file):
        try:
            with open("reader/" + file, "r", encoding='utf-8') as f:
                content = f.read()
        except:
            with open("reader/" + file, "r") as f:
                content = f.read()
        html = self.server.get_body() + '<style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;}</style><div>'
        html += '<div class="elem"><a href="/">Back</a></div>'
        html += '<div class="elem">'
        html += content.replace('\n', '<br>')
        html += '</div>'
        return html

    def process_get(self, handler, path):
        host_address = handler.headers.get('Host')
        if path.startswith('/readlist'):
            handler.answer(200, {'Content-type': 'text/html'}, self.get_files().encode('utf-8'))
            return True
        elif path.startswith('/readfile?'):
            options = self.server.getOptions(path, 'readfile')
            try:
                handler.answer(200, {'Content-type': 'text/html'}, self.open_file(urllib.parse.unquote(options['target'].replace('+', ' ')).replace('\r\n', '\n')).encode('utf-8'))
            except Exception as e:
                print("Failed to open file")
                self.server.printex(e)
                handler.answer(303, {'Location':'http://{}/readlist'.format(host_address)})
            return True
        return False

    def process_post(self, handler, path):
        return False

    def get_interface(self):
        return '<b>Reader</b><br><a href="/readlist">Open</a>'

    def get_manual(self):
        return '<b>Reader plugin</b><br>Allow you to take text files.'