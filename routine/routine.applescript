-- Jarvis Routine (phase L, and the start at login of H2). A small helper app with no window and no
-- Dock icon. macOS only lets a background program read the Documents folder when it is an app that
-- the user has allowed once ("Jarvis Routine would like to access files in your Documents folder").
-- At launch: starts the call line (start.sh does nothing if it already runs).
-- Every minute: one look at the queue (tick.py). No Claude, so waiting costs no usage.
-- The path below is written for /Users/you/HQ; build-app.sh and the installer put this HQ's path in.
property jv : "/Users/you/HQ/"

on run
	try
		do shell script "mkdir -p " & quoted form of (jv & "scratch/routine") & "; /bin/zsh " & quoted form of (jv & "app/start.sh") & " >> " & quoted form of (jv & "scratch/launchagent.log") & " 2>&1"
	end try
end run

on idle
	try
		do shell script "/usr/bin/python3 " & quoted form of (jv & "routine/tick.py") & " >> " & quoted form of (jv & "scratch/routine/routine.log") & " 2>&1"
	end try
	return 60
end idle
