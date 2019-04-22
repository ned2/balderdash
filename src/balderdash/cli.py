"""Click command line script for running balderdash"""

import click

from .markdown_converter import MarkdownConverter


@click.command()
@click.argument("path")
@click.option("--app-path", type=click.Path(), default=".")
def main(path, app_path):
    converter = MarkdownConverter(app_path=app_path)
    with open(path, encoding="utf8") as f:
        dash_file = converter.convert(f)
    print(dash_file)
