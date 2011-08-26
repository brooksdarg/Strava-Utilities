#!/usr/bin/env python
# Brooks Sizemore, brooks@darg.net

import json
import memcache
import urllib2

class StravaObject(object):
  """Abstract Strava object."""

  def __init__(self, memcache_servers=['127.0.0.1:11211']):
    """Default constructor."""
    self._api_base = 'http://app.strava.com/api/v1'
    if memcache_servers:
      self._InitMemcache(memcache_servers)

  def _InitMemcache(self, servers):
    """Initialize memcache instance."""
    self._mc = memcache.Client(servers, debug=0)

  def GetId(self):
    """Returns the id of the object."""
    return self._id

  def GetName(self):
    """Returns the name of the object."""
    return self._name
  
  def FetchJson(self, url, key=None):
    """Fetches a JSON object from Strava with caching."""
    
    # Check memcache first
    if self._mc and key:
      obj_str = self._mc.get(key)
      if obj_str:
        return json.loads(obj_str)

    f = urllib2.urlopen(url)
    json_str = f.read()
    f.close()

    if self._mc and key:
      self._mc.set(key, json_str)

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
    self._mc_key = '/segment/%d' % int(id)

  def Refresh(self):
    """Refreshes the object from Strava data."""
    segment_json = self.FetchJson(self._url, key=self._mc_key)['segment']
    self._id = segment_json[u'id']
    self._name = segment_json[u'name']

  def GetEfforts(self):
    """Fetches the best efforts for a segment."""
    efforts_url = '%s/segments/%d/efforts?best=true' % (self._api_base, int(self._id))
    mc_key = '/segment/%d/efforts' % int(self._id)
    efforts_json = self.FetchJson(efforts_url, key=mc_key)

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
    mc_key = '/ride/%d/efforts' % int(self._id)
    efforts_json = self.FetchJson(efforts_url, key=mc_key)

    efforts = []
    for effort in efforts_json[u'efforts']:
      segment = Segment(effort[u'segment'][u'id'], name=effort[u'segment'][u'name'])
      efforts.append(Effort(segment, effort[u'elapsed_time']))
    return efforts

  def GetStream(self):
    """Fetches the stream (coords over time) for a ride."""
    stream_url = '%s/streams/%d' % (self._api_base, int(self._id))
    mc_key = '/ride/%d/stream' % int(self._id)
    stream_json = self.FetchJson(stream_url, key=mc_key)
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
    mc_key = '/rides/%d' % int(self._id)
    rides_json = self.FetchJson(rides_url, key=mc_key)

    rides = []
    for ride in rides_json[u'rides']:
      rides.append(Ride(ride[u'id'], name=ride[u'name']))
    return rides

