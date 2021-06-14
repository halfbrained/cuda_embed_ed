Plugin for CudaText.
Shows "included" file in embedded editor - additional editor UI control is
shown between the text lines.
For example, you can open included .css / .js files while editing the HTML file.

Adds menu item to show/hide embedded editor in the current document, for the
current caret position: "Plugins > Embedded Editor > Toggle".

By default, plugin searches for the included filename inside double-quotes,
surrounding the caret position. This works OK for HTML and many other documents.

For example, when you have opened file "/folder/file.html", and placed caret
inside first double-quotes: 
  <link href="css/style.css" rel="stylesheet" type="text/css"/>
then embedded editor will be opened for file "/folder/css/style.css".

The search can be configured, though. For example, plugin can be used in Pascal
files for comments like {$I filename.inc}.

Configuration
-------------

Plugin has 2 config files, you will see 2 menu items in the
"Options > Settings-plugins > Embedded Editor".

1) File "plugins.ini" (shared by many plugins).
Section [embedded_editor].
Options description:
* "editor_max_lines" - height of embedded editor in text lines
* "show_line_num" - how to show line numbers; possible values:
    0 - hide
    1 - show
    2 - use CudaText settings (default)
    
2) File "cuda_embed_ed_patterns.json", to configure search patterns.
It has some default content so it is self-documented.

API for other plugins
---------------------

Plugins can use such API to open the embedded editor for any
given filename inside the current document:

    try:
        from cuda_embed_ed import open_file_embedded
        open_file_embedded(file_name, line_index)
    except ImportError:
        msg_status('Plugin "Embedded Editor" is not installed')    

open_file_embedded() parameters:
* 1st - full path to a text file to open
* 2nd - line index after which to insert the embedded editor
Optional parameters:
* "caption" - caption to show instead of the full path
* "scroll_to" - tuple (x,y), character and line indexes, scroll position in the opened document
* "carets" - carets positions, a list of caret positions, caret position can be [x,y] or 
        [x0,y0, x1,y1] for selection


About
-----
Author: Shovel, https://github.com/halfbrained/
License: MIT
