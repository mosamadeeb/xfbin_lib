import json
import os
import shutil
from argparse import ArgumentParser

from xfbin import *
from xfbin.structure.nucc import NuccChunk

VERSION = 'v1.1'
AUTHOR = 'SutandoTsukai181'


def main():
    print(f'xfbin_parser {VERSION}')
    print(f'By {AUTHOR}\n')

    parser = ArgumentParser(
        description="""Extracts nuccChunks from CyberConnect2 XFBIN container files.""")
    parser.add_argument('input', nargs='?', action='store',
                        help='path to input XFBIN file')
    parser.add_argument('output', nargs='?', action='store',
                        help='path to output folder to extract the chunks to (defaults to a new folder with the name of the input XFBIN)')
    parser.add_argument('-f', '--force-overwrite', dest='force_overwrite', action='store_true',
                        help='overwrite old extracted files without prompting')
    parser.add_argument('-d', '--file-data-only', dest='file_data_only', action='store_true',
                        help='when possible, write each chunk\'s file data only (NTP3 for .nut, NDP3 for .nud) (will disable repacking)')
    parser.add_argument('-s', '--sort-types', dest='sort_types', action='store_true',
                        help='sort nuccChunks by type instead of page (will disable repacking)')
    parser.add_argument('-j', '--no-json', dest='no_json', action='store_true',
                        help='do not write "page.json" for extracted pages (will disable repacking)')
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

    if args.file_data_only:
        args.no_json = True

    # Read the file
    xfbin = read_xfbin(args.input)

    if args.sort_types:
        # Get a dictionary of chunks based on chunk type
        for k, v in xfbin.get_type_chunk_dict().items():
            # Create a folder with the chunk's type as its name
            page_path = os.path.join(args.output, k.__qualname__[len(NuccChunk.__qualname__):])
            os.mkdir(page_path)

            for c in v:
                chunk_path = os.path.join(page_path, c.name + '.' + (c.extension
                                                                     if (args.file_data_only and c.extension != '')
                                                                     else NuccChunk.get_nucc_str_short_from_type(type(c)).lower()))

                if args.verbose:
                    print(f'Writing {chunk_path} ...')

                with open(chunk_path, 'wb') as f:
                    f.write(c.get_data(args.file_data_only))
    else:
        for i, page in enumerate(xfbin.pages):
            page.cleanup()

            if not page.chunks:
                print(f'Page {i} does not contain chunks and will be skipped.')
                continue

            # Create the page's folder with the main chunk's name
            clump_chunk = page.get_chunks_by_type(NuccChunkClump)
            main_chunk = clump_chunk[0] if len(clump_chunk) else page.chunks[-1]

            page_path = os.path.join(
                args.output, f'[{i:03}] {main_chunk.name} ({NuccChunk.get_nucc_str_from_type(type(main_chunk))})')
            os.mkdir(page_path)

            page_json = dict()
            page_json['Chunk Maps'] = list(map(lambda x: x.to_dict(), page.initial_page_chunks))

            chunk_refs = page_json['Chunk References'] = [None] * len(page.chunk_references)
            for j, cr in enumerate(page.chunk_references):
                d = chunk_refs[j] = dict()
                d['Name'] = cr.name
                d['Chunk'] = cr.chunk.to_dict()

            chunks = page_json['Chunks'] = [None] * len(page.chunks)
            for j, c in enumerate(page.chunks):
                d = chunks[j] = dict()
                d['File Name'] = c.name + '.' + (c.extension
                                                 if (args.file_data_only and c.extension != '')
                                                 else NuccChunk.get_nucc_str_short_from_type(type(c)).lower())
                d['Chunk'] = c.to_dict()

                chunk_path = os.path.join(page_path, d['File Name'])

                if args.verbose:
                    print(f'Writing {chunk_path} ...')

                with open(chunk_path, 'wb') as f:
                    f.write(c.get_data(args.file_data_only))

            if not args.no_json:
                with open(os.path.join(page_path, 'page.json'), 'w') as f:
                    json.dump(page_json, f, ensure_ascii=False, indent=4)

    print("Done!")


if __name__ == '__main__':
    main()
