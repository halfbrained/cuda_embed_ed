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

1) File settings/plugins.ini (it is shared by many plugins).
Section: [embedded_editor].
2) File "cuda_embed_ed_patterns.json", to configure search patterns.
It has some default content so it is self-documented.

About
-----
Author: Shovel, https://github.com/halfbrained/
License: MIT
