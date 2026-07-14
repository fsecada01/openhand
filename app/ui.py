"""JinjaX component catalog."""

from pathlib import Path

import jinja2
import jinjax

# JinjaX's default environment does NOT autoescape. Without it, any
# `"` a person types into their narrative truncates the hidden
# prior_narrative/profile_json fields that carry the conversation
# between rounds (silent data loss), and narrative text is injectable
# as live HTML. Everything rendered here interpolates user input, so
# escaping is non-negotiable.
catalog = jinjax.Catalog(jinja_env=jinja2.Environment(autoescape=True))
catalog.add_folder(Path(__file__).resolve().parent / "components")
