#!/usr/bin/python3

import sys

sys.path.append("py")

import exportedtables

tests = [
        {},
        {
            "Billy No-Mates" : "BNM"
        },
        {
            "Fred Bloggs" : "FB",
            "Joe Bloggs" : "JBl",
            "James Bond" : "JaB",
            "Jonathan Barmaduke Obstruction" : "JBO",
            "Tweedledum McBouncemarket" : "TMcBou1",
            "Tweedledum McBouncemarkev" : "TMcBou2"
        },
        {
            "Andy" : "Andy",
            "Andrew" : "Andr",
            "Anthea Ndaaargh" : "ANda",
            "Anthea Ndonkulous" : "ANdo",
            "Alex Northampton" : "ANo",
            "Alex Ndestination" : "ANde",
            "Alex Ndytherington" : "ANdyt" # ANdy not allowed
        },
        {
            "MacGyver" : "MG",
            "Sleve McDichael" : "SM",
            "I Have An Incredibly Long Name But My Abbreviation Can Only Have Six Characters" : "IHAILN",
            "I Also Have An Incredibly Long Name" : "IAHAIL1",
            "I also have an incredibly long name and although the case is different you still have to use a number to disambiguate" : "Iahail2",
            "Sleve McDichael Smith" : "SMS",
            "Bob" : "B",
            "Barry Oscar Burblington" : "BOBu", # Can't use BOB because of Bob
        },
        {
            "Johnny Double-Barrelled" : "JDB",
            "Punctuation O'Postrophe" : "POP",
            "Ship's Cat" : "SsC",
            "Flaputronic O'Format" : "FOFo",
            "Flaptrickster O'Fruitcake" : "FOFr"
        },
        {
            "Tom Fotherington" : "ToFot", # ToFo could be Tom Footplate
            "Tim Fotherington" : "TiF", # TF could be anyone
            "Tom Footplate" : "TFoo", # ToFo or TFo could be Tom Fotherington
            "Tommy Flatplate" : "TFl",
            "Tom Fimblington" : "TFi",
            "Tom Frobnicate" : "TomFr", # No amount of extra letters will fully disambiguate from Tombola Frobnicate
            "Tombola Frobnicate" : "TombF",
        },
        {
            "Tombolablatherington Frobnicate" : "TFrobn1",
            "Tombolablitherington Frobnicate" : "TFrobn2",
            "Tombolablotherington Frobnicate" : "TFrobn3",
            "Tombolablotherington Frobnicationary" : "TFrobn4",
            "Tombola Frog" : "TFrog",
            "Tombola Frogg" : "TFrogg",
        },
        {
            "P1" : "P1",
            "P2" : "P2",
            "P3" : "P3",
            "P4" : "P4"
        },
        {
            "Whimsical Simon" : "WhS",
            "William Oscar Skeleton" : "WOS",
            "Wobbly Simon" : "WoSi", # WSi might be Whimsical Simon, WOS is William Oscar Skeleton
            "Wooden Structure" : "WoodS",
            "Woollen Structure" : "WoolS"
        }
]

def main():
    test_num = 1
    for (test_idx, test) in enumerate(tests):
        test_num = test_idx + 1
        names = list(test)
        names_to_abbrs_observed = exportedtables.abbreviate_names(names)
        names_to_abbrs_expected = test
        fail = False
        for n in names_to_abbrs_expected:
            abbr_observed = names_to_abbrs_observed.get(n)
            abbr_expected = names_to_abbrs_expected[n]
            if abbr_observed != abbr_expected:
                print("abbreviationtest: test %d failure." % (test_num), file=sys.stderr)
                print("Expected mapping: " + str(test), file=sys.stderr)
                print("Expected abbreviation for \"%s\": \"%s\"" % (n, abbr_expected), file=sys.stderr)
                print("Observed abbreviation for \"%s\": \"%s\"" % (n, abbr_observed), file=sys.stderr)
                print("", file=sys.stderr)
                fail = True
    if fail:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
