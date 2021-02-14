"""Gui-based diff for images."""

import tkinter as tk
from collections import namedtuple
import PySimpleGUI as sg
import cairo
from PIL import Image, ImageTk, ImageChops


import gi
gi.require_version('Rsvg', '2.0')
from gi.repository import Rsvg # pylint: disable=wrong-import-position

Point = namedtuple('Point', ["x", "y"])
Point.__add__ = lambda a, b: (Point(a.x + b.x, a.y + b.y)
                              if isinstance(b, Point) else
                              Point(a.x + b, a.y + b))
Point.__radd__ = Point.__add__
Point.__sub__ = lambda a, b: (Point(a.x - b.x, a.y - b.y)
                              if isinstance(b, Point) else
                              Point(a.x - b, a.y - b))
Point.__rsub__ = Point.__sub__ # pylint: disable=no-member

Point.__mul__ = lambda a, b: (Point(a.x * b.x, a.y * b.y)
                              if isinstance(b, Point) else
                              Point(a.x * b, a.y * b))
Point.__rmul__ = Point.__mul__

Point.__truediv__ = lambda a, b: (Point(a.x / b.x, a.y / b.y)
                                  if isinstance(b, Point) else
                                  Point(a.x / b, a.y / b))
Point.from_tuple = lambda p: Point(p[0], p[1])

class SvgImage:
  """Read in svg files and create Tk PhotoImage."""
  def __init__(self, filename):
    handle = Rsvg.Handle()
    self._svg = handle.new_from_file(filename)
    self._image = None

  @property
  def image(self):
    """Returns the internal image."""
    return self._image

  def get_photo_image(self, output_dimensions, top_left=Point(0,0), bottom_right=None, lock=False):
    """Returns a TK PhotoImage.

    The image is translated and scaled to show just the section
    requested.
    """
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, output_dimensions.x, output_dimensions.y)
    context = cairo.Context(surface)
    # First, translate so that the top left of what we output is correct.
    if bottom_right:
      #Scale so that the bottom_right is correct.
      scale_x = output_dimensions.x/(bottom_right.x - top_left.x)
      scale_y = output_dimensions.y/(bottom_right.y - top_left.y)
      if lock:
        scale_x = scale_x + (scale_y - scale_x)/2
        scale_y = scale_x
    else:
      scale_x = 1
      scale_y = 1
    context.translate(-scale_x*top_left[0],-scale_y*top_left[1])
    context.scale(scale_x, scale_y)
    # use rsvg to render the cairo context
    self._svg.render_cairo(context)
    all_bytes = surface.get_data().tobytes()
    self._image = Image.frombuffer("RGBA", output_dimensions,
                                   all_bytes, "raw", "BGRA", 0, 1)
    return ImageTk.PhotoImage(self._image)


class ZoomGraph(sg.Graph): # pylint: disable=too-many-instance-attributes
  """A graph holding a single image file.

  As start, the canvas contains the SVG file in the top-left corner at
  zoom factor 1.  The canvas responds to mouse wheel and clicking and
  drag to zoom and translate the image.  The canvas can handle being
  resized.
  """
  def __init__(self, canvas_size, **kwargs):
    super().__init__(canvas_size,
                     (0, canvas_size[1]),
                     (canvas_size[0], 0),
                     **kwargs)
    self._image = None
    self._photo_image = None
    # These store the portion of the original image that we want to
    # view.
    self._top_left = Point(0,0)
    self._bottom_right = Point.from_tuple(canvas_size)
    self._image_id = None
    self._previous_mouse = None
    self._previous_size = None
    self._event_listener = None

  def register_event_listener(self, event_listener):
    """Register a new callback for getting all the events."""
    self._event_listener = event_listener

  def handle_all(self, event):
    """Single callback for all events."""
    if event.type == tk.EventType.ButtonPress and event.num in [4, 5]:
      self.handle_zoom(event)
    elif event.type in [tk.EventType.ButtonPress, tk.EventType.Motion]:
      self.handle_drag(event)
    elif event.type == tk.EventType.Configure:
      self.handle_resize(event)
    if self._event_listener:
      self._event_listener(event)

  def handle_zoom(self, event):
    """Callback for mousewheel events."""
    self.zoom(Point(event.x, event.y), 0.1 if event.num == 4 else -0.1)

  def handle_drag(self, event):
    """Callback for mouse button and drag events."""
    new_position = Point(event.x, event.y)
    if event.type == tk.EventType.Motion and self._previous_mouse:
      self.translate(new_position - self._previous_mouse)
    self._previous_mouse = new_position

  def handle_resize(self, _):
    """Callback for resize events of the ZoomGraph."""
    zoom_scale = (self._bottom_right - self._top_left) / self._previous_size
    self._bottom_right += zoom_scale*(Point.from_tuple(self.get_size()) - self._previous_size)
    self._previous_size = Point.from_tuple(self.get_size())
    self._update()

  def finalize(self):
    """Bind all the events needed to make this work."""
    self._previous_size = Point.from_tuple(self.get_size())
    self.TKCanvas.bind('<Button-4>', self.handle_all)
    self.TKCanvas.bind('<Button-5>', self.handle_all)
    self.TKCanvas.bind('<B1-Motion>', self.handle_all)
    self.TKCanvas.bind('<Button-1>', self.handle_all)
    self.TKCanvas.bind('<Configure>', self.handle_all)

  @property
  def image(self):
    """Returns the internal SvgImage class."""
    return self._image

  def load_image(self, filename):
    """Sets the image and displays it."""
    self._image = SvgImage(filename)
    # Mustn't let the image get garbage collected or it will disappear
    # from the canvas.
    self._photo_image = self._image.get_photo_image(
      Point.from_tuple(self.get_size()),
      Point(0,0),
      Point.from_tuple(self.get_size()))
    self._image_id = self.TKCanvas.create_image((0,0),anchor=tk.NW,
                                                image=self._photo_image)
  def zoom(self, position, factor):
    """Zooms the image coordinates.

    The position is the location that will stay in place after the
    zoom.  The factor can be negative.
    """
    ratio = (position - Point(0,0)) / (Point.from_tuple(self.get_size()) - Point(0,0))
    (self._top_left, self._bottom_right) = (
      self._top_left + factor*ratio*(self._bottom_right - self._top_left),
      self._bottom_right + factor*(1-ratio)*(self._bottom_right - self._top_left))
    self._update()

  def translate(self, delta):
    """Translates the coordinates.

    The delta is for on-screen pixels to move.  If the image is
    already zoomed, this function will take care of it.
    """
    # Need to scale the drag amounts by the current zoom.
    zoom_scale = (self._bottom_right - self._top_left) / Point.from_tuple(self.get_size())
    delta = zoom_scale * delta
    self._top_left -= delta
    self._bottom_right -= delta
    self._update()

  def _update(self):
    if self._image:
      self._photo_image = self._image.get_photo_image(Point.from_tuple(self.get_size()),
                                                      self._top_left,
                                                      self._bottom_right)
      self.TKCanvas.itemconfig(self._image_id, image=self._photo_image)


