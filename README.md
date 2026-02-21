*Currently requires Maple 2025 to convert latex to MathML.*
# Image2Maple
**Image2Maple** is a python program that can be activated with ``ctrl+alt+shift+v``, it takes an image from the user's clipboard then and pastes the corresponding MathML code, this is nice because MathML when pasted is automatically interpolated as a math object in maple, and other software such as word.  

**FYI:** This program creates a startup script at ``%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`` when run. There is **currently** no toggle on or off. It is deleted manually or with the ``Uninstall_ImageToMaple.exe`` or ``.py``.
## Installation
* The program can be 'installed' or run through the exe in the releases. You may be prompted with a window saying *Windows Protected Your PC* this is standard for unsigned exes, simply press *More Info* and *Run Anyways*, then press *Yes* to Admin Privileges.
* Or just by downloading the source code and running the python script ``ImageToMaple.py`` with the necessary dependencies installed.

*Note: If you do not want to use the slow render backend, you can just connect to the api yourself, for more information refer to the simpletex documentation (https://simpletex.net/api_doc). This can't be done with the exe.*
## Uninstallation
To uninstall **Image2Maple** simple run the ``Uninstall_ImageToMaple.exe`` or ``.py`` script, it will uninstall the *startup script, logs, config and ImageToMaple.exe*, while closing the running instance. It will bring up a console that shows what it is doing.  

*Note: The **only** thing left after uninstalling should be the uninstall script itself.*
## Program Flow
When you run the ``ImageToMaple.exe`` or ``.py`` it does the following:
1. Finds Maple 2025 executable and prompts user for path if its not at the default location.
2. Creates a startup ``ImageToMaple.lnk`` script at ``%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup``.  

When you press ``ctrl+alt+shift+v`` it does the following:
1. Checks whether you have Maple or Word focused.
2. Checks internet connection.
3. Grabs clipboard image.
4. Performs an API post to (https://image2maple.onrender.com/imagetolatex) with the image.
5. Converts the latex to MathML using Maple 2025 and the command ``MathML:-FromLatex(L);``.
6. Pastes the result at the cursor.

