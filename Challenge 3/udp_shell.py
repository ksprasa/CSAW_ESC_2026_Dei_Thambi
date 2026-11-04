#!/usr/bin/env python3
"""
esc3_shell.py -- interactive UDP console for the Airwave Template gateway.

The oracle "door" hops across 4210-4219 and only one port answers at a time,
so instead of guessing the live port we just fire every line at all 10 ports
on one socket and print whatever actually answers (with the source port).
No door-tracking games, no 'error'-vs-reply classifying -- you see the raw reply.

Accepted template vars (from the firmware): device_id, uptime, clients, true, false
  e.g.   {{6*7}}            -> 42
         {{uptime}}         -> <number>
         {{device_id}}      -> 843A14
         {{clients}}        -> 1

Run (connected to the SmartHomeGW SoftAP):
    python3 udp_shell.py
    python3 udp_shell.py --host 192.168.4.1 --ports 4210-4219

In the prompt:
    <anything>     send it to the live door, print the reply
    :lock          re-probe and show which port is currently live
    :raw <hex>     send raw bytes (hex), e.g.  :raw 7b7b367d7d
    :q / Ctrl-D    quit
"""
import socket, sys, select, argparse, time

def parse_ports(s):
    if "-" in s:
        lo, hi = s.split("-"); return list(range(int(lo), int(hi) + 1))
    return [int(s)]

class Door:
    def __init__(self, host, ports, timeout=0.8):
        self.host, self.ports, self.timeout = host, ports, timeout
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.setblocking(False)
        self.last_port = None

    def _collect(self, window):
        """Drain replies for `window` seconds -> list of (src_port, text)."""
        out, t0 = [], time.time()
        while time.time() - t0 < window:
            r, _, _ = select.select([self.sock], [], [], window)
            if not r:
                break
            try:
                data, src = self.sock.recvfrom(4096)
            except BlockingIOError:
                continue
            except OSError:
                break
            out.append((src[1], data))
        return out

    def send(self, raw: bytes):
        """Fire to every port, return list of (src_port, reply_text)."""
        # flush anything stale (unsolicited broadcasts) first
        self._collect(0.05)
        for p in self.ports:
            try:
                self.sock.sendto(raw, (self.host, p))
            except OSError:
                pass
        replies = self._collect(self.timeout)
        # the gateway replies FROM an ephemeral src port, not the dest door port,
        # so we can't read the door from src -- but we only care about the text.
        seen, uniq = set(), []
        for sp, data in replies:
            if data in seen:
                continue
            seen.add(data)
            uniq.append((sp, data.decode("utf-8", "replace").rstrip()))
        return uniq

    def lock(self):
        """Probe with a known-answer expr to confirm the gateway is reachable."""
        reps = self.send(b"{{6*7}}")
        return reps

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="192.168.4.1")
    ap.add_argument("--ports", default="4210-4219")
    ap.add_argument("--timeout", type=float, default=0.8)
    a = ap.parse_args()
    door = Door(a.host, parse_ports(a.ports), a.timeout)

    print(f"[*] target {a.host} ports {a.ports}")
    reps = door.lock()
    if reps:
        print(f"[+] gateway alive -- {{6*7}} => {reps[0][1]}")
    else:
        print("[!] no reply to {{6*7}} -- check you're on the SoftAP (gateway-secure-2026).")
    print("[*] type a payload and hit enter. :q to quit, :raw <hex> for raw bytes.\n")

    while True:
        try:
            line = input("udp> ")
        except (EOFError, KeyboardInterrupt):
            print(); break
        if not line.strip():
            continue
        if line.strip() in (":q", ":quit", ":exit"):
            break
        if line.strip() == ":lock":
            reps = door.lock()
            print("   alive" if reps else "   (no answer)")
            for sp, t in reps:
                print(f"   <- {t}")
            continue
        if line.startswith(":raw "):
            try:
                raw = bytes.fromhex(line[5:].strip().replace(" ", ""))
            except ValueError:
                print("   bad hex"); continue
        else:
            raw = line.encode()

        reps = door.send(raw)
        if not reps:
            print("   (no reply -- door may be mid-hop, hit enter again)")
        else:
            for sp, t in reps:
                print(f"   <- {t}")

if __name__ == "__main__":
    main()
