#!/usr/bin/env python3
import os
import requests
from bs4 import BeautifulSoup
import re
import concurrent.futures
import argparse
from urllib.parse import urljoin
import gzip
import shutil

def get_directory_listing(url):
    """Get directory listing from an FTP URL using HTTP"""
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all links
        links = []
        for link in soup.find_all('a'):
            href = link.get('href')
            if href and not href.startswith('?') and not href.startswith('/'):
                links.append(href)
        
        return links
    except Exception as e:
        print(f"Error fetching directory listing from {url}: {e}")
        return []

def download_file(url, output_dir, preserve_structure=False):
    """Download a file from URL to the output directory"""
    try:
        local_filename = os.path.basename(url)
        
        if preserve_structure:
            # Extract directory structure from URL
            path_parts = url.split('Archaea/')[1].split('/')
            if len(path_parts) > 1:
                # Remove the filename from path parts
                subdirs = '/'.join(path_parts[:-1])
                target_dir = os.path.join(output_dir, subdirs)
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir)
                output_path = os.path.join(target_dir, local_filename)
            else:
                output_path = os.path.join(output_dir, local_filename)
        else:
            output_path = os.path.join(output_dir, local_filename)
        
        # Skip if file already exists
        if os.path.exists(output_path):
            print(f"File {output_path} already exists, skipping")
            return True
            
        print(f"Downloading {url} to {output_path}")
        
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(output_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        
        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False

def process_directory(base_url, directory, output_dir, pattern, preserve_structure):
    """Process a directory and download files matching the pattern"""
    dir_url = urljoin(base_url, directory)
    files = get_directory_listing(dir_url)
    
    for file in files:
        file_url = urljoin(dir_url, file)
        
        # If it's a directory (ends with /), recursively process it
        if file.endswith('/'):
            process_directory(base_url, urljoin(directory, file), output_dir, pattern, preserve_structure)
        # If it's a file matching our pattern, download it
        elif re.search(pattern, file):
            download_file(file_url, output_dir, preserve_structure)

def main():
    parser = argparse.ArgumentParser(description='Download FASTA files from UniProt FTP server')
    parser.add_argument('--output-dir', '-o', default='./uniprot_archaea', help='Output directory')
    parser.add_argument('--pattern', '-p', default=r'\.fasta\.gz$', help='Regex pattern for files to download')
    parser.add_argument('--preserve-structure', '-s', action='store_true', help='Preserve directory structure')
    parser.add_argument('--extract', '-e', action='store_true', help='Extract downloaded gzip files')
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    
    # Base URL for archaeal reference proteomes
    base_url = "https://ftp.uniprot.org/pub/databases/uniprot/knowledgebase/reference_proteomes/Archaea/"
    
    # Get the list of directories
    directories = get_directory_listing(base_url)
    
    # Process each directory
    for directory in directories:
        if directory.endswith('/'):  # It's a directory
            process_directory(base_url, directory, args.output_dir, args.pattern, args.preserve_structure)
    
    # Extract gzip files if requested
    if args.extract:
        print("Extracting gzip files...")
        for root, _, files in os.walk(args.output_dir):
            for file in files:
                if file.endswith('.gz'):
                    gz_path = os.path.join(root, file)
                    output_path = gz_path[:-3]  # Remove .gz extension
                    with gzip.open(gz_path, 'rb') as f_in:
                        with open(output_path, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    print(f"Extracted {gz_path} to {output_path}")

if __name__ == "__main__":
    main()

