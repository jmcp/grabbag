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

__doc__ = """

A simple (quick-n-dirty) script to compare the JSON contents of
two files.

Since this script is a checker of the output from SA1-to-mbpt.py,
we know that there are only four parts to check:

-- keyname
-- "jurisdiction"
-- "locality"
-- "coords"

"""


if __name__ == "__main__":

    if len(sys.argv) < 3:
        print("Two arguments are required")
        sys.exit(1)

    leftf = open(sys.argv[1], "r")
    rightf = open(sys.argv[2], "r")

    ljson = json.load(leftf)
    rjson = json.load(rightf)

    lkset = set(ljson.keys())
    rkset = set(rjson.keys())
    diffset = lkset - rkset

    print("checking keys: left {left} vs right {right}".format(
        left=len(lkset), right=len(rkset)))
    print("difference: {diffset}".format(diffset=diffset))

    print("checking each electorate's details")

    for electorate in ljson.keys():
        if electorate not in rjson:
            print("Electorate {electorate} is not in {right}, "
                  "skipping".format(electorate=electorate,
                                    right=sys.argv[2]))
            continue

        # set up some ease-of-access variables
        lefte = ljson[electorate]
        righte = rjson[electorate]
        #
        # If the jurisdictions don't match then our inputs are
        # just plain wrong
        ljur = lefte["jurisdiction"]
        rjur = righte["jurisdiction"]
        if ljur != rjur:
            print("Jurisdictions do NOT match ({left} vs {right}) for "
                  "electorate {electorate}".format(
                      left=ljur, right=rjur, electorate=electorate))

        lloc = lefte["locality"]
        rloc = righte["locality"]
        if lloc != rloc:
            print("Localities do NOT match ({left} vs {right})".format(
                left=lloc, right=rloc))

        # Have we missed any coordinate points?
        lcset = set(lefte["coords"][0])
        rcset = set(righte["coords"][0])
        diffset = lcset - rcset
        print("Electorate of {electorate} has coordinate differences: "
              "{diffset} ".format(diffset=diffset, electorate=electorate))
