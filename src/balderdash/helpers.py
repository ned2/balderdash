import regex
from dash.development.base_component import Component

from .exceptions import ImproperlyConfigured


def component_to_str(component):
    """Convert a Dash Component into an evalable string"""
    props_with_values = [c for c in component._prop_names
                         if getattr(component, c, None) is not None]
    wc_props_with_values = [
        c for c in component.__dict__
        if any(
            c.startswith(wc_attr)
            for wc_attr in component._valid_wildcard_attributes
        )
    ]

    all_props_with_values = props_with_values + wc_props_with_values

    def prop_to_str(component, prop):
        value = getattr(component, prop)

        if isinstance(value, Component):
            return component_to_str(value)
        
        if isinstance(value, list):
            components = ", ".join(component_to_str(c) for c in value)
            return f"[{components}]"
        
        return repr(value)
    props_string = ", ".join(f"{prop}={prop_to_str(component, prop)}"
                             for prop in props_with_values)
    return f"{component._type}({props_string})"


def preprocess_dash_app(content, precode):
    # strip `app = Dash()``
    content = regex.sub("app?\s=?\sDash(\((?>[^)(]+|(?1))*+\))", "", content)
    return f"{precode}\n\n{content}"


def load_dash_app(path, app, precode="", encoding="utf8"):
    with open(path, encoding=encoding) as f:
        content = f.read()
    content = preprocess_dash_app(content, precode)
    scope = {"app": app}
    exec(content, scope)

    not_configured = ImproperlyConfigured(
        "Your included Dash app must define either an `app` "
        "attribute, which is Dash instance that is associated with "
        "a layout, or a `layout` attribute, which is a Dash "
        "Component."
    )
    
    try:
        layout = scope["app"].layout
    except KeyError as error:
        try:
            layout = scope["layout"].layout
        except KeyError as error:
            raise not_configured
        
    if callable(layout):
        layout = layout()

    if layout is None:
        raise not_configured
    
    return layout
