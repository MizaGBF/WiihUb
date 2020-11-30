class Youtube():
    def __init__(self, server):
        self.server = server

    def stop(self):
        pass

    def process_get(self, handler, path):
        return False

    def process_post(self, handler, path):
        return False

    def get_interface(self):
        return '<b>Youtube</b><br><a href="https://m.youtube.com/?persist_app=1&app=m">Open</a>'

    def get_manual(self):
        return '<b>Youtube plugin</b><br>Change the Browser User-Agent to Ipad if it doesn\'t work.'