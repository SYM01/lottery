#!/usr/bin/env python3

from gitfs import app

if __name__ == '__main__':
    app.run(threaded=True, debug=True)
    