ZOOM_FACTOR=0.1
CANVAS_SIZE=Point(500, 500)
CANVAS_ZERO=Point(0, 0)

def main():
  """Open a window and start the program."""
  sg.theme("LightBlue")
  left = ZoomGraph(CANVAS_SIZE,
                   key='left', float_values=True)
  diff = ZoomGraph(CANVAS_SIZE,
                   key='diff', float_values=True)
  right = ZoomGraph(CANVAS_SIZE,
                    key='right', float_values=True)
  layout = [ [left, sg.VerticalSeparator(pad=(0,0), key="divleft"),
              diff, sg.VerticalSeparator(pad=(0,0), key="divright"),
             right],
             [sg.HorizontalSeparator(pad=(0,0))],
             [sg.Button('Exit')] ]
  disable_updates = False
  diff_image = None
  diff_photo_image = None
  diff_image_id = None
  def make_listener(others):
    def listener(event):
      nonlocal disable_updates
      nonlocal diff_image
      nonlocal diff_photo_image
      if not disable_updates:
        disable_updates = True
        for other in others:
          other.handle_all(event)
        diff_image = ImageChops.difference(left.image.image, right.image.image)
        diff_photo_image = ImageTk.PhotoImage(diff_image)
        window['diff'].TKCanvas.itemconfig(diff_image_id, image=diff_photo_image)
        disable_updates = False
    return listener

  left.register_event_listener(make_listener([right]))
  right.register_event_listener(make_listener([left]))
  diff.register_event_listener(make_listener([left, right]))
  window = sg.Window('Window Title', layout, finalize=True, location=(0,0), resizable=True)
  left.finalize()
  right.finalize()
  diff.finalize()
  left.load_image(
    "/home/esoha/private/pcb2gcode/testing/gerbv_example/" +
    "multivibrator/processed_back.svg")
  right.load_image(
    "/home/esoha/private/pcb2gcode/testing/gerbv_example/" +
    "multivibrator/traced_back.svg")
  diff_image = ImageChops.difference(left.image.image, right.image.image)
  diff_photo_image = ImageTk.PhotoImage(diff_image)
  diff_image_id = window['diff'].TKCanvas.create_image((0,0),anchor=tk.NW, image=diff_photo_image)
  diff_height = window.size[1] - CANVAS_SIZE[1]
  diff_width = window.size[0] - CANVAS_SIZE[0]*3

  window.bind('<Configure>', "Configure")
  while True:
    event, _ = window.read()
    if event in (sg.WIN_CLOSED, "Exit"):
      break
    if event == "Configure":
      window['left'].set_size(((window.size[0]-diff_width)/3, window.size[1]-diff_height))
      window['diff'].set_size(((window.size[0]-diff_width)/3, window.size[1]-diff_height))
      window['right'].set_size(((window.size[0]-diff_width)/3, window.size[1]-diff_height))
  window.close()

if __name__ == "__main__":
  main()
