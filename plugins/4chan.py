from xml.sax import saxutils as su
import re
from urllib.parse import quote, unquote

class FourChan():
    def __init__(self, server):
        self.server = server
        self.search_results = None
        self.chan_board = self.server.data.get("4chan_board", "")
        self.chan_search = self.server.data.get("4chan_search", "")
        
        threads = self.get4chan(self.chan_board, self.chan_search)
        self.search_results = ""
        for i in range(min(len(threads), 5)):
            if len(threads[i][2]) > 20:
                self.search_results += '<a href="https://boards.4channel.org/{}/thread/{}"><i>{}</i> - {}...</a><br>'.format(self.chan_board, threads[i][0], threads[i][1], threads[i][2][:20])
            else:
                self.search_results += '<a href="https://boards.4channel.org/{}/thread/{}"><i>{}</i> - {}</a><br>'.format(self.chan_board, threads[i][0], threads[i][1], threads[i][2])

    def stop(self):
        self.server.data["4chan_board"] = self.chan_board
        self.server.data["4chan_search"] = self.chan_search

    def cleanhtml(self, raw):
      cleaner = re.compile('<.*?>')
      return su.unescape(re.sub(cleaner, '', raw.replace('<br>', ' '))).replace('>', '')

    def get4chan(self, board, search): # be sure to not abuse it, you are not supposed to call the api more than once per second
        try:
            url = 'http://a.4cdn.org/{}/catalog.json'.format(board) # board catalog url
            rep = self.server.http_client.get(url, follow_redirects=True)
            if rep.status_code != 200: raise Exception("HTTP Error {}".format(rep.status_code))
            data = rep.json()
            search = search.lower()
            threads = []
            for p in data:
                for t in p["threads"]:
                    try:
                        if t.get("sub", "").lower().find(search) != -1 or t.get("com", "").lower().find(search) != -1:
                            threads.append([t["no"], t["replies"], su.unescape(self.cleanhtml(t.get("com", "")))]) # store the thread ids matching our search word
                    except:
                        pass
            threads.sort(reverse=True)
            return threads
        except:
            return []

    def process_get(self, handler, path):
        if path.startswith('/4chan?'):
            options = self.server.getOptions(path, '4chan')
            try:
                if 'board' not in options or 'search' not in options: raise Exception()
                
                threads = self.get4chan(options['board'], options['search'])
                if len(threads) == 0: raise Exception()
                self.search_results = ""
                for i in range(min(len(threads), 5)):
                    if len(threads[i][2]) > 20:
                        self.search_results += '<a href="https://boards.4channel.org/{}/thread/{}"><i>{}</i> - {}...</a><br>'.format(options['board'], threads[i][0], threads[i][1], threads[i][2][:20])
                    else:
                        self.search_results += '<a href="https://boards.4channel.org/{}/thread/{}"><i>{}</i> - {}</a><br>'.format(options['board'], threads[i][0], threads[i][1], threads[i][2])
                if self.search_results == "": self.search_results = "No results"
            except Exception as e:
                print("Failed to retrieve 4chan threads")
                self.server.printex(e)
                self.search_results = "Search failed"

            self.chan_board = options.get('board', self.chan_board)
            self.chan_search = options.get('search', self.chan_search)

            handler.answer(303, {'Location':'http://{}'.format(host_address)})
            return True
        return False

    def process_post(self, handler, path):
        return False

    def get_interface(self):
        html = '<form action="/4chan"><legend><b>4chan Thread Search</b></legend><label for="board">Board </label><input type="text" id="board" name="board" value="{}"><br><label for="search">Search </label><input type="text" id="search" name="search" value="{}"><br><input type="submit" value="Search"></form>'.format(self.chan_board, unquote(self.chan_search).replace('+', ' '))
        if self.search_results is not None:
            html += "{}<br>".format(self.search_results)
        return html

    def get_manual(self):
        return '<b>4chan Search plugin</b><br>"Board" must be a valid 4chan board, without the \'/\' (example: vg).<br>"Search" can be anything.'