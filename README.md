* pypgf - Python PGF Tools

Just a script to help laying out fonts for PSP translations. Much thanks to JPCSP for its PGF/SceFont implementation which I used as a reference.

* Usage

This script is intended to be used as a module by another Python script i.e., Create a PGFFont instance and call wrap_text as needed. I've also included a simple mode for laying out a single line of text from the command line via 
python pypgf/pypgf.py pgf-font-file "Testing layout"

The final line will return a list of "chunks", each chunk should fit on a single on-screen line

* Setup

This requires the bitstring and numpy modules. Either install them through your package manager of choice or type "pip install" from the root directory of this project. I'll create a distribution at some point.
