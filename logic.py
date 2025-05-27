import xml.etree.ElementTree as ET
import math
import ezdxf

# --- Constants ---
CANVAS_SIZE: int = 540
CANVAS_CENTER: int = CANVAS_SIZE // 2
SCALE_PADDING: float = 0.7
SCALE_DENOM: float = 520
DEFAULT_START_ANGLE: float = 90.0
DEFAULT_ANGLE_INCREMENT: float = 0.25
SPACING_X: int = 5000
COLOR_MAP = {
    'Warning1': 2,      # Yellow
    'Warning2': 1,      # Red
    'Protection1': 3,   # Green
    'Default': 7        # White
}
REGION_COLORS = {
    "Warning1": "#ffe066",
    "Warning2": "#ff5c5c",
    "Protection1": "#5cff8d",
    "Default": "#7ecfff"
}

def load_xml_points(file_path: str) -> list:
    """
    Parse the XML file and extract area and region points.
    Args:
        file_path (str): Path to the XML file.
    Returns:
        list: List of areas, each area is a list of regions with type and points.
    """
    tree = ET.parse(file_path)
    root = tree.getroot()
    areas = []
    for area in root.findall('.//Area'):
        area_data = []
        for region in area.findall('.//Region'):
            region_type = region.attrib.get('Type')
            points_raw = region.findtext('Points')
            if not points_raw:
                continue
            points = [int(p) for p in points_raw.strip().split(',') if p.strip().isdigit()]
            area_data.append({
                'region_type': region_type,
                'points': points
            })
        areas.append(area_data)
    return areas

def polar_to_cartesian(
    points: list[int],
    start_angle_deg: float = DEFAULT_START_ANGLE,
    angle_increment_deg: float = DEFAULT_ANGLE_INCREMENT,
    offset_x: float = 0.0
) -> list[tuple[float, float]]:
    """
    Convert a list of polar distances to cartesian coordinates.
    Args:
        points (list[int]): List of distances.
        start_angle_deg (float): Starting angle in degrees.
        angle_increment_deg (float): Angle increment per point in degrees.
        offset_x (float): X offset for all points.
    Returns:
        list[tuple[float, float]]: List of (x, y) coordinates.
    """
    angle_rad = math.radians(start_angle_deg)
    increment_rad = math.radians(angle_increment_deg)
    coords = []
    for p in points:
        x = p * math.cos(angle_rad) + offset_x
        y = p * math.sin(angle_rad)
        coords.append((x, y))
        angle_rad += increment_rad
    return coords

def draw_to_dxf(
    areas: list,
    output_path: str = "laser_output.dxf",
    spacing_x: int = SPACING_X,
    start_angle_deg: float = DEFAULT_START_ANGLE,
    angle_increment_deg: float = DEFAULT_ANGLE_INCREMENT
) -> None:
    """
    Draws the areas to a DXF file.
    Args:
        areas (list): List of areas with regions and points.
        output_path (str): Output DXF file path.
        spacing_x (int): X offset between areas.
        start_angle_deg (float): Starting angle in degrees.
        angle_increment_deg (float): Angle increment per point in degrees.
    """
    doc = ezdxf.new(dxfversion="R2010")
    msp = doc.modelspace()
    for i, area in enumerate(areas):
        offset_x = i * spacing_x
        for region in area:
            coords = polar_to_cartesian(
                region['points'],
                start_angle_deg=start_angle_deg,
                angle_increment_deg=angle_increment_deg,
                offset_x=offset_x
            )
            if len(coords) > 1:
                is_closed = coords[0] == coords[-1] if len(coords) > 2 else False
                msp.add_lwpolyline(
                    coords,
                    dxfattribs={
                        "color": COLOR_MAP.get(region['region_type'], COLOR_MAP['Default'])
                    },
                    close=is_closed
                )
    doc.saveas(output_path)
    # Nu bloca UI-ul cu messagebox la fișiere mari
