import os, sys, http.server, urllib.parse

class RangeRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def send_head(self):
        path = self.translate_path(self.path)
        f = None
        if os.path.isdir(path):
            parts = urllib.parse.urlsplit(self.path)
            if not parts.path.endswith('/'):
                self.send_response(http.HTTPStatus.MOVED_PERMANENTLY)
                new_parts = (parts[0], parts[1], parts[2] + '/', parts[3], parts[4])
                new_url = urllib.parse.urlunsplit(new_parts)
                self.send_header("Location", new_url)
                self.end_headers()
                return None
            for index in "index.html", "index.htm":
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                return self.list_directory(path)
        ctype = self.guess_type(path)
        try:
            f = open(path, 'rb')
        except OSError:
            self.send_error(http.HTTPStatus.NOT_FOUND, "File not found")
            return None

        fs = os.fstat(f.fileno())
        size = fs[6]
        
        # Support Range header (HTTP 206)
        range_header = self.headers.get('Range')
        if range_header and range_header.startswith('bytes='):
            try:
                ranges = range_header[6:].split('-')
                start = int(ranges[0]) if ranges[0] else 0
                end = int(ranges[1]) if len(ranges) > 1 and ranges[1] else size - 1
                if start >= size or end >= size or start > end:
                    self.send_error(http.HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                    f.close()
                    return None
                
                self.send_response(http.HTTPStatus.PARTIAL_CONTENT)
                self.send_header('Content-Type', ctype)
                self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
                self.send_header('Content-Length', str(end - start + 1))
                self.send_header('Accept-Ranges', 'bytes')
                self.end_headers()
                
                f.seek(start)
                class LimitedFile:
                    def __init__(self, file, length):
                        self.file = file
                        self.remaining = length
                    def read(self, size=-1):
                        if self.remaining <= 0:
                            return b''
                        if size < 0 or size > self.remaining:
                            size = self.remaining
                        data = self.file.read(size)
                        self.remaining -= len(data)
                        return data
                    def close(self):
                        self.file.close()
                return LimitedFile(f, end - start + 1)
            except Exception as e:
                pass

        self.send_response(http.HTTPStatus.OK)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(size))
        self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
        self.send_header('Accept-Ranges', 'bytes')
        self.end_headers()
        return f

PORT = 5050
server_address = ('', PORT)
http.server.ThreadingHTTPServer.allow_reuse_address = True
httpd = http.server.ThreadingHTTPServer(server_address, RangeRequestHandler)
print(f"Threading HTTP Server running at http://localhost:{PORT}")
httpd.serve_forever()