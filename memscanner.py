#!/usr/bin/env python3
import os
import sys
import struct
import time
import threading
from typing import List, Tuple

def parse_maps(pid: str) -> List[Tuple[int, int, str]]:
    """
    Parses /proc/<pid>/maps to extract readable memory regions.
    Returns a list of tuples: (start_address, end_address, permissions)
    """
    maps_file = f"/proc/{pid}/maps"
    regions = []
    try:
        with open(maps_file, "r") as f:
            for line in f:
                parts = line.strip().split(maxsplit=5)
                if len(parts) < 2:
                    continue
                addr_range, perms = parts[0], parts[1]
                if 'r' not in perms:
                    continue
                start_str, end_str = addr_range.split("-")
                start = int(start_str, 16)
                end = int(end_str, 16)
                regions.append((start, end, perms))
    except Exception as e:
        print(f"Error opening maps file: {e}")
        sys.exit(1)
    return regions

def initial_scan(pid: str, search_val: int, regions: List[Tuple[int, int, str]]) -> List[int]:
    """
    Scans memory regions in chunks for the given 32-bit integer.
    Returns a list of matching addresses.
    """
    mem_file = f"/proc/{pid}/mem"
    matches = []
    search_bytes = struct.pack("i", search_val)
    chunk_size = 4096  # Process memory in 4KB chunks

    try:
        with open(mem_file, "rb", 0) as mem:
            for start, end, perms in regions:
                offset_in_region = 0
                region_size = end - start
                while offset_in_region < region_size:
                    current_pos = start + offset_in_region
                    remaining = region_size - offset_in_region
                    read_size = min(chunk_size, remaining)
                    try:
                        mem.seek(current_pos)
                        chunk = mem.read(read_size)
                    except Exception:
                        break  # Skip to next region
                    if not chunk:
                        break

                    # Search within chunk
                    offset = 0
                    while True:
                        idx = chunk.find(search_bytes, offset)
                        if idx == -1:
                            break
                        absolute_addr = current_pos + idx
                        matches.append(absolute_addr)
                        offset = idx + 1  # Allow overlapping matches

                    offset_in_region += read_size
    except Exception as e:
        print(f"Error accessing process memory: {e}")
        sys.exit(1)
    return matches

def refine_scan(pid: str, candidates: List[int], new_val: int) -> List[int]:
    """
    Verifies candidate addresses against current memory state.
    Returns addresses that match the new value.
    """
    mem_file = f"/proc/{pid}/mem"
    refined = []
    new_bytes = struct.pack("i", new_val)

    try:
        with open(mem_file, "rb", 0) as mem:
            for addr in candidates:
                try:
                    mem.seek(addr)
                    data = mem.read(4)
                    if data == new_bytes:
                        refined.append(addr)
                except Exception:
                    continue
    except Exception as e:
        print(f"Memory access error during refinement: {e}")
        sys.exit(1)
    return refined

def modify_memory(pid: str, addresses: List[int], new_val: int) -> int:
    """
    Writes new value only to addresses in writable regions.
    Returns number of successful modifications.
    """
    mem_file = f"/proc/{pid}/mem"
    new_bytes = struct.pack("i", new_val)
    success_count = 0
    current_regions = parse_maps(pid)

    # Filter addresses in writable regions
    writable_addrs = []
    for addr in addresses:
        for start, end, perms in current_regions:
            if start <= addr < end and 'w' in perms:
                writable_addrs.append(addr)
                break
        else:
            print(f"Skipping read-only address: {hex(addr)}")

    if not writable_addrs:
        print("No writable addresses found")
        return 0

    try:
        with open(mem_file, "r+b", 0) as mem:
            for addr in writable_addrs:
                try:
                    mem.seek(addr)
                    mem.write(new_bytes)
                    success_count += 1
                except Exception as e:
                    print(f"Write failed at {hex(addr)}: {e}")
    except Exception as e:
        print(f"Memory access error: {e}")
        sys.exit(1)
    return success_count

