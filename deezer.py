import spotipy
from spotipy.oauth2 import SpotifyOAuth
import requests
import pygame
import tempfile
import os
import deezer
import deezer
import json
import pandas as pd
import requests
import re
import csv







# --- deezer --------------------------------------
client = deezer.Client()

with deezer.Client() as client:
    client.search('Dead Limit')
    client.get