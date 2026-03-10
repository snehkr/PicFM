import piexif
from PIL import Image


def get_exif_data(image_path):
    """Extract relevant EXIF metadata safely."""
    data = {
        "date_taken": None,
        "camera_model": None,
        "gps_lat": None,
        "gps_lon": None,
    }

    try:
        exif_dict = piexif.load(image_path)
    except Exception:
        # Image has no EXIF data
        return data

    try:
        # --- Date Taken ---
        if piexif.ExifIFD.DateTimeOriginal in exif_dict.get("Exif", {}):
            data["date_taken"] = exif_dict["Exif"][
                piexif.ExifIFD.DateTimeOriginal
            ].decode("utf-8")

        elif piexif.ImageIFD.DateTime in exif_dict.get("0th", {}):
            data["date_taken"] = exif_dict["0th"][piexif.ImageIFD.DateTime].decode(
                "utf-8"
            )

        # --- Camera Model ---
        if piexif.ImageIFD.Model in exif_dict.get("0th", {}):
            data["camera_model"] = (
                exif_dict["0th"][piexif.ImageIFD.Model]
                .decode("utf-8", errors="ignore")
                .strip("\x00")
            )

        # --- GPS Data ---
        gps = exif_dict.get("GPS", {})

        if (
            piexif.GPSIFD.GPSLatitude in gps
            and piexif.GPSIFD.GPSLongitude in gps
            and piexif.GPSIFD.GPSLatitudeRef in gps
            and piexif.GPSIFD.GPSLongitudeRef in gps
        ):
            lat = gps[piexif.GPSIFD.GPSLatitude]
            lon = gps[piexif.GPSIFD.GPSLongitude]

            lat_ref = gps[piexif.GPSIFD.GPSLatitudeRef].decode("utf-8")
            lon_ref = gps[piexif.GPSIFD.GPSLongitudeRef].decode("utf-8")

            data["gps_lat"] = dms_to_dd(lat, lat_ref)
            data["gps_lon"] = dms_to_dd(lon, lon_ref)

    except Exception:
        pass

    return data


def dms_to_dd(dms, ref):
    """Convert GPS coordinates from DMS to decimal degrees."""
    try:
        degrees = dms[0][0] / dms[0][1]
        minutes = dms[1][0] / dms[1][1] / 60
        seconds = dms[2][0] / dms[2][1] / 3600

        dd = degrees + minutes + seconds

        if ref in ("S", "W"):
            dd *= -1

        return round(dd, 6)

    except Exception:
        return None
