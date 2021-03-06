#!/usr/bin/env python

"""

A wrapper for conversion libraries like Mammoth and html2textile
and of course my own XSLT stylesheet

"""

import os, io, re, ntpath, subprocess

import mammoth, base64
from html2textile import *
from lxml import html, etree
from PIL import Image

import stylemapper

def _noPath(path):
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)

def _prePath(path):
    head, tail = ntpath.split(path)
    return head + "/"

def _splitFullPath(fullPath):
    baseDir = _prePath(fullPath)
    fileName = os.path.splitext( _noPath(fullPath) )[0]
    scriptPath = _prePath(os.path.abspath(__file__))
    return {'fullPath': fullPath, 'baseDir': baseDir, 'fileName': fileName, 'scriptPath': scriptPath }

def _parse_from_unicode(unicode_str):
    utf8_parser = etree.XMLParser(encoding='utf-8')
    s = unicode_str.encode('utf-8')
    return etree.fromstring(s, parser=utf8_parser)

# Custom image handler for Mammoth
# --------------------------------
def add_dimensions(image):

    with image.open() as image_source:
        image_bytes = image_source.read()
        encoded_src = base64.b64encode(image_bytes).decode("ascii")
        img_size = Image.open(io.BytesIO(image_bytes)).size

    img = {
        "src": "data:{0};base64,{1}".format(image.content_type, encoded_src)
    }

    if img_size:
        img["width"]  = str(img_size[0]);
        img["height"] = str(img_size[1]);

    return img

def docx_to_html(filePath, style_map):
    pathInfo = _splitFullPath(filePath)
    with open(filePath, "rb") as docx_file:
        result = mammoth.convert_to_html(docx_file, style_map=style_map, ignore_empty_paragraphs=False, convert_image=mammoth.images.img_element(add_dimensions))
        messages = result.messages # Any messages, such as warnings during conversion
        html = "<body>" + result.value + "</body>" # XML needs a root tag
        
        prettyhtml = etree.tostring(_parse_from_unicode(html) ) #pretty_print=True indesign parses spaces
        
        # START TEXT CLEAN
        # ----------------
        # remove empy white space at beginning of paragraphs
        prettyhtml = re.sub(r"(?<=\<p\>)\s+", "", prettyhtml)
        # remove empy white space at end of paragraphs
        prettyhtml = re.sub(r"\s+(?=\<\/p\>)", "", prettyhtml)

        # replace empty paragraphs (with or without class) with line break <br />
        prettyhtml = re.sub(r"\<p(\s((class)|(id))=[\'\"][A-z0-9\s]+[\'\"]\s*)*\>\s*\<\/p\>", "<br />", prettyhtml)
        prettyhtml = re.sub(r"<p\s*/>", "<br />", prettyhtml)

        # multiple to single line break
        prettyhtml = re.sub(r"(\s*\<br\s*\/?\>){2,}", "<br />", prettyhtml, flags=re.IGNORECASE)
        
        # remove double spaces
        prettyhtml = re.sub(" +", " ", prettyhtml)
        # revert to original class names
        prettyhtml = prettyhtml.replace(' class="x-', ' class="')
        
        # END TEXT CLEAN
        # ----------------

        htmlPathStr = os.path.join(pathInfo["baseDir"], pathInfo["fileName"] + ".html")
        
        saveFile = open( htmlPathStr, "w+")
        saveFile.write( prettyhtml )
        saveFile.close()


    # Display any messages, such as warnings during conversion
    for m in messages:
        print m
        
    print "INFO: docxcavate finished conversion from DOCX to HTML"

    return htmlPathStr

def html_to_textile(filePath):
    pathInfo = _splitFullPath(filePath)
    html = etree.parse(filePath)
    prettyhtml = etree.tostring(html, pretty_print = True)
    textile = html2textile( prettyhtml );
    texPathStr = os.path.join(pathInfo["baseDir"], pathInfo["fileName"] + ".textile")
    saveFile = io.open( texPathStr, "w+", encoding='utf8')
    saveFile.write( textile )
    saveFile.close()

def html_to_icml(filePath):
    pathInfo = _splitFullPath(filePath)
    icmlPathStr = os.path.join(pathInfo["baseDir"], pathInfo["fileName"] + ".icml")
    # Call a system process
    output = subprocess.call(["java", "-cp", os.path.join(pathInfo["scriptPath"], "saxon9he.jar"), "net.sf.saxon.Transform", "-t", "-s:"+os.path.join(pathInfo["baseDir"], pathInfo["fileName"] + ".html"), "-xsl:"+os.path.join(pathInfo["scriptPath"], "xhtml_2_icml.xslt"), "-o:"+os.path.join(pathInfo["baseDir"], pathInfo["fileName"] + ".icml")], stderr=subprocess.STDOUT)
    print output or "INFO: docxcavate finished conversion from HTML to ICML"
    return icmlPathStr

def convert(docxPath, custom_xsltPath):
    # Generate stylemap
    styleMap = stylemapper.create_stylemap(docxPath);
    # XHTML is the heart of all conversion
    htmlPath = docx_to_html(docxPath, styleMap);
    # html_to_textile(htmlPath);
    icmlPath = html_to_icml(htmlPath);
    return ["Done"]
    
