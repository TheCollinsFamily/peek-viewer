RFab Viewer for Linux (x86-64)

Run it:      ./"RFab Viewer" picture.jpg        (or a folder)
Install it:  ./install.sh
             -> a menu entry, "Open With" for images and videos, and the command rfab-viewer
Remove it:   ~/.local/opt/rfab-viewer/uninstall.sh

It needs a desktop (X11 or Wayland) and the usual Qt libraries, which every mainstream
distribution ships. If it stops with "could not load the Qt platform plugin xcb",
install libxcb-cursor:
  Debian / Ubuntu:  sudo apt install libxcb-cursor0
  Fedora:           sudo dnf install xcb-util-cursor
Video playback uses the system's GStreamer plugins (gstreamer1.0-plugins-good and -bad
on Ubuntu). Pictures need nothing extra.

Keys:  Left / Right  next file      F  full screen      G  grid view
       S  slideshow                 Esc  close          Ctrl+`  boss key (hide everything)

Log file:  /tmp/rfab_viewer.log
Source:    https://github.com/TheCollinsFamily/peek-viewer
