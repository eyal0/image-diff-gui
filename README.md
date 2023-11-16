# image-diff-gui
Graphically compare two SVG images.

# To install

```sh
sudo apt-get install gir1.2-rsvg-2.0 python3-cairo python3-gi-cairo python3-gi libcairo2-dev gir1.2-gtk-3.0 libgirepository1.0-dev python3-pil python3-pil.imagetk
pip3 install .
```
It looks like this:

![image](https://github.com/eyal0/image-diff-gui/assets/109809/416cae41-7f1a-48e7-b4b4-f3f514b3faa5)

The image is on the left, on the right, and the diff is in the middle.  You can zoom and pan the images with the mouse.  There is an option to ignore the alpha channel, too.
