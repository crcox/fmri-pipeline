This script normalizes the dataset shared by Becky Jackson @ York, UK and Chris
Cox's events.tsv files, derived from the Psychopy behavior output, into a BIDS
compliant dataset. The mapping of task conditions to runs is represented in
experiment_design.yaml at the root of the fmriprep analysis directory.

This script was written specifically for these data and their quirks. If doing something similar in the future, copy this directory and follow these design patterns. But do not try to make this code overly general.

Use recursive globbing to find files on the filesystem that certainly include
the ones you want, but do not try to glob perfectly. Follow up by applying a
regular expression to the file names to retain those that you want.

Once you find the files, parse their filenames to extract the design
information expressed by the BIDS conventions. Verify that what you are
extracting is what you expect. Enforce this through typing, dataclasses, etc.

Then you can build new filenames. This is where the information in
experiment_design.yaml is referenced.

Finally, once all that is done, you rename the files.

This sounds simple, all written out. But keeping these processes strictly
separate makes the code easier to read and reason about.
