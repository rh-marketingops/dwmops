#!/bin/bash
case $(( $(date +%M) % 30 )) in
0)  ;; # Run GET job
[1-28])  ;; # Run minutely jobs
29)  ;; # Run POST job
esac
