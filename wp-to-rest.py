#!/usr/bin/python3.5

#
# Copyright (c) 2018, James C. McPherson. All Rights Reserved.
#

# Available under the terms of the MIT license:
#
# Permission is hereby granted, free of charge, to any
# person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the
# Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the
# Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice
# shall be included in all copies or substantial portions of
# the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY
# KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
# PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS
# OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


import bs4
import getopt
import os
import re
import sys
import time


__USAGE = """
Usage:

wp-to-rest <directory tree to process> <output directory>

This is a very simple script which aims to turn WordPress posts
into reST-formatted documents suitable to importing into a blog
engine such as Nikola or Pelican.

This tool operates on a BEST EFFORT basis - each translated file
mst be checked for accuracy prior to use with a blog engine.

It works for me, but you might need to hack on it for your purposes.
"""

__USAGE = __USAGE.strip()

__doc__ = __USAGE

# We search the posts that we find for three specific <div..> attributes:
#
# post-headline, post-bodycopy, post-footer
#
# post-headline gives us the title of the post without any extra bits
# post-bodycopy gives the text of the post which we want to massage into reST
# post-footer gives us the categories which the post appeared in.
#
# Rather than using the post-footer to tell us the publication date, we
# construct that from the post directory name and assert that all posts
# occurred at 10:00 in (time.strftime("%z")) - your utc offset.
#
# Once we have the information required for the post metadata, we start
# constructing the output file.


METADATA_TMPL="""
.. title: {0}
.. date: {1}T10:00:00 {2}
.. tags: {3}
.. category: {4}\n
"""

URL_TMPL=".. _{0}: {1}\n"
IMG_TMPL="\n.. image:: {0}\n"
PRE_TMPL="\n.. code-block::\n    "



def urlreplace(instr):
    instr = instr.replace("http://www.jmcpdotcom.com/rollerhttp", "http")
    instr = instr.replace("http://www.jmcpdotcom.com/blog/wp-content/uploads",
                          "")
    instr = instr.replace("http://www.jmcpdotcom.com/blog/wp-includes",
                          "")
    instr = instr.replace(
        "http://www.jmcpdotcom.com/wordpress/3.3/wp-content/uploads",
        "")
    return instr


def handle_img(tag):
    imgdecl = IMG_TMPL.format(tag.get("src"))
    imgdecl = urlreplace(imgdecl)
    if tag.get("height"):
        imgdecl += ("    :height: {0}\n".format(tag.get("height")))
    if tag.get("width"):
        imgdecl += ("    :width: {0}\n".format(tag.get("width")))
    if tag.get("alt"):
        imgdecl += ("    :alt: {0}\n".format(tag.get("alt")))
    if tag.get("title"):
        print("\timage ref {0} has 'title' when it should just have 'alt'".
              format(tag.get("src")))
    imgdecl += "\n"
    return imgdecl
                       

def handle_thtd(tdata):
    cells = []
    for tdel in tdata:
        if isinstance(tdel, bs4.element.NavigableString):
            if tdel.string != '\n':
                cells.append(tdel)
        else:
            cells.append(tags_r(tdel))
    #print("\tcalled with {0}\n\treturning {1}\n".format(tdata, cells))
    return cells


def format_thtd(cells, celltype):
    # Called on a per-row basis
    outstr = ""
    # Handle the top of the table, key off whether we're given '='
    # for celltype.
    if celltype is "=":
        outstr += "+"
        for col in cells:
            outstr += '-' * (len(col) + 2) + "+"
        outstr += "\n"
    tstr = "| "
    lstr = "+"
    for col in cells:
        tstr += col + " | "
        lstr += celltype * (len(col) + 2) + "+"
    tstr += "\n"
    tstr = urlreplace(tstr)
    lstr += "\n"
    outstr += tstr
    outstr += lstr
    return(outstr)





def handle_table(tag):
    allrows = []
    restr = ""
    for jk in tag.children:
        #print(jk.name)
        if not jk.name or jk.name is "tbody":
            #print("skipping tbody")
            continue
        if not isinstance(jk, bs4.element.NavigableString):
            allrows.append(handle_thtd(jk))
    retstr = format_thtd(allrows[0], "=")
    for _l in range(1, len(allrows)):
        retstr += format_thtd(allrows[_l], "-")
    return retstr


            
