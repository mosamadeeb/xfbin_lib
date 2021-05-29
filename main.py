import os
import shutil
from argparse import ArgumentParser

from xfbin import *
from xfbin.structure.nucc import NuccChunk


def main():
    parser = ArgumentParser(
        description="""Extracts nuccChunks from CyberConnect2 XFBIN container files.""")
    parser.add_argument('input', nargs='?', action='store',
                        help='path to input XFBIN file')
    parser.add_argument('output', nargs='?', action='store',
                        help='path to output folder to extract the chunks to (defaults to a new folder with the name of the input XFBIN)')
    parser.add_argument('-f', '--force-overwrite', dest='force_overwrite', action='store_true',
                        help='overwrite old extracted files without prompting')
    parser.add_argument('-s', '--sort-types', dest='sort_types', action='store_true',
                        help='sort nuccChunks by type instead of page')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='print info about each extracted chunk')

    args = parser.parse_args()

    if not args.input:
        print('No INPUT was given.\nAborting.')
        os.system('pause')
        return

    if not args.output:
        args.output = os.path.basename(args.input).split('.')[0]

    args.output = os.path.abspath(args.output)
    if os.path.exists(args.output):
        if (not args.force_overwrite) and input('Overwrite existing files? (Y/N)\n').lower() != 'y':
            print('Aborting.')
            os.system('pause')
            return
        print(f'Removing old directory: {args.output}')
        shutil.rmtree(args.output)

    os.mkdir(args.output)

    # Read the file
    xfbin = read_xfbin(args.input)

    # Get a dictionary of chunks based on page or chunk type
    chunk_dict = (xfbin.get_type_chunk_dict() if args.sort_types else xfbin.get_page_chunk_dict()).items()

    for k, v in chunk_dict:
        # Create a folder with the chunk's type as its name (or page number)
        page_path = os.path.join(args.output, k.__qualname__[len(NuccChunk.__qualname__):] if args.sort_types else k)
        os.mkdir(page_path)

        for c in v:
            chunk_path = os.path.join(page_path, c.name + c.extension)

            if args.verbose:
                print(f'Writing {chunk_path} ...')

            with open(chunk_path, 'wb') as f:
                f.write(c.data)

    print("Done!")


if __name__ == '__main__':
    main()
