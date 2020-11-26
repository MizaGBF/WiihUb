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
        self.check_cache_folder()
        self.img_re = re.compile('src="(\\.\\.[a-zA-Z0-9\\/]+\\.jpg)"')

    def stop(self):
        self.clean_cache()

    def check_cache_folder(self):
        if not path.exists("epub_cache"):
            print("Created cache folder")
            makedirs("epub_cache")

    def clean_cache(self):
        for filename in listdir("epub_cache"):
            file_path = join("epub_cache", filename)
            try:
                if isfile(file_path) or islink(file_path):
                    unlink(file_path)
            except Exception as e: print(e)

    def get_book_chapter(self, book, chapter): # TEST get_pages
        if book != self.book_path:
            self.book = epub.read_epub('books/' + book)
            if self.book is None: return None
            self.book_path = book
            spine = self.book.spine
            self.chapters = []
            self.clean_cache()
            for s in spine:
                i = self.book.get_item_with_id(s[0])
                if i.get_type() == ebooklib.ITEM_DOCUMENT:
                    self.chapters.append(i)
            for i in self.book.get_items_of_type(ebooklib.ITEM_IMAGE):
                with open("epub_cache/"+i.get_name().split('/')[-1], "wb") as f:
                    f.write(i.get_content())
            for i in self.book.get_items_of_type(ebooklib.ITEM_COVER):
                with open("epub_cache/"+i.get_name().split('/')[-1], "wb") as f:
                    f.write(i.get_content())
            
        if chapter > len(self.chapters):
            chapter = 0
        return self.chapters[chapter].get_body_content().decode("utf-8"), chapter, len(self.chapters)

    def get_book_list(self):
        try: fs = [f for f in listdir("books") if (isfile(join("books", f)) and f.endswith('.epub'))]
        except: fs = []
        html = '<meta charset="UTF-8"><style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;}</style><title>WiihUb</title><body style="background-color: #242424;"><div>'
        html += '<div class="elem"><a href="/">Back</a></div>'
        if self.notification is not None:
            html += '<div class="elem">{}</div>'.format(self.notification)
            self.notification = None
        html += '<div class="elem">'
        for b in fs:
            html += '<a href="/book?file={}">{}</a><br>'.format(b, b)
        if len(fs) == 0: html += "No e-pub files found"
        html += '</div>'
        return html

    def insert_image(self, content):
        r = self.img_re.findall(content)
        for i in r:
            content = content.replace(i, '/bookimage?file={}'.format(i.split('/')[-1]))
            print("REPLACE", i.split('/')[-1])
        return content

    def process_get(self, handler, path):
        host_address = handler.headers.get('Host')
        if path.startswith('/booklist'):
            handler.send_response(200)
            handler.send_header('Content-type', 'text/html')
            handler.end_headers()
            handler.wfile.write(self.get_book_list().encode('utf-8'))
            return True
        elif path.startswith('/book?'):
            path_str = str(path)[len('/book?'):]
            param_strs = path_str.split('&')
            options = {}
            for s in param_strs:
                ss = s.split('=')
                options[ss[0]] = ss[1]
            try:
                content, chapter, max_chapter = self.get_book_chapter(urllib.parse.unquote(options['file']), int(options.get('chapter', 0)))
                html = '<meta charset="UTF-8"><style>.elem {border: 2px solid black;display: table;background-color: #b8b8b8;margin: 10px 50px 10px;padding: 10px 10px 10px 10px;font-size: 180%;} .epub_content {color: #c7c7c7;font-size: 140%;}</style><title>WiihUb</title><body style="background-color: #242424;">'
                footer = '<div class="elem">'
                if chapter > 0: footer += '<a href="/book?file={}&chapter={}">Previous</a> ◾ '.format(options['file'], chapter-1)
                footer += '<a href="/booklist">Back</a>'
                if chapter < max_chapter: footer += ' ◾ <a href="/book?file={}&chapter={}">Next</a>'.format(options['file'], chapter+1)
                footer += '</div>'
                html += footer + '<div class="epub_content">{}</div>'.format(self.insert_image(content)) + footer + '</body>'
                handler.send_response(200)
                handler.send_header('Content-type', 'text/html')
                handler.end_headers()
                handler.wfile.write(html.encode('utf-8'))
                return True
            except Exception as e:
                print("Failed to open book")
                print(e)
                self.notification = "Failed to open {}.epub<br>".format(options.get('file', ''), e)
                host_address = handler.headers.get('Host')
                handler.send_response(303)
                handler.send_header('Location','http://{}/booklist'.format(host_address))
                handler.end_headers()
            return True
        elif path.startswith('/bookimage?'):
            path_str = str(path)[len('/bookimage?'):]
            param_strs = path_str.split('&')
            options = {}
            for s in param_strs:
                ss = s.split('=')
                options[ss[0]] = ss[1]
            try:
                with open("epub_cache/"+urllib.parse.unquote(options['file']), "rb") as f:
                    handler.send_response(200)
                    handler.send_header('Content-type', 'image/jpeg')
                    handler.end_headers()
                    handler.wfile.write(f.read())
            except Exception as e:
                print(e)
                handler.send_response(404)
                handler.end_headers()
            return True
        return False

    def process_post(self, handler, path):
        return False
        
    def get_interface(self):
        return '<b>E-Pub Reader</b><br><a href="/booklist">Open folder</a>'

    def get_manual(self):
        return '<b>>E-Pub Reader plugin</b><br>Put your e-pub files in a "books" folder before starting.'