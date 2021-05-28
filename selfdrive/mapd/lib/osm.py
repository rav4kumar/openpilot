import overpy


class OSM():
  def __init__(self):
    self.api = overpy.Overpass()
    # self.api = overpy.Overpass(url='http://3.65.170.21/api/interpreter')

  def fetch_road_ways_around_location(self, lat, lon, radius):
      # fetch all ways and nodes on this ways around location
      around_str = f'{str(radius)},{str(lat)},{str(lon)}'
      q = """
          way(around:""" + around_str + """)
            [highway]
            [highway!~"^(footway|path|bridleway|steps|cycleway|construction|bus_guideway|escape|service)$"];
          (._;>;);
          out;
          """
      try:
        ways = self.api.query(q).ways
      except Exception as e:
        print(f'Exception while querying OSM:\n{e}')
        ways = []

      return ways
