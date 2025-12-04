#! /usr/bin/env python3

"""
Zotify
It's like youtube-dl, but for that other music platform.
"""

import argparse

from zotify import __version__
from zotify.app import client
from zotify.config import CONFIG_VALUES, DEPRECIATED_CONFIGS
from zotify.termoutput import Printer

class DepreciatedAction(argparse.Action):
    def __init__(self, option_strings, dest, **kwargs):
        if "help" in kwargs:
            kwargs["help"] = "[DEPRECATED] " + kwargs["help"]
        super().__init__(option_strings, dest, **kwargs)
    
    def __call__(self, parser, namespace, values, option_string=None):
        Printer.depreciated_warning(option_string, self.help, CONFIG=False)
        setattr(namespace, self.dest, values)

DEPRECIATED_FLAGS = (
    {"flags":    ('-d', '--download',),     "type":    str,     "help":    'Use `--file` (`-f`) instead'},
)

def main():
    parser = argparse.ArgumentParser(prog='zotify',
        description='A music and podcast downloader needing only Python and FFMPEG.')
    
    parser.register('action', 'depreciated_ignore_warn', DepreciatedAction)
    
    parser.add_argument('--version',
                        action='version',
                        version=f'Zotify {__version__}',
                        help='Show the version of Zotify')
    
    parser.add_argument('-c', '--config', '--config-location',
                        type=str,
                        dest='config_location',
                        help='Specify a directory containing a Zotify `config.json` file to load settings')
    parser.add_argument('-u', '--username',
                        type=str,
                        dest='username',
                        help='Account username')
    parser.add_argument('--token',
                        type=str,
                        dest='token',
                        help='Authentication token')
    
    # Headless OAuth options
    parser.add_argument('--generate-auth-url',
                        action='store_true',
                        dest='generate_auth_url',
                        help='Generate OAuth URL and code_verifier for headless authentication (requires --client-id and --redirect-uri)')
    
    parser.add_argument('-ns', '--no-splash',
                        action='store_true',
                        help='Suppress the splash screen when loading')
    parser.add_argument('--debug',
                        action='store_true',
                        help='Enable debug mode, prints extra information and creates a `config_DEBUG.json` file')
    parser.add_argument('--update-config',
                        action='store_true',
                        help='Updates the `config.json` file while keeping all current settings unchanged')
    
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument('urls',
                       type=str,
                       # action='extend',
                       default='',
                       nargs='*',
                       help='Download track(s), album(s), playlist(s), podcast episode(s), or artist(s) specified by the URL(s) passed as a command line argument(s). If an artist\'s URL is given, all albums by the specified artist will be downloaded. Can take multiple URLs as multiple arguments.')
    group.add_argument('-l', '--liked',
                       dest='liked_songs',
                       action='store_true',
                       help='Download all Liked Songs on your account')
    group.add_argument('-a', '--artists',
                       dest='followed_artists',
                       action='store_true',
                       help='Download all songs by all followed artists')
    group.add_argument('-p', '--playlist',
                       action='store_true',
                       help='Download playlist(s) saved by your account (interactive)')
    group.add_argument('-s', '--search',
                       type=str,
                       nargs='?',
                       const=' ',
                       help='Search tracks/albums/artists/playlists based on argument (interactive)')
    group.add_argument('-f', '--file',
                       type=str,
                       dest='file_of_urls',
                       help='Download all tracks/albums/episodes/playlists URLs within the file passed as argument')
    group.add_argument('-v', '--verify-library',
                       dest='verify_library',
                       action='store_true',
                       help='Check metadata for all tracks in ROOT_PATH or listed in SONG_ARCHIVE, updating the metadata if necessary. This will not download any new tracks, but may take a very, very long time.')
    
    for flag in DEPRECIATED_FLAGS: 
        group.add_argument(*flag["flags"],
                           type=flag["type"],
                           help=flag["help"],
                           action='depreciated_ignore_warn')
    
    for key in DEPRECIATED_CONFIGS:
        parser.add_argument(*DEPRECIATED_CONFIGS[key]['arg'],
                            type=str,
                            action='depreciated_ignore_warn',
                            help=f'Delete the {key} flag from the commandline call'
                            )
    
    for key in CONFIG_VALUES:
        parser.add_argument(*CONFIG_VALUES[key]['arg'],
                            type=str, #type conversion occurs in config.parse_arg_value()
                            dest=key.lower(),
                            default=None,
                            )
    
    parser.set_defaults(func=client)
    
    args = parser.parse_args()
    
    # Handle --generate-auth-url mode
    if args.generate_auth_url:
        handle_generate_auth_url(args)
        return
    
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\n")
        raise
    print("\n")


def handle_generate_auth_url(args):
    """Generate OAuth URL and code_verifier for headless authentication."""
    from zotify.config import Zotify
    
    client_id = getattr(args, 'client_id', None)
    redirect_uri = getattr(args, 'oauth_redirect_uri', None)
    
    if not client_id:
        print("Error: --client-id is required for --generate-auth-url")
        return
    
    if not redirect_uri:
        print("Error: --oauth-redirect-uri is required for --generate-auth-url")
        return
    
    oauth_url, code_verifier = Zotify.generate_auth_url(client_id, redirect_uri)
    
    print(f"OAuth URL: {oauth_url}")
    print(f"Code Verifier: {code_verifier}")
    print("\nInstructions:")
    print("1. Open the OAuth URL in a browser")
    print("2. Authorize the application")
    print("3. Copy the 'code' parameter from the redirect URL")
    print("4. Use zotify with --auth-code <CODE> --code-verifier <VERIFIER>")


if __name__ == '__main__':
    main()
