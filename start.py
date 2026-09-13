"""Portable launcher, with a readable error instead of a disappearing window."""
import sys

def main():
    if sys.version_info < (3,10):
        print('FleetMesh requires Python 3.10 or newer. Install Python, then run this launcher again.')
        return 1
    from server import main as launch
    try:
        launch()
        return 0
    except Exception as error:
        print('\nFleetMesh could not start: '+str(error),file=sys.stderr)
        return 1
if __name__=='__main__':
    raise SystemExit(main())
