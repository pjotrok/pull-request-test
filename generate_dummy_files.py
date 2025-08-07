#!/usr/bin/env python3
"""
Script to generate large dummy files for testing purposes.
Supports various size units (B, KB, MB, GB, TB) and different content types.
"""

import os
import sys
import argparse
import time
from pathlib import Path


def parse_size(size_str):
    """
    Parse size string like '1GB', '500MB', '2.5GB' into bytes.
    
    Args:
        size_str (str): Size string with unit (B, KB, MB, GB, TB)
    
    Returns:
        int: Size in bytes
    """
    size_str = size_str.upper().strip()
    
    # Define size multipliers
    units = {
        'KB': 1024,
        'MB': 1024**2,
        'GB': 1024**3,
        'TB': 1024**4
    }
    
    # Extract number and unit
    for unit in units:
        if size_str.endswith(unit):
            try:
                number = float(size_str[:-len(unit)])
                return int(number * units[unit])
            except ValueError:
                raise ValueError(f"Invalid size format: {size_str} {size_str[:-len(unit)]}")
    
    # If no unit specified, assume bytes
    try:
        return int(size_str)
    except ValueError:
        raise ValueError(f"Invalid size format: {size_str}")


def format_size(bytes_size):
    """Format bytes into human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"


def generate_dummy_file(filename, size_bytes, content_type='random', chunk_size=1024*1024):
    """
    Generate a dummy file with specified size and content type.
    
    Args:
        filename (str): Output filename
        size_bytes (int): Size in bytes
        content_type (str): Type of content ('random', 'zeros', 'pattern', 'text')
        chunk_size (int): Size of chunks to write at once (default 1MB)
    """
    print(f"Generating {format_size(size_bytes)} file: {filename}")
    print(f"Content type: {content_type}")
    
    start_time = time.time()
    
    try:
        with open(filename, 'wb') as f:
            remaining = size_bytes
            
            while remaining > 0:
                # Determine chunk size for this iteration
                current_chunk_size = min(chunk_size, remaining)
                
                # Generate content based on type
                if content_type == 'zeros':
                    chunk = b'\x00' * current_chunk_size
                elif content_type == 'pattern':
                    # Create a repeating pattern
                    pattern = b'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
                    chunk = (pattern * (current_chunk_size // len(pattern) + 1))[:current_chunk_size]
                elif content_type == 'text':
                    # Generate readable text
                    text_line = "This is a dummy file for testing purposes. Line number: {}\n"
                    lines_needed = current_chunk_size // 64  # Approximate line length
                    text_content = ""
                    for i in range(lines_needed):
                        text_content += text_line.format(i)
                    chunk = text_content.encode('utf-8')[:current_chunk_size]
                else:  # random
                    chunk = os.urandom(current_chunk_size)
                
                f.write(chunk)
                remaining -= current_chunk_size
                
                # Show progress for large files
                if size_bytes > 100 * 1024 * 1024:  # Show progress for files > 100MB
                    progress = ((size_bytes - remaining) / size_bytes) * 100
                    print(f"\rProgress: {progress:.1f}%", end='', flush=True)
        
        if size_bytes > 100 * 1024 * 1024:
            print()  # New line after progress
            
    except IOError as e:
        print(f"Error writing file: {e}")
        return False
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Verify file size
    actual_size = os.path.getsize(filename)
    print(f"File created successfully!")
    print(f"Expected size: {format_size(size_bytes)}")
    print(f"Actual size: {format_size(actual_size)}")
    print(f"Time taken: {duration:.2f} seconds")
    
    if duration > 0:
        speed = actual_size / duration / (1024 * 1024)  # MB/s
        print(f"Write speed: {speed:.2f} MB/s")
    
    return actual_size == size_bytes


def main():
    parser = argparse.ArgumentParser(
        description="Generate large dummy files for testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s dummy.bin 1GB                    # Generate 1GB file with random data
  %(prog)s test.dat 500MB --type zeros      # Generate 500MB file filled with zeros
  %(prog)s pattern.bin 2.5GB --type pattern # Generate 2.5GB file with pattern
  %(prog)s multiple 100MB 200MB 300MB      # Generate multiple files
        """
    )
    
    parser.add_argument('filename', help='Output filename')
    parser.add_argument('sizes', nargs='+', help='File size(s) (e.g., 1GB, 500MB, 2.5GB)')
    parser.add_argument('--type', choices=['random', 'zeros', 'pattern', 'text'], 
                       default='random', help='Content type (default: random)')
    parser.add_argument('--chunk-size', type=str, default='1MB',
                       help='Chunk size for writing (default: 1MB)')
    parser.add_argument('--force', action='store_true',
                       help='Overwrite existing files without confirmation')
    
    args = parser.parse_args()
    
    try:
        chunk_size = parse_size(args.chunk_size)
    except ValueError as e:
        print(f"Error parsing chunk size: {e}")
        return 1
    
    # Parse all sizes
    try:
        sizes_bytes = [parse_size(size) for size in args.sizes]
    except ValueError as e:
        print(f"Error parsing size: {e}")
        return 1
    
    # Generate files
    success_count = 0
    
    for i, size_bytes in enumerate(sizes_bytes):
        # Generate filename for multiple files
        if len(sizes_bytes) > 1:
            name, ext = os.path.splitext(args.filename)
            filename = f"{name}_{i+1}_{args.sizes[i]}{ext}"
        else:
            filename = args.filename
        
        # Check if file exists
        if os.path.exists(filename) and not args.force:
            response = input(f"File '{filename}' already exists. Overwrite? (y/N): ")
            if response.lower() not in ['y', 'yes']:
                print(f"Skipping {filename}")
                continue
        
        # Check available disk space
        try:
            free_space = os.statvfs(os.path.dirname(os.path.abspath(filename)) or '.').f_bavail * \
                        os.statvfs(os.path.dirname(os.path.abspath(filename)) or '.').f_frsize
            if size_bytes > free_space:
                print(f"Warning: Not enough free disk space!")
                print(f"Required: {format_size(size_bytes)}, Available: {format_size(free_space)}")
                response = input("Continue anyway? (y/N): ")
                if response.lower() not in ['y', 'yes']:
                    continue
        except (OSError, AttributeError):
            # Can't check disk space on this system
            pass
        
        print(f"\n{'='*50}")
        if generate_dummy_file(filename, size_bytes, args.type, chunk_size):
            success_count += 1
        else:
            print(f"Failed to generate {filename}")
    
    print(f"\n{'='*50}")
    print(f"Successfully generated {success_count} out of {len(sizes_bytes)} files")
    
    return 0 if success_count == len(sizes_bytes) else 1


if __name__ == '__main__':
    sys.exit(main())
