pypgf - Python PGF Tools
========================

Just a script to help laying out fonts for PSP translations. Much thanks to JPCSP for its PGF/SceFont implementation which I used as a reference.

Usage
-----

This script is intended to be used as a module by another Python script i.e., Create a PGFFont instance and call wrap_text as needed. I've also included a simple mode for laying out a single line of text from the command line via 
     python pypgf/pypgf.py pgf-font-file ""Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea"

The final line will return a list of "chunks", each chunk should fit on a single on-screen line

Setup
-----

This requires the bitstring and numpy modules. Either install them through your package manager of choice or type "pip install" from the root directory of this project. I'll create a distribution at some point.

     easy_install numpy bitstring

Should also work

You'll need a pgf font for this to work, Ideally you'll want to use a dumped pgf font from your psp. 
