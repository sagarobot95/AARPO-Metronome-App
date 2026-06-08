"""PyInstaller entry point.

Uses an absolute import so it works when frozen as a top-level script (where the
package-relative ``from .app import main`` in ``__main__.py`` would not).
"""

from aarpo_metronome.app import main

if __name__ == "__main__":
    main()
