import ephem
import numpy as np

# Constants
# Earth radius in kilometers
R_EARTH_KM = 6378.137
# Astronomical unit in kilometers
AU_KM = 149597870.7

def eci_vector(body):
    ra = float(body.g_ra)
    dec = float(body.g_dec)
    r_km = float(body.range) * AU_KM
    x = r_km * np.cos(dec) * np.cos(ra)
    y = r_km * np.cos(dec) * np.sin(ra)
    z = r_km * np.sin(dec)
    return np.array([x, y, z])

def is_sunlit(sat, when=None):
    # 1) parse/normalize the time
    if when is not None:
        date = ephem.Date(when)    # <— convert string (or datetime) to ephem.Date
    else:
        date = sat.date           # use the satellite’s internal date

    # 2) compute satellite and sun at that ephem.Date
    sat.compute(date)            # sets g_ra, g_dec, range, etc.
    sun = ephem.Sun()            
    sun.compute(date)            # now sun.range is defined

    # 3) build ECI vectors
    r_sat = eci_vector(sat)
    r_sun = eci_vector(sun)

    # 4) check line‐of‐sight shadow test
    v = r_sun - r_sat
    t0 = -np.dot(r_sat, v) / np.dot(v, v)
    closest = r_sat + t0 * v
    return np.linalg.norm(closest) > R_EARTH_KM


# ------------- example usage -------------
# load your satellite from TLE
tle_line1 = "1 33314U 08040C   25019.64834203  .00003890  00000-0  30932-3 0  9993"
tle_line2 = "2 33314  97.4748  63.3164 0026290 131.9660 228.3811 15.00717199888563"
sat = ephem.readtle("ISS", tle_line1, tle_line2)

# # check right now
# if is_sunlit(sat):
#     print("🚀 Satellite is sunlit right now.")
# else:
#     print("🌑 Satellite is in Earth's shadow (eclipse).")

# check at a specific UTC time
for t in ["2025/04/24 00:00:00", "2025/04/24 06:00:00", "2025/04/24 12:00:00"]:
    print(f"{t} UTC:", "sunlit" if is_sunlit(sat, t) else "eclipsed")