def handle_pre(tag):
    predecl = PRE_TMPL
    for line in tag.contents:
        if isinstance(line, bs4.element.Tag):
            if not line.is_empty_element:
                predecl += tags_r(line)
        else:
            predecl += line.replace("\n", "\n    ")
    predecl += "\n\n"
    return predecl


def handle_blockquote(tag):
    line = "::\n  "
    for el in tag.contents:
        if isinstance(el, bs4.element.Tag):
            line += tags_r(el)
        else:
            line += el + "\n  "
    line += "\n"
    return line


def handle_a(tag):
    retstr = ""
    if isinstance(tag, bs4.element.NavigableString):
        retstr += tag
    else:
        retstr = tags_r(tag)
    url = "`{0}`_\ ".format(retstr)
    return url


def tags_r(arg):
    retstr = ""
    for el in arg.contents:
        if isinstance(el, bs4.element.NavigableString) and len(el) > 0:
            retstr += el.strip("\n")
        elif el.__dict__['name'] == "br":
            continue
        elif el.__dict__['name'] == "blockquote":
            retstr += handle_blockquote(el)
        elif el.__dict__['name'].startswith("img"):
            retstr += handle_img(el)
        elif el.__dict__['name'].startswith("a"):
            retstr += handle_a(el)
        elif el.__dict__['name'] == "tt":
            retstr += "``" + tags_r(el) + "``"
        elif el.__dict__['name'] == "it" or el.__dict__['name'] == "i":
            retstr += "*"  + tags_r(el) + "*"
        elif el.__dict__['name'] == "b" or el.__dict__['name'] == "strong":
            retstr += "**"  + tags_r(el) + "**"
        elif el.__dict__['name'] == "ul":
            retstr += "\n" + tags_r(el)
        elif el.__dict__['name'] == "li":
            retstr += "\n  - " + tags_r(el)
        elif el.__dict__['name'] == "ol":
            retstr += "\n" + tags_r(el)
        elif el.__dict__['name'] == "hr":
            retstr += "\n........ \n" 
        elif el.__dict__['name'] == "h1":
            outstr = "".join(el.contents)
            retstr += "\n" + outstr
            retstr += "\n" + '=' * len(outstr)
        elif el.__dict__['name'] == "h2" or el.__dict__['name'] == "h3":
            outstr = ""
            if not isinstance(el, bs4.element.NavigableString):
                outstr += tags_r(el)
            else:
                #print(type(el))
                outstr += el.strip("\n")
            retstr += "\n" + outstr
            retstr += "\n" + '-' * len(outstr)
        elif el.__dict__['name'] == "p":
            retstr += "\n"
            retstr += tags_r(el)
            retstr += "\n"
        elif el.__dict__['name'] == "div":
            print("\tGot a <div> with attrs {0}".format(el.attrs))
        elif el.__dict__['name'] == "table":
            retstr += handle_table(el)
            retstr += "\n"
        elif el.__dict__['name'].startswith("pre") or \
             el.__dict__['name'].startswith("code"):
            retstr += handle_pre(el)
            retstr += "\n"
        elif el.__dict__['name'] == "font":
            retstr += "\n.. raw:: html\n" + el.contents + "\n"
        else:
            print("\tunknown tag name: {0}".format(el.__dict__['name']))
            print("\ttag contents:\n{0}".format(el.contents))
            retstr += tags_r(el)
    return retstr


def get_other_meta(footer):
    """
    Obtain the category list, publish date and slug from the footer.
    """
    catlist = []
    for elem in footer.findAll("a", {'rel': 'category tag'}):
        catlist.append(elem.text)
    theREs = re.compile(r"(.*/blog/)((\d{4}/\d{2}/\d{2})(.*))/#.*")
    try:
        slugall = footer.find("a", {'class': 'comments-link'}).get('href')
    except AttributeError as _exc:
        return catlist, None, None
    slugfn = theREs.match(slugall).group(2).replace('/', '-')
    pubdate = theREs.match(slugall).group(3).replace('/', '-')
    return catlist, slugfn, pubdate


