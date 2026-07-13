"""JinjaX component catalog."""

from pathlib import Path

import jinjax

catalog = jinjax.Catalog()
catalog.add_folder(Path(__file__).resolve().parent / "components")