def freeze_address(pid: str, addr: int, new_bytes: bytes, interval: float, stop_event: threading.Event):
    """Continuously writes to memory until stopped."""
    mem_file = f"/proc/{pid}/mem"
    while not stop_event.is_set():
        try:
            with open(mem_file, "r+b", 0) as mem:
                mem.seek(addr)
                mem.write(new_bytes)
        except Exception as e:
            print(f"Freeze error at {hex(addr)}: {e}")
        time.sleep(interval)

def freeze_memory(pid: str, addresses: List[int], new_val: int):
    """Manages freeze threads with proper cleanup."""
    new_bytes = struct.pack("i", new_val)
    stop_event = threading.Event()
    threads = []

    for addr in addresses:
        t = threading.Thread(
            target=freeze_address,
            args=(pid, addr, new_bytes, 0.1, stop_event),
            daemon=True
        )
        t.start()
        threads.append(t)

    print(f"Freezing {len(addresses)} addresses. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping freeze...")
        stop_event.set()
        for t in threads:
            t.join(timeout=1)
        print("Freezing stopped.")

def validate_integer(value: str) -> int:
    """Ensures input fits in 32-bit signed integer range."""
    try:
        val = int(value)
        if not (-2**31 <= val < 2**31):
            print(f"Warning: Value {val} exceeds 32-bit signed integer range")
        return val
    except ValueError:
        print("Invalid integer value")
        sys.exit(1)

def main():
    if len(sys.argv) != 3:
        print("Usage: ./memscanner.py <pid> <initial_value>")
        sys.exit(1)

    pid = sys.argv[1]
    if not os.path.exists(f"/proc/{pid}"):
        print(f"Process {pid} does not exist")
        sys.exit(1)

    # Initial setup
    initial_val = validate_integer(sys.argv[2])
    candidates = []
    regions = []

    def refresh_regions():
        """Helper to reload memory regions with existence check"""
        if not os.path.exists(f"/proc/{pid}"):
            print(f"Process {pid} no longer exists")
            sys.exit(1)
        return parse_maps(pid)

    def new_search():
        """Handle new search workflow"""
        nonlocal candidates, regions, initial_val
        try:
            new_val = validate_integer(input("New initial search value: "))
        except KeyboardInterrupt:
            print("\nCancelled new search")
            return
        
        print("\nStarting fresh search...")
        regions = refresh_regions()
        initial_val = new_val
        candidates = initial_scan(pid, initial_val, regions)
        print(f"Found {len(candidates)} new candidates")

    # Initial search
    regions = refresh_regions()
    candidates = initial_scan(pid, initial_val, regions)
    print(f"Initial scan found {len(candidates)} candidates")

    while True:
        print("\n======================")
        print(f"Current value focus: {initial_val}")
        print(f"Active candidates: {len(candidates)}")
        print("Options:")
        print("  [N]ew search")
        if candidates:
            print("  [R]efine scan  [M]odify  [F]reeze")
        print("  [Q]uit")
        
        choice = input("Choose action: ").strip().lower()

        if choice == 'n':
            new_search()
        elif choice == 'r' and candidates:
            new_val = validate_integer(input("New refinement value: "))
            candidates = refine_scan(pid, candidates, new_val)
            print(f"Remaining candidates: {len(candidates)}")
        elif choice == 'm' and candidates:
            new_val = validate_integer(input("New value to write: "))
            modified = modify_memory(pid, candidates, new_val)
            print(f"Successfully modified {modified} locations")
        elif choice == 'f' and candidates:
            new_val = validate_integer(input("Value to freeze: "))
            freeze_memory(pid, candidates, new_val)
        elif choice == 'q':
            print("Exiting")
            sys.exit(0)
        else:
            print("Invalid choice or no candidates for that action")

        # Auto-refresh regions after significant actions
        if choice in ['m', 'f'] and candidates:
            regions = refresh_regions()

if __name__ == "__main__":
    main()

