#!/usr/bin/env python
# Python client library for Strava.com API v1
# Brooks Sizemore, brooks@darg.net

import gzip
import json
import re
import urllib2

from StringIO import StringIO

class StravaObject(object):
  """Abstract Strava object."""

  def __init__(self):
    """Default constructor."""
    self._api_base = 'http://app.strava.com/api/v1'

  def GetId(self):
    """Returns the id of the object."""
    return self._id

  def GetName(self):
    """Returns the name of the object."""
    return self._name

  def FetchViaHttp(self, url):
    """Fetches a file/page over HTTP."""

    # Create a new request with gzip encoding enabled
    request = urllib2.Request(url)
    request.add_header('Accept-Encoding', 'gzip')
    response = urllib2.urlopen(request)

    # Check to be sure the response came back encoded
    if response.info().get('Content-Encoding') == 'gzip':
      buf = StringIO(response.read())
      f = gzip.GzipFile(fileobj=buf)
      content = f.read()
      f.close()
    else:
      content = response.read()

    return content
  
  def FetchJson(self, url):
    """Fetches a JSON object from Strava with caching."""
    
    json_str = self.FetchViaHttp(url)
    return json.loads(json_str)

  @classmethod
  def convert_seconds(self, seconds):
    """Converts integer seconds into human-readable MM:SS format."""
    minutes = seconds // 60
    seconds %= 60
    return '%02i:%02i' % (minutes, seconds)

class Segment(StravaObject):
  """A Strava segment."""

  def __init__(self, id, name=None):
    """Default constructor."""
    StravaObject.__init__(self)
    self._id = id
    self._name = name
    self._url = '%s/segments/%d' % (self._api_base, int(self._id))

  def Refresh(self):
    """Refreshes the object from Strava data."""
    segment_json = self.FetchJson(self._url)['segment']
    self._id = segment_json[u'id']
    self._name = segment_json[u'name']

  def GetEfforts(self):
    """Fetches the best efforts for a segment."""
    efforts_url = '%s/segments/%d/efforts?best=true' % (self._api_base, int(self._id))
    efforts_json = self.FetchJson(efforts_url)

    efforts = []
    rank = 1
    for effort in efforts_json[u'efforts']:
      athlete = Athlete(effort[u'athlete'][u'id'], name=effort[u'athlete'][u'name'])
      efforts.append(Effort(self, effort[u'elapsedTime'], athlete=athlete, rank=rank))
      rank += 1
    return efforts

  def GetRank(self, athlete):
    """Fetches the rank of the athlete for the segment."""
    efforts = self.GetEfforts()
    for effort in efforts:
      if effort.GetAthlete == athlete:
        return effort.GetRank
    return None

  def GetLeader(self):
    """Returns the KOM/leader athlete for the segment."""
    efforts = self.GetEfforts()
    return efforts[0].GetAthlete()

  def GetStream(self):
    """Returns the stream for the segment."""
    stream_url = '%s/stream/segments/%d' % (self._api_base, int(self._id))
    stream_json = self.FetchJson(stream_url)
    return stream_json


class Effort(StravaObject):
  """A Strava segment effort."""

  def __init__(self, segment, elapsed_time, athlete=None, rank=None):
    """Default constructor."""
    StravaObject.__init__(self)
    self._segment = segment
    self._elapsed_time = elapsed_time
    self._athlete = athlete
    self._rank = rank

  def GetSegment(self):
    """Returns the segment for the effort."""
    return self._segment

  def GetElapsedTime(self):
    """Returns the elapsed time in seconds for the effort."""
    return int(self._elapsed_time)

  def GetAthlete(self):
    """Returns the athlete for the effort."""
    return self._athlete

  def GetRank(self):
    """Returns the rank of the effort."""
    return self._rank

class Ride(StravaObject):
  """A Strava ride."""

  def __init__(self, id, name=None):
    """Default constructor."""
    StravaObject.__init__(self)
    self._id = id
    self._name = name

  def GetEfforts(self):
    """Fetches a list of efforts for a ride."""
    efforts_url = '%s/rides/%d/efforts' % (self._api_base, int(self._id))
    efforts_json = self.FetchJson(efforts_url)

    efforts = []
    for effort in efforts_json[u'efforts']:
      segment = Segment(effort[u'segment'][u'id'], name=effort[u'segment'][u'name'])
      efforts.append(Effort(segment, effort[u'elapsed_time']))
    return efforts

  def GetStream(self):
    """Fetches the stream (coords over time) for a ride."""
    stream_url = '%s/streams/%d' % (self._api_base, int(self._id))
    stream_json = self.FetchJson(stream_url)
    return stream_json

  def Refresh(self):
    """Refreshes the object from Strava data."""
    ride_url = '%s/rides/%d' % (self._api_base, self._id)
    ride_key = '/ride/%d' % self._id
    ride_json = self.FetchJson(ride_url, key=ride_key)[u'ride']
    self._ride = ride_json

  def Get(self, attr):
    """Gets an attribute from the ride json."""
    return self._ride[attr]


class Athlete(StravaObject):
  """A Strava athlete."""

  def __init__(self, id, name=None):
    """Default constructor."""
    StravaObject.__init__(self)
    self._id = id
    self._name = name

  def GetRides(self):
    """Fetch a list of rides for the athlete."""
    rides_url = '%s/rides?athleteId=%d' % (self._api_base, int(self._id))
    rides_json = self.FetchJson(rides_url)

    rides = []
    for ride in rides_json[u'rides']:
      rides.append(Ride(ride[u'id'], name=ride[u'name']))
    return rides

  def GetKOMs(self):
    """Fetches a list of segments where Athlete is the leader."""

    segments = []

    for page_num in range(1, 999): # NO one has 999 pages of KOMs, right?
      html = self.FetchViaHttp('http://www.strava.com/athletes/%d/segments/leader?page=%d' % (self._id, page_num))
      matches = re.finditer('"/segments/(\d+)"\s+title="([^"]+)"', html)

      num_matches = 0
      for match in matches:
        segment = Segment(int(match.group(1)), name=match.group(2))
        segments.append(segment)
        num_matches += 1

      if num_matches == 0:
        break

    return segments

