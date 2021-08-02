import ebooklib
from ebooklib import epub
from os import listdir, unlink, makedirs, path
from os.path import isfile, join, islink
import urllib.parse
import re

class Epub():
    def __init__(self, server):
        self.server = server
        self.book_path = None
        self.book = None
        self.chapters = []
        self.notification = None
        self.img_re = re.compile('(src|xlink:href)="([a-zA-Z0-9\/\-\.\_]+\.(jpg|png|jpeg))')
        self.img_cache = {}
        self.folder = self.server.data.get("epub_folder", "books")
        if self.folder == "": self.folder = "books"
        if self.folder[-1] == "/": self.folder = self.folder[:-1]
        self.bookmarks = self.server.data.get("epub_bookmarks", {})

    def stop(self):
        self.server.data["epub_folder"] = self.folder
        self.server.data["epub_bookmarks"] = self.bookmarks

    def get_book_chapter(self, book, chapter): # TEST get_pages
        if book != self.book_path:
            self.book = epub.read_epub(self.folder + '/' + book)
            if self.book is None: return None
            self.book_path = book
            spine = self.book.spine
            self.chapters = []
            self.img_cache = {}
            for s in spine:
                i = self.book.get_item_with_id(s[0])
                if i.get_type() == ebooklib.ITEM_DOCUMENT:
                    self.chapters.append(i)
            for i in self.book.get_items_of_type(ebooklib.ITEM_IMAGE):
                self.img_cache[i.get_name().split('/')[-1]] = i.get_content()
            for i in self.book.get_items_of_type(ebooklib.ITEM_COVER):
                self.img_cache[i.get_name().split('/')[-1]] = i.get_content()
            
        if chapter > len(self.chapters):
            chapter = 0
        return self.chapters[chapter].get_body_content().decode("utf-8"), chapter, len(self.chapters)-1

    def get_book_list(self):
        try: fs = [f for f in listdir(self.folder) if (isfile(join(self.folder, f)) and f.endswith('.epub'))]
        except: fs = []
        html = self.server.get_body() + '<style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;}</style><div>'
        html += '<div class="elem"><a href="/">Back</a></div>'
        if self.notification is not None:
            html += '<div class="elem">{}</div>'.format(self.notification)
            self.notification = None
        html += '<div class="elem">'
        for k in list(self.bookmarks.keys()):
            if k not in fs: self.bookmarks.pop(k)
        for b in fs:
            if b in self.bookmarks: html += '<a href="/book?file={}&chapter={}">{}</a><br>'.format(b, self.bookmarks[b], b)
            else: html += '<a href="/book?file={}">{}</a><br>'.format(b, b)
        if len(fs) == 0: html += "No e-pub files found in the '{}' folder".format(self.folder)
        html += '</div>'
        return html

    def insert_image(self, content):
        r = self.img_re.findall(content)
        for i in r:
            if i[0] == 'xlink:href':
                a = content.find('<svg')
                b = content.find('</svg>')
                content = content[:a] + '<img src="/bookimage?file={}">'.format(i[1].split('/')[-1]) + content[b+6:]
            else:
                content = content.replace(i[1], '/bookimage?file={}'.format(i[1].split('/')[-1]))
        return content

    def process_get(self, handler, path):
        host_address = handler.headers.get('Host')
        if path.startswith('/booklist'):
            handler.answer(200, {'Content-type':'text/html'}, self.get_book_list().encode('utf-8'))
            return True
        elif path.startswith('/book?'):
            options = self.server.getOptions(path, 'book')
            try:
                if '3ds' in handler.headers.get('User-Agent').lower():
                    ds = True
                else:
                    ds = False
                content, chapter, last_chapter = self.get_book_chapter(urllib.parse.unquote(options['file']), int(options.get('chapter', 0)))
                html = '<head><meta charset="UTF-8"></head><style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;font-size: 180%;} .epub_content {color: #c7c7c7;font-size: 150%}</style><title>WiihUb</title><body style="background-color: #242424;margin: 5px 20px;font-size: ' + str(200 if ds else 100) + '%">'
                footer = '<div class="elem">'
                if chapter > 0: footer += '<a href="/book?file={}&chapter={}">Previous</a> # '.format(options['file'], chapter-1)
                footer += '<a href="/booklist">Back</a>'
                if chapter < last_chapter: footer += ' # <a href="/book?file={}&chapter={}">Next</a>'.format(options['file'], chapter+1)
                footer += '</div>'
                html += footer + '<div class="epub_content">{}</div>'.format(self.insert_image(content)) + footer + '</body>'
                self.bookmarks[urllib.parse.unquote(options['file'])] = chapter
                handler.answer(200, {'Content-type':'text/html'}, html.encode('utf-8'))
                return True
            except Exception as e:
                print("Failed to open book")
                self.server.printex(e)
                self.notification = "Failed to open {}.epub<br>{}".format(options.get('file', ''), e)
                handler.answer(303, {'Location':'http://{}/booklist'.format(host_address)})
            return True
        elif path.startswith('/bookimage?'):
            options = self.server.getOptions(path, 'bookimage')
            try:
                handler.answer(200, {'Content-type':'image/{}'.format(options['file'].split('.')[-1])}, self.img_cache[urllib.parse.unquote(options['file'])])
            except Exception as e:
                print("Image not found in cache")
                self.server.printex(e)
                handler.answer(404)
            return True
        return False

    def process_post(self, handler, path):
        return False

    def get_interface(self):
        html = '<b>E-Pub Reader</b><br><a href="/booklist">Open folder</a>'
        if self.notification is not None:
            html += "{}<br>".format(self.notification)
            self.notification = None
        return html

    def get_manual(self):
        return '<b>E-Pub Reader plugin</b><br>Put your e-pub files in a folder defined in config.json, at "epub_folder"'