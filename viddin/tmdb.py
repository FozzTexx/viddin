# Copyright 2024 by Chris Osborn <fozztexx@fozztexx.com>
#
# This file is part of viddin.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License at <http://www.gnu.org/licenses/> for
# more details.

import os
import tmdbsimple as tmdb
from viddin.episode import EpisodeInfo, EpisodeID

def loadEpisodeInfoFromTMDB(seriesName, dvdIgnore=False, dvdMissing=False,
                            quietFlag=False, interactiveFlag=False):
  key_path = os.path.join(os.path.expanduser("~"), ".tmdbkey")
  with open(key_path, "r") as f:
    tmdb_key = f.readline().strip()
    tmdb.API_KEY = tmdb_key

  search = tmdb.Search()
  response = search.tv(query=seriesName)

  series = tmdb.TV(search.results[0]['id'])
  series_info = series.info()
  seasons = [x['season_number'] for x in series_info['seasons']]

  series = tmdb.TV(series_info['id'])
  append_keys = [f"season/{x}" for x in seasons]
  append = ",".join(append_keys)
  ep_data = series.info(append_to_response=append)

  episodes = []
  for key in append_keys:
    season = ep_data[key]
    for idx, ep_info in enumerate(season['episodes']):
      epdict = {
        'airedID': EpisodeID(season=ep_info['season_number'],
                             episode=ep_info['episode_number']),
        'absoluteNum': idx+1,
        'title': ep_info['name'],
        'airDate': ep_info['air_date'],
        'productionCode': ep_info['production_code'],
      }
      epdict['dvdID'] = epdict['airedID']
      episodes.append(EpisodeInfo(**epdict))

  return episodes
