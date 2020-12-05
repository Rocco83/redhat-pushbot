#!/usr/bin/python3
"""
parse and pretty print the xml file
"""
from pprint import pprint
import xmltodict

def main():
    """Do the whole job"""
    with open('testcase.xml') as xmlfd:
        parseddict = xmltodict.parse(xmlfd.read())
        pprint(parseddict)

if __name__ == '__main__':
    main()
