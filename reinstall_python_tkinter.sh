#!/bin/bash

# Reinstall Python 3.11.7 with Tkinter support

export PATH="/opt/homebrew/opt/tcl-tk/bin:$PATH"
export LDFLAGS="-L/opt/homebrew/opt/tcl-tk/lib"
export CPPFLAGS="-I/opt/homebrew/opt/tcl-tk/include"
export PKG_CONFIG_PATH="/opt/homebrew/opt/tcl-tk/lib/pkgconfig"
export PYTHON_CONFIGURE_OPTS="--with-tcltk-includes='-I/opt/homebrew/opt/tcl-tk/include' --with-tcltk-libs='-L/opt/homebrew/opt/tcl-tk/lib -ltcl9.0 -ltk9.0'"

echo "Reinstalling Python 3.11.7 with Tkinter support..."
echo "This will take 5-10 minutes..."

pyenv install 3.11.7 --force

echo ""
echo "Installation complete! Testing Tkinter..."
python3 -m tkinter && echo "✓ Tkinter is working!" || echo "✗ Tkinter installation failed"
