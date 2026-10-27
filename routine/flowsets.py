"""Which happy flows hold on which computer (one place, H169): the installer's test round and the nightly run read it.

H56.5: the quick happy flows (no Claude turns) that hold on a Linux server; the rest are written for the Mac (the
helper app, pmset, the Mac's own tools) and get their Linux side one by one. A new flow that holds on Linux goes in
here. Standard library only: the installer imports it before anything is installed.
"""

LINUX_FLOWS = "8,15,16,20,23,26,34,41,42,44,45,51,54,56,60,61,63,65,66,67,70,71,72,73,79,84,85,86,87,88,89,91,92,93,95,101,105,106,107,108,109,111,112,113,114,115,116,117,118,119,120,122,124,125,126,127,128,130,131,132,133,134,135,136,137,138,139,140,141,142,143,144,145,146,147,148,149,150,151,152,153,154,155,156,157,158,159,160,161,162,163,164,165,166,167,168"

# H169 (16 October 2026): the nightly run on a Linux server. Every quick flow that passed on the VPS that day
# (62 of 86, and 103); the others need the Mac (the helper app, pmset, clang, a headless browser, the Mac's own settings),
# so the Mac's nightly covers them. A flow that starts holding on Linux goes in here too.
# H162 (18 October 2026): the browser flows find the server's headless browser and run it without the sandbox,
# so 27, 28, 35, 36, 50, 52, 55, 57 and 68 hold here now; 59 too (it reads Linux's crash record).
# 24 October 2026 (nightly): 141 and 142 were added on 23 October without a line here, so the night skipped them; in now.
LINUX_NIGHTLY = "1,8,9,10,15,16,20,21,23,26,27,28,29,34,35,36,40,41,42,44,45,46,48,50,51,52,53,54,55,56,57,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106,107,108,109,111,112,113,114,115,116,117,118,119,120,122,123,124,125,126,127,128,130,131,132,133,134,135,136,137,138,139,140,141,142,143,144,145,146,147,148,149,150,151,152,153,154,155,156,157,158,159,160,161,162,163,164,165,166,167,168"
