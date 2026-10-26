"""Expose the same shipped language reference in desktop and editor clients."""
from importlib.resources import files
from xml.etree import ElementTree


def topics():
    root = ElementTree.fromstring(files("plankalkulsharp").joinpath("dotnet_assets", "desktop", "LanguageHelp.xaml").read_text(encoding="utf-8"))
    ns = "{http://schemas.microsoft.com/winfx/2006/xaml/presentation}"
    return [{"title": section.attrib["Tag"], "paragraphs": [
        {"text": "".join(paragraph.itertext()).strip(), "code": paragraph.attrib.get("FontFamily") == "Consolas"}
        for paragraph in section.findall(ns + "Paragraph")
    ]} for section in root.iter(ns + "Section")]
