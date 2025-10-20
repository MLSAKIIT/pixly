## Pixly Quick Start Guide 
A guide to setup Pixly in your desktop.
### 📋 Prerequisites
<div>

<table>
<tr>
<td align="center" width="25%">

**🐍 Python 3.11+**
```bash
python --version
```

</td>
<td align="center" width="25%">

**🪟 Windows 10/11** or **🍎 macOS**
```bash
# Check your OS
uname -s
```

</td>
<td align="center" width="25%">

**⚡ uv Package Manager**

```bash
pip install uv
```
</td>

<td align="center" width="25%">

**🔧 Git**
```bash
git --version
```

</td>
</tr>
</table>
</div>


### Quick Setup (Windows)

1. Clone the repository :
```bash
git clone https://github.com/MLSAKIIT/pixly.git
cd pixly
```
2. Open a powershell terminal as administrator and run the setup.bat file.
```bash
.\setup.bat
```

### macOS Setup

#### Prerequisites: Tkinter Support

Pixly requires Tkinter for the GUI overlay. If you're using `pyenv`, you need to install Python with Tkinter support:

1. **Install tcl-tk via Homebrew**:
```bash
brew install tcl-tk
```

2. **Reinstall Python 3.11+ with Tkinter support**:
```bash
# Use the provided script
chmod +x reinstall_python_tkinter.sh
./reinstall_python_tkinter.sh
```

Or manually:
```bash
export PATH="/opt/homebrew/opt/tcl-tk/bin:$PATH"
export LDFLAGS="-L/opt/homebrew/opt/tcl-tk/lib"
export CPPFLAGS="-I/opt/homebrew/opt/tcl-tk/include"
export PKG_CONFIG_PATH="/opt/homebrew/opt/tcl-tk/lib/pkgconfig"
export PYTHON_CONFIGURE_OPTS="--with-tcltk-includes='-I/opt/homebrew/opt/tcl-tk/include' --with-tcltk-libs='-L/opt/homebrew/opt/tcl-tk/lib -ltcl9.0 -ltk9.0'"

pyenv install 3.11.7 --force
```

3. **Verify Tkinter is working**:
```bash
python3 -m tkinter
```
If a small window appears, Tkinter is working correctly!

4. **Continue with Manual Setup below**

### Manual Setup 
1. Clone the repository : 
```bash 
git clone https://github.com/MLSAKIIT/pixly.git
cd pixly
```
1. Install uv package manager 
```bash 
pip install uv
# or
curl -LsSf https://astral.sh/uv/install.sh | sh
```
1. Install dependencies 
```bash
uv sync
```
1. Set up environment variables : 
   1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
   2. Create a new API key
   3. Add to `.env`:
```bash
GEMINI_API_KEY=your_gemini_key_here
```

1. Make a folder called `vector_db`

2. Start the application

**On Windows** - Create two PowerShell terminals:

Terminal 1 - Start Backend:
```bash
uv run run.py
```
Wait for the backend to start then in Terminal 2 - Start Frontend:
```bash
uv run overlay.py
```

**On macOS** - Create two terminal windows:

Terminal 1 - Start Backend:
```bash
uv run run.py
```
Wait for the backend to start then in Terminal 2 - Start Frontend:
```bash
uv run overlay.py
```

## Troubleshooting

### macOS: "ModuleNotFoundError: No module named '_tkinter'"

This error occurs when Python doesn't have Tkinter support. Follow the **macOS Setup** section above to reinstall Python with Tkinter.

Quick fix:
```bash
brew install tcl-tk
chmod +x reinstall_python_tkinter.sh
./reinstall_python_tkinter.sh
```

### macOS: Platform-specific dependencies

The project automatically installs platform-specific dependencies:
- **Windows**: `pywin32` for window detection
- **macOS**: `pyobjc-framework-Quartz` for window detection

No manual intervention needed - `uv sync` handles this automatically!

## Debugging

To test the various parts of the backend pipeline:

1. Start the server in Terminal 1:
```bash
uv run run.py
```
2. Start the test script in Terminal 2:
```bash
uv run test_system.py
```