def get_post_title(post_head):
    """ Obtain the title of the post, returns a string."""
    try:
        title = post_head.find("h1").text
    except AttributeError as _exc:
        try:
            title = post_head.find("h2").text
        except AttributeError as _exc2:
            title = "ERROR: NO TITLE DECLARATION FOUND IN {0}".format(
                post_head)
    return title.replace("\n", "").replace("\t", "")


def get_list_of_posts(startdir, strippath):
    """
    Returns a dict of {slugified-post-title: filename} to work on. If
    strippath is not None, then we remove every strippath from the
    slugified entry.
    """
    postlist = {}
    for dirname, _dirs, fname in os.walk(startdir):
        if len(fname) > 0:
            dirk = dirname
            if strippath:
                dirk = dirk.replace(strippath, "")
            dirk = dirk.replace("/", "-")
            for i in fname:
                postlist[dirk] = os.path.join(dirname, i)
    return postlist



if __name__ == "__main__":
    """ main function, where we provide direction. """

    startdir = sys.argv[1]
    outfdir = sys.argv[2]

    # get the list of files to process
    allposts = get_list_of_posts(startdir, None)

    utcoff = time.strftime("%z")

    if not os.path.exists(outfdir):
        os.makedirs(outfdir)

    for slug in allposts:
        fname = allposts[slug]
        print("opening {0}".format(fname))
        soup = bs4.BeautifulSoup(open(fname, "r"), "html.parser")
        # How many posts do we have in this file? I really wish that
        # findNext() was an iterator. Instead, find all the headers,
        # bodycopy and footer elements, and make the assumption that
        # they've been returned in associated order. We rely on the
        # human to check this.
        post_heads = soup.findAll(name="div", attrs={'class': 'post-headline'})
        post_bodies = soup.findAll(name="div", attrs={'class': 'post-bodycopy'})
        post_footers = soup.findAll(name="div", attrs={'class': 'post-footer'})

        if len(post_heads) != len(post_bodies) or len(post_heads) != len(post_footers) \
           or len(post_bodies) != len(post_footers):
            # urg
            print("Differing numbers of headers, bodies and footers in {0}.\n"
                  "Manual pre-processing required, sorry\n".format(fname))
            print("headers: {0}\n{1}\n----\n # bodies {2}\n----\nfooters: {3}\n{4}".format(
                len(post_heads), post_heads, len(post_bodies),
                len(post_footers), [j for j in post_footers.findAll("a", {"class":"comments-link"})]))
            continue
        for idx in range(len(post_heads)):
            title = get_post_title(post_heads[idx])
            print("\tidx {0} has title :: {1}".format(idx, title))
            # Get our list of hrefs
            post_hrefs = {}
            for ref in post_bodies[idx].findAll("a"):
                #print(ref.__dict__)
                if ref.has_attr('id'):
                    post_hrefs[ref['id']] = ref.text
                else:
                    post_hrefs[ref.text] = ref['href']
            outstr = tags_r(post_bodies[idx])
            categories, slugfn, pubdate = get_other_meta(post_footers[idx])
            if slugfn is None:
                # new-style footer, have to use a different approach
                pubdate = slug[0:10]
                slugfn = slug
            outfn = os.path.join(outfdir, slugfn) + ".rst"
            outf = open(outfn, "w")
            metablock = METADATA_TMPL.format(title,
                                             pubdate, utcoff,
                                             ", ".join(categories),
                                             categories[0])
            #print(metablock)
            outf.write(metablock)
            outf.write(outstr)
            outf.write("\n")
            urlblock = ""
            for k in post_hrefs:
                urlblock += URL_TMPL.format(k, post_hrefs[k])
            urlblock = urlblock.replace("http://www.jmcpdotcom.com/rollerhttp",
                                        "http")
            urlblock = urlblock.replace(
                "http://www.jmcpdotcom.com/blog/wp-content/uploads",
                "")
            urlblock = urlblock.replace(
                "http://www.jmcpdotcom.com/blog/wp-includes",
                "")
            outf.write(urlblock)
            outf.write("\n")
            outf.close()
        print("Finished processing {0}\n".format(fname))
