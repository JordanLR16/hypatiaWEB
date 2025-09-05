import ephem
import numpy as np

# Constants
# Earth radius in kilometers
R_EARTH_KM = 6378.137
# Astronomical unit in kilometers
AU_KM = 149597870.7

def eci_vector(body, body_type='sat'):
    """
    Given a PyEphem Body (e.g. your satellite or the Sun, after .compute(date)),
    return its position vector in Earth-centered inertial coordinates (km).
    Uses the body's geocentric RA/Dec and range (in AU for both sats & planets).
    """
    ra = float(body.g_ra)
    dec = float(body.g_dec)
    # PyEphem's .range is in AU
    if body_type == 'sat':
        r_km = float(body.range) / 1e3
    elif body_type == 'sun':
        r_au = float(body.earth_distance)
        r_km = r_au * AU_KM

    x = r_km * np.cos(dec) * np.cos(ra)
    y = r_km * np.cos(dec) * np.sin(ra)
    z = r_km * np.sin(dec)
    return np.array([x, y, z])


def is_sunlit(sat, when=None):
    """
    Returns True if `sat` (a PyEphem EarthSatellite) is sunlit at time `when`,
    False if it's in the Earth's umbra (full shadow).

    `when` can be a string like '2025/04/24 12:34:56' or a datetime;
    if None, uses the satellite's current .date.
    """
    # create observer
    observer = ephem.Observer()
    observer.elevation = - R_EARTH_KM * 1e3
    observer.date = when if when is not None else sat.date

    # 1) compute satellite at the desired time
    sat.compute(observer)

    # 2) compute Sun at the same moment
    sun = ephem.Sun()
    sun.compute(observer)

    # 3) get ECI vectors (Earth center at origin) in km
    r_sat = eci_vector(sat, body_type='sat')
    r_sun = eci_vector(sun, body_type='sun')

    # 4) line from sat to sun: parametric point p(t) = r_sat + t*(r_sun - r_sat)
    v = r_sun - r_sat

    # 5) find the closest approach of that line to Earth's center
    #    t0 = - (r_sat · v) / (v · v)
    t0 = -np.dot(r_sat, v) / np.dot(v, v)
    closest = r_sat + t0 * v
    dist_closest = np.linalg.norm(closest)
    print(dist_closest)

    # 6) if that closest‐approach distance is less than Earth's radius,
    #    the Earth blocks the Sun → satellite is in eclipse
    return dist_closest > R_EARTH_KM

if __name__ == "__main__":
    tle_line1 = "1 33314U 08040C   25019.64834203  .00003890  00000-0  30932-3 0  9993"
    tle_line2 = "2 33314  97.4748  63.3164 0026290 131.9660 228.3811 15.00717199888563"
    sat = ephem.readtle("ISS", tle_line1, tle_line2)

    # # check right now
    # if is_sunlit(sat):
    #     print("🚀 Satellite is sunlit right now.")
    # else:
    #     print("🌑 Satellite is in Earth's shadow (eclipse).")

    # check at a specific UTC time
    for hour in range(24):
        t = f"2025/04/24 {hour}:00:00"
    # for t in ["2025/04/24 00:00:00", "2025/04/24 06:00:00", "2025/04/24 12:00:00", "2025/04/24 10:00:00"]:
        print(f"{t} UTC:", "sunlit" if is_sunlit(sat, t) else "eclipsed")