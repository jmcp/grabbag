#!/usr/bin/env python3.7

#
# Copyright (c) 2019, James C. McPherson. All Rights Reserved.
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

import datetime
import json
import re
import sys

from bs4 import BeautifulSoup

__doc__ = """
This script extracts ABS Mesh Block names (SA1), Suburb/Locality
names (SA2) and polygon points from the ABS' SA1 dataset after
conversion with ogr2ogr.

Once the data has been extracted we dump it to a file in JSON format.

This is a *very* quick-n-dirty script - it takes two arguments (only);
the first is the ABS' CSV-formatted mesh block to State Electoral Division
file, the second is the mesh block kml.

TODO: Each time there is a redistribution of electorates, this script
must be re-run.

TODO: add functionality to check whether a particular electorate
has been redistributed, and notify the user while updating the
database entry for the affected areas.

TODO: add support for checking local government areas.
"""

usagestr = """

USAGE
-----

SA1-to-mbpt.py SEDfile.csv MB.kml

    SEDfile.csv is the ABS' CSV-formatted Mesh Block / Electorate file
    MB.kml is the ABS' kml containing all the Mesh Blocks in Australia.

"""

# Each electorate is 'Name' : points. We also stash the date and
# time the script is run, and the full filename
electorates = {}

# We're ignoring the "(OT)" entries
alljuris = {
    "Australian Capital Territory": "ACT",
    "New South Wales": "NSW",
    "Northern Territory": "NT",
    "Queensland": "QLD",
    "South Australia": "SA",
    "Tasmania": "TAS",
    "Victoria": "VIC",
    "Western Australia": "WA",
    "Other Territories": "(OT)"
}

# regex to match the "divisions" that we ignore, such as "No usual address"
# or "Migratory - Offshore"
ignoRE = re.compile("(No usual address.*)|(Migratory.*)|(Unclassified.*)")

# State Electoral Division to Mesh Block dict
sed_to_mb = {}

# Mesh Block to (cleaned) State Electoral Division
mb_to_sed = {}

# Convenience mapping of each state's electoral divisions.
perstate_ed = {}

# SA1 as BeautifulSoup
sakml = ""

# Mesh Blocks with coordinates
mb_coord = {}


def usage():
    """ Provides the usage statement for this utility """
    print(__doc__)
    print(usagestr)


#
def process_csv(csvfile):
    """
    Turn the CSV file into a SED:[mb] mapping we can use, and update
    the sed_to_mb mapping. We also strip out any "(...)", and strip
    off trailing whitespace.
    """
    for line in csvfile:
        # strip \n
        line.strip()
        mb, _, sed, _, juris, _ = line.strip().split(",")
        if len(sed) < 3:
            print(line.strip())
        # Skip the Other Territories
        if juris == "Other Territories" or ignoRE.match(sed):
            continue
        if juris not in perstate_ed:
            perstate_ed[juris] = {"localities": set()}
        cleaned = re.split(" \(", sed)[0]
        perstate_ed[juris]["localities"].add(cleaned)
        if cleaned in sed_to_mb:
            sed_to_mb[cleaned]["blocks"].append(mb)
        else:
            sed_to_mb[cleaned] = {
                "jurisdiction": alljuris[juris],
                "locality": cleaned,
                "blocks": [mb],
                "coords": []
            }
        mb_to_sed[mb] = cleaned


#
def mb_to_points(area):
    """
    Extract the polygon points from ogr:GeometryProperty for a given
    mesh block (ogr:SA1_MAIN16).
    Depends upon global variable sakml
    Returns a list.
    """
    llalt = area.findAll("gml:coordinates")
    coords = []
    for c in llalt:
        coords.extend(list(map(float, x.split(",")[0:2])) for x in
                      c.text.split(" ") if len(x) > 1)
    return coords


#
def prettytime():
    """ returns formatted time string """
    return datetime.date.strftime(datetime.datetime.now(),
                                  "%Y%m%d T %H%M%S")


if __name__ == "__main__":

    if len(sys.argv) < 3:
        usage()
        sys.exit(1)

    # Open the CSV file
    with open(sys.argv[1], "r") as csvinf:
        mbcsv = csvinf.readlines()
    process_csv(mbcsv[1:])
    print("[{nowish}] CSV processed".format(nowish=prettytime()))

    # Open the SA1 kml
    kmlf = open(sys.argv[2], "r")
    # Now we start the interesting bits
    sakml = BeautifulSoup(kmlf.read(), "xml")
    kmlf.close()

    print("[{nowish}] kmlf turned into soup".format(nowish=prettytime()))

    # Add the SA1s as attributes to each gml:featureMember, to ease
    # lookups.
    for feature in sakml.findAll("gml:featureMember"):
        sa1 = feature.find("ogr:SA1_MAIN16").text
        mb_coord[sa1] = mb_to_points(feature)
    print("[{nowish}] coordinates for mesh blocks associated".format(
        nowish=prettytime()))

    for block in mb_to_sed:
        electorate = mb_to_sed[block]
        # print("[{nowish}] Updating coords for {electorate}".format(
        #     electorate=electorate, nowish=prettytime()))
        sed_to_mb[electorate]["coords"].extend(mb_coord[block])

    # Time to write things out - on a per-jurisdiction basis
    for k in alljuris:
        if k == "Other Territories":
            continue
        runlist = list(perstate_ed[k]["localities"])
        runlist.sort()
        outj = {}
        for ename in runlist:
            outj[ename] = sed_to_mb[ename]
        fname = alljuris[k] + ".json"
        print("writing to {fname}".format(fname=fname))
        with open(fname, "w") as outf:
            json.dump(outj, outf)
    print("[{nowish}] all done".format(nowish=prettytime()))
