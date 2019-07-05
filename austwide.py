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

import json
import sys

from bs4 import BeautifulSoup


__doc__ = """
This script extracts state and territory names and polygon points
from the Australian Bureau of Statistics shapefile

State and Territory ASGC Ed 2011 Digital Boundaries in MapInfo
  Interchange Format 
https://www.abs.gov.au/ausstats/subscriber.nsf/log?openagent&1259030001_ste11aaust_midmif.zip&1259.0.30.001&Data%20Cubes&6E45E3029A27FFEFCA2578CC0012083E&0&July%202011&14.07.2011&Latest


then writes that data to local (same directory) JSON files.
"""

usagestr = """

austwide.py filename

    filename is the KML file to read the state/territory boundaries from.

"""

areas = {
    "New South Wales": "nsw",
    "Victoria": "vic",
    "Australian Capital Territory": "act",
    "Queensland": "qld",
    "South Australia" : "sa",
    "Western Australia": "wa",
    "Tasmania": "tas",
    "Northern Territory": "nt",
    "Other Territories": "other"
}


# Yes, this script has a lot in common with electorates.py, but it's
# somewhat more special case - and I'm not really worried about much
# in the way of error handling. Quick-n-dirty.

kmlf = open(sys.argv[1], "r")

ksoup = BeautifulSoup(kmlf.read(), "xml")
# Basic check #1
ogrFC = ksoup.find("ogr:FeatureCollection")
if not ogrFC.attrs:
    print("{0} does not appear to be a valid GML file "
          "(no attrs found)\n".format(kmlf.name))
    sys.exit(1)

print("\n")
print("{0:^30} {1:^18}".format("State/Territory", "Number of points"))
print("{0:^30} {1:^18}".format("-"*30, "-"*18))

for place in ksoup.findAll("gml:featureMember"):
    terrname = place.find("ogr:STATE_NAME_2011").string
    #
    # Ensure that we strip off the altitude and any erroneous
    # leading null elements before we add the record
    llalt = []
    for coo in place.findAll("gml:coordinates"):
        llalt.extend(coo.string.split(" "))
    # This mouthful ensures that we stores the floating point
    # values for lat/long, rather than string forms. This makes
    # consumers of this output much happier.
    coords = [list(map(float, x.split(",")[0:2])) for x in
              llalt if len(x) > 1]
    print("{0:30} {1:18}".format(terrname, len(coords)))

    outfn = areas[terrname] + ".json"

    outf = open(outfn, "w")
    terrdict = {
        "jurisdiction": terrname,
        "abbrjuris": areas[terrname],
        "coords": coords
        }
    json.dump(terrdict, outf)
    outf.close()

print("\n")

kmlf.close()
