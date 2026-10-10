-- F8: closes the Terminal window a job or the mail check ran in, once nothing runs in it any more.
-- Run by the window's own script (CLOSE_WINDOW in tick.py), detached from the window, with its tty.
-- Every window on that tty whose shell has ended is closed (it has no processes, so Terminal asks
-- nothing). That includes an old leftover window that had the same tty: Terminal reuses tty names,
-- and the L11 version closed whichever window came first, sometimes the old one, and stopped.
-- Gives up after five minutes. Errors in one round (a window closing under it) don't stop it.
-- Prints one line for the close log.
on run argv
	set t to item 1 of argv
	set closed to 0
	set seen to false
	repeat 600 times
		delay 0.5
		try
			tell application "Terminal"
				with timeout of 10 seconds
					set remaining to 0
					repeat with w in (every window)
						try
							if (tty of tab 1 of w) is t then
								set seen to true
								if (count of processes of tab 1 of w) is 0 then
									close w
									set closed to closed + 1
								else
									set remaining to remaining + 1
								end if
							end if
						end try
					end repeat
				end timeout
			end tell
			if seen and remaining is 0 then return t & " closed " & closed
		end try
	end repeat
	return t & " gave up after 5 min, closed " & closed
end run
