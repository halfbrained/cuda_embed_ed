Plugin for CudaText.

Shows documents in an embedded editor. For example '.js' and '.css' files in HTML.

Adds menu item to show/hide embedded editor in the current document:
    "Plugins > Embedded Editor > Toggle"


Searches for a relative path according to configurable set of patterns under caret's position. 
By default it's a path between quotation marks (") globally, and a Pascal-lexer specific format.

So if file is opened: 
    "/folder/file.html" 
    
 and an embedded editor is opened in `href` value in text:
    <link href="css/style.css" rel="stylesheet" type="text/css"/>
    
 following file will be shown:
    "/folder/css/style.css"
    
    
Patterns can be edited via main menu:
	"Options > Settings-plugins > Embedded Editor > Config patterns"
	
Comments in the config descibe the format.

About
-----
Author: Shovel, https://github.com/halfbrained/
License: MIT
