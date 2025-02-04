# MemScanner

**MemScanner** is a Python-based memory scanning tool for Linux systems. It allows you to search a running process's memory for a specific 32-bit integer value, refine the search results, modify the found values, and even "freeze" them by continuously writing a new value. This tool leverages the Linux `/proc` filesystem to inspect and manipulate process memory.

> **Disclaimer:**  
> **Use responsibly and only on processes you own or have explicit permission to modify. Unauthorized memory manipulation may violate laws or system policies.**

## Features

- **Initial Scan:**  
  Search all readable memory regions of a process for a given 32-bit integer value.

- **Refinement:**  
  Refine the candidate addresses by providing a new expected value to narrow down the list.

- **Modification:**  
  Write a new value to the candidate addresses (only if the memory region is writable).

- **Freeze:**  
  Continuously write a value to selected addresses to "freeze" them at a particular value.

- **New Search:**  
  Start a fresh search with a different initial value without restarting the tool.

## How It Works

1. **Parsing Memory Regions:**  
   The program reads the `/proc/<pid>/maps` file to identify all readable memory regions in the target process.

2. **Scanning Memory:**  
   It then scans these regions by reading memory in chunks (defaulting to 4KB) and searching for the specified 32-bit integer value.

3. **Refining Candidates:**  
   You can refine the list of candidate addresses by providing a new integer value, which filters out addresses that do not match the new value.

4. **Modifying Memory:**  
   The tool attempts to write a new value to each candidate address, verifying that the address is part of a writable region.

5. **Freezing Values:**  
   For addresses you wish to "freeze," the program spawns threads that continuously write a specified value to these addresses until you stop the process.

## Prerequisites

- Linux-based operating system
- Python 3 installed
- Sufficient privileges to read and write to the target process memory (typically requires root or the appropriate permissions)

## Installation

Clone this repository:

```bash
git clone https://github.com/valinux/MemScanner.git
cd MemScanner
```

Make the script executable (if not already):

```bash
chmod +x memscanner.py
```

## Usage

Run the tool by providing the process ID (PID) of the target process and an initial search value (32-bit integer):

```bash
sudo python memscanner.py <pid> <initial_value>
```

Example:

```bash
sudo python memscanner.py 1234 42
```

Once running, you'll see an interactive menu with the following options:

- **[N]ew search:**  
  Start a fresh memory search with a new initial value.

- **[R]efine scan:**  
  Provide a new integer value to refine the current list of candidate addresses.

- **[M]odify:**  
  Write a new integer value to all candidate addresses (only in writable memory regions).

- **[F]reeze:**  
  Continuously write a specified value to the candidate addresses (press `Ctrl+C` to stop freezing).

- **[Q]uit:**  
  Exit the program.

### Example Workflow

1. **Initial Search:**  
   Start the tool with the desired PID and initial value. The program will display the number of candidate addresses found.

2. **Refinement:**  
   If needed, choose the `R` option and enter a new value to refine the search results.

3. **Modification:**  
   Use the `M` option to change the values at the candidate addresses.

4. **Freezing:**  
   Use the `F` option to continuously enforce a new value on these addresses until you decide to stop the operation.

5. **New Search:**  
   If you want to start over, choose the `N` option and input a new initial search value.

## Important Considerations

- **Permissions:**  
  Accessing and modifying process memory typically requires elevated permissions. Run the script as root if necessary.

- **Safety:**  
  Modifying process memory can cause instability or crashes. Always ensure you understand the implications of the changes you're making.

- **Compatibility:**  
  This tool is designed for Linux systems utilizing the `/proc` filesystem.

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests if you have suggestions or improvements.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
