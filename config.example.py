#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# License: GPL-3.0
# Original Kinobot by Vitiko <vhnz98@gmail.com>
#
# kinobot/__init__.py imports this module (`import config`).
# Copy it to config.py and fill in what you use. Leave the rest blank.
# kinobot/config.py reads the same names from config.yml (or YAML_CONFIG)
# and from KINOBOT_* environment variables.

# --- process ---
test = ""  # true/false
image_extension = ""  # jpg or png
app_dir = ""
db = ""
fonts_dir = ""
stories_dir = ""
movies_dir = ""
tv_shows_dir = ""
subs_dir = ""
profiles_path = ""
offensive_regex = ""
hdr_tonemap = ""  # auto, on, or off
trace_config = ""
proxy_file = ""
backdrops = ""
period = ""
type = ""
video = ""
emby_user = ""
jellyfin_user = ""

# --- apis ---
tmdb = {"api_key": ""}
fanart = {"api_key": ""}
last_fm = {"api_key": ""}
igdb = {"client_id": "", "client_secret": "", "access_token": ""}
genius = {"token": "", "proxy_file": ""}

# --- discord ---
discord = {
    "token_admin": "",
    "token_public": "",
    "token_public_foreign": "",
    "token_patreon_test": "",
    "logger": "",
}

# --- webhooks ---
webhooks = {
    "traceback": "",
    "announcer": "",
    "addition": "",
    "tickets": "",
    "ticket_filter": "",
}
webhook = {"announcer": ""}

# --- media servers ---
emby = {"host": "", "api_key": ""}
jellyfin = {"host": "", "api_key": ""}
plex = {"host": "", "token": "", "mappings": []}
deluge = {"host": "", "port": "", "username": "", "password": ""}
anime = {"username": "", "passkey": "", "folder": "", "mapping": []}

# --- libraries (radarr entries also use movies_dir and radarr_root_dir) ---
curator = {
    "radarr": {"url": "", "token": ""},
    "sonarr": {"url": "", "token": "", "map": []},
}
radarr = [{"url": "", "token": "", "movies_dir": "", "radarr_root_dir": ""}]

# --- facebook / posters ---
facebook = {
    "main": {"token": "", "insights_token": ""},
}
posters = {
    "published": "",
    "instances": [
        {
            "enabled": "",
            "name": "",
            "tag": "",
            "page": "",
            "table": "",
            "token": "",
            "scheduler": "",
        }
    ],
}
post_events = {
    "webhook": "",
    "money_bonus": "",
    "money_bonus_plus": "",
    "gb_bonus": "",
}

# --- downloads ---
ytdlp = {"cookies": "", "proxy": "", "cache_dir": ""}
requests_cache = {"games": ""}

# --- databases ---
infra = {"sqlalchemy_url": ""}
sources = {"sqlalchemy_url": ""}

# --- instagram (KINOBOT_IG_*) ---
db_url = ""
ig_client = {}
client = {}
publishers = []

# --- http service (KINOBOT_SERVER_CONFIG) ---
services = {"default_image_transporter": {"name": "", "config": {"host": "", "output_dir": ""}}}
rest = {
    "port": "",
    "host": "",
    "api_key": "",
    "log_level": "",
    "workers": "",
    "log_config": "",
    "reload": "",
}

# --- comics ---
comics = {
    "root_dir": "",
    "url": "",
    "api_key": "",
    "username": "",
    "password": "",
    "comicvine": {"api_key": ""},
}

# --- wrapped cards ---
wrapped = {
    "font_medium": "",
    "font_bold": "",
    "font_color": "",
    "template": "",
}
