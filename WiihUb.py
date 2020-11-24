from http.server import BaseHTTPRequestHandler, HTTPServer
import logging
import json
import plugins

class Handler(BaseHTTPRequestHandler):
    def check_client_address(self, address):
        try:
            if not address[0].startswith(self.server.data['home_network']):
                self.send_response(403)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write("403 FORBIDDEN".encode('utf-8'))
                return False
        except:
            pass
        return True

    def check_blacklist(self, path):
        for i in self.server.blacklist:
            if path.find(i) != -1:
                self.send_response(404)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write("404 not found".encode('utf-8'))
                return False
        return True


    def do_GET(self):
        path = str(self.path)
        if not self.check_client_address(self.client_address) or not self.check_blacklist(path):
            return
        print("GET Request", path)
        for p in self.server.plugins:
            try:
                if p.process_get(self, path):
                    return
            except:
                pass
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(self.get_interface().encode('utf-8'))


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

    def get_interface(self):
        html = "<style>.elem {border: 2px solid black;display: inline-block;}</style><div>"
        for p in self.server.plugins:
            try:
                html += '<div class="elem">'+p.get_interface()+'</div>'
            except:
                pass
        html += '</div>'
        return html

class WiihUb(HTTPServer):
    def __init__(self, RequestHandlerClass=Handler):
        try:
            with open('config.json') as f:
                self.data = json.load(f)
        except Exception as e:
            print("Failed to load config.json")
            print(e)
            self.data = {'home_network':'192.168.1'}
            self.save()
        self.plugins = []
        self.blacklist = ['/favicon']
        plugins.load(self)
    
        super().__init__(('',8000), RequestHandlerClass)

    def run(self):
        print("WiihUb - v1.0.0")
        print("Server started")
        try:
            self.serve_forever()
        except KeyboardInterrupt:
            pass
        print("Closing server...")
        self.stop()
        self.save()

    def add_plugin(self, plugin):
        self.plugins.append(plugin)

    def stop(self):
        for p in self.plugins:
            try: p.stop()
            except: pass

    def save(self):
        try:
            with open('config.json', 'w') as outfile:
                json.dump(self.data, outfile)
        except Exception as e:
            print("Failed to save config.json")
            print(e)


if __name__ == '__main__':
    WiihUb().run()