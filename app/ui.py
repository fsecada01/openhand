"""JinjaX component catalog."""

from pathlib import Path

import jinja2
import jinjax
from jinjax.component import Component


class _Utf8Catalog(jinjax.Catalog):
    """Catalog that always reads component source as UTF-8.

    Upstream reads component files in two places with the *locale*
    encoding (cp1252 on Windows): `Component.__init__` (when not
    handed a `source`) and `get_source`. That crashes on emoji with
    variation selectors and silently mojibakes everything else
    non-ASCII. Both overrides below read the file as UTF-8 up front
    and otherwise mirror upstream.
    """

    def _get_from_file(
        self, *, prefix: str, name: str, file_ext: str
    ) -> Component | None:
        path, relpath = self._get_component_path(
            prefix, name, file_ext=file_ext
        )
        if path is None or relpath is None:
            return None
        source = path.read_text(encoding="utf-8")
        component = Component(
            name=name,
            prefix=prefix,
            path=path,
            relpath=relpath,
            source=source,
        )
        gs = self.jinja_env.make_globals(self.tmpl_globals)
        code = self.jinja_env.compile(
            source, name=str(relpath.as_posix()), filename=str(path)
        )
        component.tmpl = self.jinja_env.template_class.from_code(
            self.jinja_env, code, gs
        )
        return component

    def get_source(self, cname: str, file_ext: str = "") -> str:
        file_ext = file_ext or self.file_ext
        prefix, name = self._split_name(cname)
        path, _relpath = self._get_component_path(
            prefix, name, file_ext=file_ext
        )
        if not path:
            raise jinjax.ComponentNotFound(cname, file_ext)
        return path.read_text(encoding="utf-8")


# JinjaX's default environment does NOT autoescape. Without it, any
# `"` a person types into their narrative truncates the hidden
# prior_narrative/profile_json fields that carry the conversation
# between rounds (silent data loss), and narrative text is injectable
# as live HTML. Everything rendered here interpolates user input, so
# escaping is non-negotiable.
catalog = _Utf8Catalog(jinja_env=jinja2.Environment(autoescape=True))
catalog.add_folder(Path(__file__).resolve().parent / "components")
