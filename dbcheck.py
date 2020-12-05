#!/usr/bin/python3
"""
parse and pretty print the current db json file
"""
import json
from pprint import pprint

def main():
    """Do the whole job"""
    db = json.load(open('db.json'))
    # limit the depth to 4 levels to avoid case details
    pprint(db, depth=4)

if __name__ == '__main__':
    main()
