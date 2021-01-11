from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import logging
import json
import plugins

class Handler(BaseHTTPRequestHandler):
    def check_client_address(self, address):
        try:
            if not address[0].startswith(self.server.data['home_network']):
                self.answer(403, {'Content-type':'text/html'}, "403 FORBIDEN".encode('utf-8'))
                return False
        except:
            pass
        return True

    def check_blacklist(self, path):
        for i in self.server.blacklist:
            if path.find(i) != -1:
                self.answer(404, {'Content-type':'text/html'}, "404 NOT FOUND".encode('utf-8'))
                return False
        return True

    def do_GET(self):
        path = str(self.path)
        if not self.check_client_address(self.client_address) or not self.check_blacklist(path):
            return
        print("GET Request", path)
        if path.startswith('/favicon.ico'):
            self.answer(200, {'Content-type':'image/x-icon'}, self.server.icon)
        else:
            for p in self.server.plugins:
                try:
                    if p.process_get(self, path):
                        return
                except:
                    pass

            host_address = self.headers.get('Host')
            if path.startswith('/manual'):
                self.answer(200, {'Content-type':'text/html'}, self.get_manual().encode('utf-8'))
            elif path == "/":
                self.answer(200, {'Content-type':'text/html'}, self.get_interface().encode('utf-8'))
            else:
                self.answer(303, {'Location':'http://{}'.format(host_address)})

    def do_POST(self):
        path = str(self.path)
        if not self.check_client_address(self.client_address) or not self.check_blacklist(path):
            return
        print("POST Request", path)
        for p in self.server.plugins:
            try:
                if p.process_post(self, path):
                    return
            except:
                pass

        self.answer(303, {'Location':'http://{}'.format(self.headers.get('Host'))})

    def answer(self, code : int, headers : dict = {}, write=None):
        self.send_response(code)
        for k in headers:
            self.send_header(k, headers[k])
        self.end_headers()
        if write is not None:
            self.wfile.write(write)

    def get_interface(self):
        html = '<style>.elem {border: 2px solid black;display: inline-block;background-color: #b8b8b8;}</style><title>WiihUb</title><body style="background-color: #242424;"><div><div class="elem"><b>WiihUb '+self.server.version+'</b><br><a href="/manual">Help</a></div>'
        for p in self.server.plugins:
            try:
                html += '<div class="elem">'+p.get_interface()+'</div>'
            except:
                pass
        html += '</div></body>'
        return html

    def get_manual(self):
        html = '<style>.elem {border: 2px solid black;display: inline-block;background-color: #b8b8b8;}</style><title>WiihUb</title><body style="background-color: #242424;"><div><div class="elem"><b>WiihUb '+self.server.version+'</b><br><a href="/">Back</a></div>'
        for p in self.server.plugins:
            try:
                html += '<div class="elem">'+p.get_manual()+'</div>'
            except:
                pass
        html += '</div></body>'
        return html


class WiihUb(ThreadingHTTPServer):
    def __init__(self):
        self.version = "v2.0.1"
        try:
            with open('config.json') as f:
                self.data = json.load(f)
        except Exception as e:
            print("Failed to load config.json")
            print(e)
            while True:
                print("An empty config.json file will be created, continue? (y/n)")
                i = input()
                if i.lower() == 'n': exit(0)
                elif i.lower() == 'y': break
            self.data = {'home_network':'192.168.1'}
            self.save()
        self.plugins = []
        self.blacklist = []
        self.is_running = True
        self.user_agent_common = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36"
        self.icon = bytearray([0, 0, 1, 0, 1, 0, 17, 16, 16, 0, 1, 0, 4, 0, 104, 1, 0, 0, 22, 0, 0, 0, 40, 0, 0, 0, 17, 0, 0, 0, 32, 0, 0, 0, 1, 0, 4, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 3, 94, 0, 0, 0, 255, 0, 104, 64, 11, 0, 15, 100, 9, 0, 255, 147, 8, 0, 18, 255, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 102, 102, 102, 102, 102, 102, 102, 102, 96, 0, 0, 0, 102, 102, 85, 85, 83, 97, 6, 102, 96, 0, 0, 0, 102, 102, 101, 85, 54, 17, 16, 102, 96, 0, 0, 0, 102, 102, 102, 83, 97, 17, 17, 6, 96, 0, 0, 0, 102, 102, 102, 102, 102, 102, 102, 102, 96, 0, 0, 0, 102, 102, 100, 68, 68, 66, 102, 102, 96, 0, 0, 0, 102, 102, 68, 68, 68, 68, 38, 102, 96, 0, 0, 0, 102, 102, 68, 38, 102, 68, 38, 102, 96, 0, 0, 0, 102, 102, 68, 38, 102, 68, 38, 102, 96, 0, 0, 0, 102, 102, 68, 38, 102, 68, 38, 102, 96, 0, 0, 0, 102, 102, 68, 38, 102, 68, 38, 102, 96, 0, 0, 0, 102, 102, 68, 38, 102, 68, 38, 102, 96, 0, 0, 0, 102, 102, 68, 38, 102, 68, 38, 102, 96, 0, 0, 0, 102, 102, 68, 38, 102, 68, 38, 102, 96, 0, 0, 0, 102, 102, 102, 102, 102, 102, 102, 102, 96, 0, 0, 0, 102, 102, 102, 102, 102, 102, 102, 102, 96, 0, 0, 0, 255, 255, 128, 0, 240, 39, 128, 0, 248, 67, 128, 0, 252, 129, 128, 0, 255, 255, 128, 0, 248, 15, 128, 0, 240, 7, 128, 0, 241, 199, 128, 0, 241, 199, 128, 0, 241, 199, 128, 0, 241, 199, 128, 0, 241, 199, 128, 0, 241, 199, 128, 0, 241, 199, 128, 0, 255, 255, 128, 0, 255, 255, 128, 0])
        plugins.load(self)
    
        super().__init__(('',8000), Handler)
        self.daemon_threads = True

    def run(self):
        print("WiihUb - "+self.version)
        print("Server started, listening on port 8000")
        self.request_queue_size = 80
        try:
            self.serve_forever()
        except KeyboardInterrupt:
            self.is_running = False
            self.server_close()
        print("Closing server...")
        self.stop()
        self.save()

    def getOptions(self, path, prefix):
        path_str = str(path)[len('/' + prefix + '?'):]
        param_strs = path_str.split('&')
        options = {}
        for s in param_strs:
            ss = s.split('=')
            if len(ss) >= 2: options[ss[0]] = '='.join(ss[1:])
        return options

    def add_plugin(self, plugin):
        self.plugins.append(plugin)

    def stop(self):
        for p in self.plugins:
            try: p.stop()
            except: pass

    def save(self):
        try:
            with open('config.json', 'w') as outfile:
                json.dump(self.data, outfile, sort_keys=True, indent=4)
        except Exception as e:
            print("Failed to save config.json")
            print(e)


if __name__ == '__main__':
    WiihUb().run()