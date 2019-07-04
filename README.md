# balderdash

A tool for authoring Dash apps as Markdown documents.

This project is currently in the proof of concept phase. The goal is to provide
a tool that enables you to author Dash apps as Markdown documents, in the same
spirit as tools like R's [Blogdown](https://bookdown.org/yihui/blogdown/).

This allows you to easily publish articles and blog posts etc that include
inline interactive Dash apps, by separating (at the source-code level) the prose
from the various apps featured inline. This style of content is useful for
documenting the results of an analysis or model, or for content that is
explaining a complex idea. This latter category of content has been described as
[Explorable Explanations](https://explorabl.es/).


## Syntax

Currently, the syntax for including Dash apps within Markdown uses
[Pandoc](https://pandoc.org) style mark-up. A basic Balderdash document that
includes a single Dash app looks like this:


    # This is a Balderdash Markdown file
    
    You can see that there's a bunch of Markdown, followed by an inline Dash app:
    
    ```{.dash app=character_counter.py}
    ```
    
    And then some more text as Markdown.

Where the file `character_counter.py` is a Python module containing either an `app`
attribute that is a `Dash` instance, or a `layout` attribute, that is a valid Dash 
component tree.


## Running Balderdash

Install Balderdash into your virtual environment:

    $ pip install -e path_to_balderdash

To convert the above Markdown document into a Dash app using Balderdash, run the
following command:

    $ bdash --app-path apps test.md > test_app.py
    
This assumes the `character_counter.py` module (or any other app used in the
document) is found in the path specified by the `--app-path` parameter.

You can now run `test_app.py` as a regular Dash app using the development server
like so:

    $ python test_app.py
