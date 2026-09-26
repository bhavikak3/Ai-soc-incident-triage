"""
Minimal Streamlit stub for headless testing.

Importing this module in place of the real Streamlit lets the render functions
in app.py execute without a browser or server, while recording every call so
tests can assert on what was rendered.

It shadows the real `streamlit` package only for scripts run from inside this
`tests/` directory, because Python puts the script's own directory first on
sys.path. Running `streamlit run app.py` from the project root is unaffected.
"""

CALLS = []      # (method_name, payload) for every render call
MARKDOWN = []   # every text/html string emitted, by any method
HTML = []       # only strings passed with unsafe_allow_html=True
CLICK = set()   # button keys or labels that should report a click
RERUN = []      # appended to when st.rerun() fires


class _State(dict):
    """Stand-in for st.session_state: dict plus attribute access."""

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, key, value):
        self[key] = value


session_state = _State()


class _Rerun(Exception):
    """Raised by st.rerun() so tests can detect and absorb it."""


class _Ctx:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _Node:
    """Anything renderable: the module itself, a column, a tab, an expander."""

    def markdown(self, body="", unsafe_allow_html=False, **kw):
        CALLS.append(("markdown", body))
        MARKDOWN.append(str(body))
        if unsafe_allow_html:
            HTML.append(str(body))

    def write(self, body="", **kw):
        CALLS.append(("write", body))
        MARKDOWN.append(str(body))

    def caption(self, body="", **kw):
        CALLS.append(("caption", body))
        MARKDOWN.append(str(body))

    def info(self, body="", **kw):
        CALLS.append(("info", body))
        MARKDOWN.append(str(body))

    def success(self, body="", **kw):
        CALLS.append(("success", body))
        MARKDOWN.append(str(body))

    def warning(self, body="", **kw):
        CALLS.append(("warning", body))
        MARKDOWN.append(str(body))

    def error(self, body="", **kw):
        CALLS.append(("error", body))
        MARKDOWN.append(str(body))

    def divider(self):
        CALLS.append(("divider", None))

    def progress(self, value, **kw):
        assert 0.0 <= value <= 1.0, f"st.progress out of range: {value}"
        CALLS.append(("progress", value))

    def bar_chart(self, data, **kw):
        CALLS.append(("bar_chart", getattr(data, "shape", None)))

    def dataframe(self, data, **kw):
        CALLS.append(("dataframe", getattr(data, "shape", None)))

    def button(self, label, key=None, on_click=None, args=(), **kw):
        CALLS.append(("button", label))
        clicked = (key in CLICK) or (label in CLICK)
        if clicked and on_click:
            on_click(*args)
        return clicked

    def download_button(self, label, data=None, **kw):
        CALLS.append(("download_button", label))
        assert data is not None and len(data) > 0, "download_button got empty data"
        return False

    def text_area(self, label, key=None, value=None, **kw):
        CALLS.append(("text_area", label))
        if key is not None:
            return session_state.setdefault(key, value or "")
        return value or ""

    def text_input(self, label, key=None, value="", **kw):
        CALLS.append(("text_input", label))
        return session_state.get(key, value) if key else value

    def selectbox(self, label, options, index=0, key=None, **kw):
        CALLS.append(("selectbox", label))
        opts = list(options)
        if key in session_state:
            return session_state[key]
        return opts[index] if opts else None

    def radio(self, label, options, index=0, key=None, **kw):
        CALLS.append(("radio", label))
        opts = list(options)
        if key in session_state:
            return session_state[key]
        return opts[index] if opts else None

    def columns(self, spec, **kw):
        n = spec if isinstance(spec, int) else len(spec)
        return [_Tab() for _ in range(n)]  # real columns are context managers

    def tabs(self, labels):
        CALLS.append(("tabs", tuple(labels)))
        return [_Tab() for _ in labels]

    def expander(self, label, **kw):
        CALLS.append(("expander", label))
        return _Tab()

    def spinner(self, text=""):
        return _Ctx()

    def container(self, **kw):
        return _Tab()

    def set_page_config(self, **kw):
        CALLS.append(("set_page_config", None))

    def rerun(self):
        RERUN.append(True)
        raise _Rerun()


class _Tab(_Node, _Ctx):
    pass


def reset():
    """Clear all recorded state between test cases."""
    for lst in (CALLS, MARKDOWN, HTML, RERUN):
        lst.clear()
    CLICK.clear()


_module = _Node()

markdown = _module.markdown
write = _module.write
caption = _module.caption
info = _module.info
success = _module.success
warning = _module.warning
error = _module.error
divider = _module.divider
progress = _module.progress
bar_chart = _module.bar_chart
dataframe = _module.dataframe
button = _module.button
download_button = _module.download_button
text_area = _module.text_area
text_input = _module.text_input
selectbox = _module.selectbox
radio = _module.radio
columns = _module.columns
tabs = _module.tabs
expander = _module.expander
spinner = _module.spinner
container = _module.container
set_page_config = _module.set_page_config
rerun = _module.rerun
