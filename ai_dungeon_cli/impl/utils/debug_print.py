from pprint import pprint


# -------------------------------------------------------------------------
# STATE

DEBUG = False

def activate_debug():
    global DEBUG
    DEBUG = True


# -------------------------------------------------------------------------
# FNS

def debug_print(msg):
    if DEBUG:
        print(msg)

def debug_pprint(msg):
    if DEBUG:
        pprint(msg)
