#!/usr/bin/env python

def resize_image(src, dst, width, height, forse_size):
    from PIL import Image 
    im = Image.open(src)
    w, h = im.size
     
    if forse_size:
        w, h = width, height
        factor = 1
    else:
        w_factor, h_factor = width / float(w), height / float(h)
        factor = min(w_factor, h_factor)

    newIm = im.resize((int(w*factor), int(h*factor)))
    newIm.save(dst)

    return newIm.size

if __name__ == "__main__":
    import sys
    import json

    MAX_SIZE = 8192

    run = True
    while(run):
        data = sys.stdin.readline()
        data = data.strip()
        if not data:
            run = False
        else:
            try:
                request = json.loads(data)
            except ValueError:
                res = {'status' : 'error', 'msg': 'can\'t decode request'}
                print json.dumps(res)
                continue

            try:
                if request['cmd'] == 'resize':
                    src = request['src']
                    dst = request['dst']
                    resize = request['resize']
                    forse_size = False
                    if resize[0] == "!":
                        forse_size = True
                        resize = resize[1:]
                    xidx = resize.find("x")
                    if xidx == -1:
                        width = int(resize)
                        height = width
                    else:
                        width = resize[0:xidx]
                        if not width: # empty
                            width = MAX_SIZE
                        else:
                            width = int(width)
   

                        height = resize[xidx + 1:]
                        if not height:
                            height = MAX_SIZE
                        else:
                            height = int(height)

                    if width == MAX_SIZE and height == MAX_SIZE:
                         raise ValueError(MAX_SIZE)

                    w, h = resize_image(src, dst, width, height, forse_size)
                    res = {'status' : 'ok', 'src': src, 'dst': dst, 'width': w, 'height': h}
 
            except ValueError:
                res = {'status' : 'error', 'msg': 'unexpected data', 'data': data}

            except KeyError:
                res = {'status' : 'error', 'msg': 'no command', 'data': data}
            print json.dumps(res)
            sys.stdout.flush()


