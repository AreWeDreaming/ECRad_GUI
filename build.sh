#!/bin/bash
python3 -m build -n -x
python3 -m pip install --no-deps .
git rev-parse HEAD > id
# make USE_3D=True DEBUG=True
# make USE_3D=True
# make USE_3D=True DEBUG=True OPEN_MP=True
# make USE_3D=True OPEN_MP=True