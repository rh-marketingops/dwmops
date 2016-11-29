#!/bin/bash
case $(( $(date +%M) % 30 )) in
0) echo "0 ran" ;; # Run GET job
[1-28]*) echo "1-28 ran" ;; # Run minutely jobs
29) echo "29 ran" ;; # Run POST job
esac
