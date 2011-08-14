#!/usr/bin/env python
# Utility to track Strava.com KOMs.
# Brooks Sizemore (brooks@darg.net)

import datetime
import getopt
import json
import os
import re
import sys
import urllib2

MAX_KOM_PAGES = 10

class KOM(object):
  """Monitors KOMs on Strava."""

  def __init__(self, athlete_id):
    """Default Constructor."""
    self.koms = {}
    self.old_koms = self._LoadFromFile('koms.json')
    self.athlete_id = athlete_id

  def _FetchPage(self, page_num=1):
    """Fetches a page of KOM listings."""

    # Construct the paginated URL
    url = 'http://app.strava.com/athletes/%d/segments/leader?page=%d' % (self.athlete_id, page_num)

    f = urllib2.urlopen(url)
    html = f.read()
    f.close()

    return html

  def _ParseSegments(self, html):
    """Parses segments from the KOM segments page HTML."""

    num_matches = 0

    # Apply the regex to the HTML source
    matches = re.finditer('"/segments/(\d+)"\s+title="([^"]+)"', html)

    # Iterate over the matches
    for match in matches:
      num_matches += 1
      self.koms[match.group(1)] = match.group(2)

    if num_matches > 0:
      return True
    else:
      return False

  def _LoadFromFile(self, filename):
    """Loads a list of serialized KOM segments from a file."""
    f = None

    # Attempt to open the state koms file.
    try:
      f = open(filename, 'r')
    except IOError:
      # Return an empty json data structure
      return json.loads('{}')

    # Load the koms, then return them as a json data structure.
    koms = json.load(f)
    f.close()
    return koms

  def _SaveToFile(self, filename):
    """Saves a list of KOM segments to a file."""
    f = open(filename, 'wb')
    json.dump(self.koms, f)
    f.close()

  def RefreshKOMs(self):
    """Refreshes the list of KOMs from Strava."""
    for page in range(1, MAX_KOM_PAGES + 1):
      html = self._FetchPage(page)
      if not self._ParseSegments(html):
        break

  def Diff(self, filename):
    """Shows a diff of new/old KOMs."""
    old = set(self.old_koms.keys())
    new = set(self.koms.keys())
    return [new - old, old - new]

  def GetSegmentName(self, segment_id):
    """Returns the name of the KOM segment."""
    try:
      segment_name = self.koms[segment_id]
    except KeyError:
      segment_name = self.old_koms[segment_id]

    return segment_name

def usage():
  """Describes usage of the KOM monitor."""
  print 'Usage: kom.py --athlete_id=<id>'

def main(argv):
  """Main entry point."""

  # Defaults
  athlete_id = 0
  opts = []
  args = []

  try:
    opts, args = getopt.getopt(argv, 'a:', ['athlete_id='])
  except getopt.GetoptError:
    usage()
    sys.exit(2)

  for opt, arg in opts:
    if opt in ('-a', '--athlete_id'):
      athlete_id = int(arg)

  if athlete_id == 0:
    usage()
    sys.exit(2)

  kom = KOM(athlete_id)
  kom.RefreshKOMs()
  diff = kom.Diff('koms.json')

  # KOMs gained
  for segment_id in diff[0]:
    print '+ %s\t%s' % (segment_id, kom.GetSegmentName(segment_id))

  # KOMs lost
  for segment_id in diff[1]:
    print '- %s\t%s' % (segment_id, kom.GetSegmentName(segment_id))

  # Calculate 'today'
  now = datetime.datetime.now()
  json_today = 'koms.json.%04d%02d%02d' % (now.year, now.month, now.day)

  # Archive today's KOMs for a later diff
  os.unlink('koms.json')
  kom._SaveToFile(json_today)
  os.symlink(json_today, 'koms.json')

if __name__ == '__main__':
  main(sys.argv[1:])
