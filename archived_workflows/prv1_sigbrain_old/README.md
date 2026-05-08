# Archived PRV1 / SIG Brain workflows

These workflows were archived because the stable runtime path is now:

PRV1 AUTO REFRESH1 Master
-> PRV1 LIVE FEED1 Twelve Data Timestamp Feed
-> PRV1 JOURNAL FIX1 From Current Payload
-> PRV1 PAGES RESTORE1 Restore Working SIG Brain Pages

Archived workflows should not run on schedule because they may overwrite
the current payload, journal, or Pages artifact.

Boundary:
DISPLAY ONLY / NOT SIGNAL / NO BROKER / NO EXECUTION / NO SHADOW ACTIVATION
