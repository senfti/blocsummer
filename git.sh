#!/bin/bash

cd /app/blocsummer
chown root:root /root/.ssh/config
git add -A
git commit -m "new data"
git push -u origin main
