#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
ファイルをアップロードする
'''
html = '''Content-Type: text/html

<html>
<head>
  <meta http-equiv="Content-Type" content="text/html" charset="UTF-8" />
  <title>RtsProfileをアップロードする</title>
</head>
<body>
<h3>RtsProfileをアップロードする</h3>
<p>%s</p>
<form action="upload.py" method="post" enctype="multipart/form-data">
  <input type="file" name="file" />
  <input type="submit" />
</form>
</body>
</html>
'''

import cgi
import os, sys

try:
    import msvcrt
    msvcrt.setmode(0, os.O_BINARY)
    msvcrt.setmode(1, os.O_BINARY)
except ImportError:
    pass

result = ''
form = cgi.FieldStorage()
if form.has_key('file'):
    item = form['file']
    if item.file:
        fout = file(os.path.join('./rtsprofiles', item.filename), 'wb')
        while True:
            chunk = item.file.read(1000000)
            if not chunk:
                break
            fout.write(chunk)
        fout.close()
        result = 'アップロードしました。'

print html % result
