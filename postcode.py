#!/usr/bin/env python3.7

__doc__ = """
Takes a postcode argument, queries the appropriate AEC webpage
and returns the list of possible electorates as (1) line by line
mapping and (2) JSON formatted.

Performs basic validation on the input postcode based on the free
Australia Postcode dataset downloaded from
https://www.aggdata.com/system/files_force/samples/au_postal_codes.csv?download=1
"""

import csv
import json
import os
import re
import sys

import requests

from bs4 import BeautifulSoup


allPostCodes = set()
fields = ["State", "Locality", "Postcode", "Electorate",
          "RedistributedElectorate", "OtherLocality"]

# For result pages > 1 we need to pass a dict of ASP.net args
payload = {}
followups = set()
eventTgt = "ctl00$ContentPlaceHolderBody$gridViewLocalities"
tblAttr = "ContentPlaceHolderBody_gridViewLocalities"

linkRE = re.compile(
    ".*__doPostBack.'(.*?gridViewLocalities)','(Page.[0-9]+)'.*")


def isDoPostBack(href):
    """Callback to identify the __doPostBack links of interest"""
    try:
        res = linkRE.match(str(href))
        arg = res.group(2)
    except Exception as _err:
        arg = None
    return arg


def findFollowups(soup):
    """
    Finds results pages for multi-page responses. Update global variable
    payload with the common args, returns a list of followup pages for
    the caller to handle.
    """
    inputs = soup.find_all("input")
    # if we've got __VIEWSTATE then this is the input we need
    for inp in inputs:
        if "name" in inp.attrs:
            arg = re.match("(^__.*)", inp.attrs["name"])
            if not arg:
                continue
            payload[arg.group(1)] = inp.attrs["value"]
            for href in inp.find_all("a"):
                arg = isDoPostBack(href)
                if arg:
                    followups.add(arg)
        else:
            continue
    payload["__EVENTTARGET"] = eventTgt


def queryAEC(postcode, extrapage):
    """
    Queries the AEC url and returns soup. If extrapage is empty
    then we pass the soup to findFollowups before returning.
    """
    url = "https://electorate.aec.gov.au/LocalitySearchResults.aspx?"
    url += "filter={0}&filterby=Postcode"

    if not extrapage:
        res = requests.post(url.format(postcode))
    else:
        payload["__EVENTARGUMENT"] = extrapage
        res = requests.post(url.format(postcode), data=payload)

    resh = BeautifulSoup(res.text, "html.parser")
    if not extrapage:
        findFollowups(resh)

    restbl = resh.find_all(name="table",
                           attrs={"id": tblAttr})

    rows = restbl[0].find_all("tr")
    results = []
    #
    # We skip the header row
    for entry in rows[1:]:
        if "class" in entry.attrs and entry.attrs["class"][0].startswith(
                "pagingLink"):
            # we've hit the end of the data elements
            break
        resdict = {}
        for i, tdata in enumerate(entry.find_all("td")):
            if tdata.string is None:
                break
            resdict[fields[i]] = tdata.string
        if resdict:
            results.append(resdict)
    return results


def output(results, fmt):
    """ prints the results to stdout, using fmt """
    if fmt == "raw":
        layout = "{0:8} {1:10} {2:32} {3}"
        print(layout.format("State", "Postcode", "Locality", "Electorate"))
        for resd in results:
            print(layout.format(resd["State"], resd["Postcode"],
                                resd["Locality"], resd["Electorate"]))
        print("\n")
    elif fmt == "json":
        print(json.dumps(results))
        print("\n")
    else:
        print("invalid format")
        sys.exit(1)


def setupPostCodes():
    """Reads in the postcode file, updates allPostCodes"""
    homedir = os.getenv("HOME")
    pcf = open(os.path.join(homedir,
                            "OneDrive/scraping/au_postal_codes.csv"), "r")
    csvr = csv.reader(pcf)
    for row in csvr:
        allPostCodes.add(row[0])


def main():
    """Does setup tasks then queries the AEC website"""
    postcode = sys.argv[1]
    setupPostCodes()
    if postcode not in allPostCodes:
        print("Error: {0} is not a valid post code".format(postcode),
              file=sys.stderr)
        sys.exit(1)
    results = queryAEC(postcode, None)
    if followups:
        for nth in followups:
            results.extend(queryAEC(postcode, nth))
    output(results, "raw")
    output(results, "json")


if __name__ == "__main__":
    main()
