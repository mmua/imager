#!/usr/bin/env python
import sys
import os
import Image

from cropy.entropy import entropy_crop
from skimage import io

def _makedirs(dstdir):
    from os import makedirs
    try:
        makedirs(dstdir)
    except OSError, e:
       if e.errno == 17: # dir exists already
           pass
       else:
           raise e

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

    newIm = im.resize((int(w*factor), int(h*factor)), Image.ANTIALIAS)
    newIm.save(dst)

    return newIm.size

def crop_image(src, dst, width, height):
    src_im = Image.open(src)
    w, h = src_im.size
     
    im_factor = w / float(h)
    crop_factor = width / float(height)

    if im_factor < crop_factor: # "taller" than crop
        crop_width = w
        crop_height = int(round(w / crop_factor))
    else:                       # "shorter" than crop
        crop_width = int(round(h * crop_factor))
        crop_height = h

    
    im = io.imread(src, as_grey=True)  # Load an image with float format
    maxSteps = float(10)
    x_offset, y_offset = entropy_crop(im, crop_width, crop_height, maxSteps)

    imfin = Image.open(src)
    region = imfin.crop((x_offset, y_offset, crop_width + x_offset, crop_height + y_offset))

    # Final resize
    newIm = region.resize((width, height), Image.ANTIALIAS)
    newIm.save(dst)

    return newIm.size

if __name__ == "__main__":
    import sys
    import json
    import os.path

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
               
                dstdir = os.path.dirname(dst)
                if dstdir:
                    _makedirs(dstdir)
                    
                if request['cmd'] == 'resize':
                    w, h = resize_image(src, dst, width, height, forse_size)
                    res = {'status' : 'ok', 'src': src, 'dst': dst, 'width': w, 'height': h}
                elif request['cmd'] == 'crop':
                    w, h = crop_image(src, dst, width, height)
                    res = {'status' : 'ok', 'src': src, 'dst': dst, 'width': w, 'height': h}
 
            except ValueError:
                res = {'status' : 'error', 'msg': 'unexpected data', 'data': data}

            except KeyError:
                res = {'status' : 'error', 'msg': 'no command', 'data': data}
            print json.dumps(res)
            sys.stdout.flush()


