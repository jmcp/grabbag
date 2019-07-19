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
import getopt
import json
import sys

from pymongo import MongoClient

from bs4 import BeautifulSoup


__doc__ = """
This script extracts electorate names and polygon points from the
various state/territory Electoral Commission KML data (whether that's
supplied as native KML, or I've run it through with ogr2ogr), then
writes that data to a MongoDB instance **stored locally** as well as
dumping it to a file in JSON format. The output filename is based
on the date and time when the script is run.

TODO: support checking against for previous database files.
-- mitigation: MongoDB's "find_one_and_update"

Each time there is a redistribution of electorates, this script
must be re-run.

TODO: add functionality to check whether a particular electorate
has been redistributed, and notify the user while updating the
database entry for the affected areas.

TODO: add support for checking local government areas.
"""

usagestr = """

electorates.py -f filename [-p prefix] -t state-or-territory
electorates.py -h

    filename is the KML file to read the electorate boundaries from.

    state-or-territory is the name of an Australian state or territory
    with 'federal' to cover the whole country. Local government area
    boundaries are not supported.

    prefix is optional, and if supplied is for the output filename.

"""

# Each electorate is 'Name' : points. We also stash the date and
# time the script is run, and the full filename
electorates = {}

territories = set(["federal", "act", "nt"])
states = set(["nsw", "qld", "sa", "tas", "vic", "wa"])

kmlf = ""
outf = ""
ddnow = datetime.datetime.now()
outprefix = ddnow.strftime("%Y%m%d-%H%M")
ddupdate = ddnow.strftime("%Y%m%d")


def usage():
    """ Provides the usage statement for this utility """
    print(__doc__)
    print(usagestr)


def getName(where):
    """
    Callout function to find the name field, given that we've got several
    different schema forms to check.
    """
    useName = where.find("name")
    if useName:
        return useName.string

    useAttrName = where.find("SimpleData", attrs={"name":"ELECTORATE"})
    if useAttrName:
        return useAttrName.string

    useAttrNAME = where.find("SimpleData", attrs={"name": "DISTRICT_NAME"})
    if useAttrNAME:
        return useAttrNAME.string

    useDiv = where.find("ogr:Elect_div")
    if useDiv:
        return useDiv.string

    useOgrName = where.find("ogr:Name")
    if useOgrName:
        return useOgrName.string

    useOgrNAME = where.find("ogr:NAME")
    if useOgrNAME:
        return useOgrNAME.string

    useOgrname = where.find("ogr:name")
    if useOgrname:
        return useOgrname.string
    
    return "Unable to find a supported Tag, please check the schema."


if __name__ == "__main__":
    opts, args = getopt.getopt(sys.argv[1:], "f:hp:t:")
    dopts = dict(opts)

    if "-h" in dopts or len(dopts) < 1:
        usage()
        sys.exit(0)

    if "-t" not in dopts:
        print("A State ({0}) or Territory ({1}) must be specified".format(
            territories, states))
        sys.exit(1)
    else:
        terr = dopts["-t"]
        if terr not in territories and terr not in states:
            print("Invalid territory specified. Please use a value "
                  "from {0} or {1}".format(territories, states))
            sys.exit(3)

    if "-f" not in dopts:
        print("KML file to parse must be specified")
        sys.exit(1)
    else:
        try:
            kmlf = open(dopts["-f"], "r")
        except OSError as _err:
            print("Unable to open {0} for reading: {1}".format(
                dopts["-f"], _err.strerror))
            sys.exit(_err.errno)

    outprefix += "-" + terr
    if "-p" not in dopts:
        outf = outprefix + ".json"
    else:
        outf = opts["-p"] + "-" + outprefix + ".json"

    # Now we start the interesting bits
    ksoup = BeautifulSoup(kmlf.read(), "xml")

    # Is this KML (and if so, which sort?), or is it an ogr2ogr-converted
    # mapinfo thing?
    if ksoup.find("kml"):
        placemark = "Placemark"
        coordname = "coordinates"
    else:
        placemark = "gml:featureMember"
        coordname = "gml:coordinates"

    # Now that we've got element names figured out, it's time to
    # extract some data and then add it to a MongoDB instance
    client = MongoClient("mongodb://localhost/Electorates")
    dbc = client.Electoratesdb.coll

    for place in ksoup.findAll(placemark):
        ename = getName(place).title()
        if terr == "federal":
            tstate = place.find("ogr:State").string
        else:
            tstate = terr.upper()
        #
        # Ensure that we strip off the altitude and any erroneous
        # leading null elements before we add the record
        llalt = place.findAll(coordname)[0].string.split(" ")
        #
        # This mouthful ensures that we stores the floating point
        # values for lat/long, rather than string forms. Trust me,
        # it will make consumers of this db much happier.
        coords = [list(map(float, x.split(",")[0:2])) for x in
                  llalt if len(x) > 1]
        #
        # This is effectively a cast to void, because we're not
        # *really* interested in any returned document. At this point,
        # at any rate.
        dbc.find_one_and_update(
            {"locality": ename, "jurisdiction": tstate},
            {'$set': {"coords": coords}},
            upsert=True)
        electorates[ename] = {
            "locality": ename,
            "jurisdiction": tstate,
            "coords": coords
        }

    with open(outf, "w") as outfile:
        outfile.write(json.dumps(electorates))
        outfile.close()
