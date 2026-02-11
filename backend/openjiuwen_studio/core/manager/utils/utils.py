import os
import re
from typing import Optional, Tuple
import tomllib

from pydantic import BaseModel, Field, ValidationError

from openjiuwen.core.common.logging import logger


class Version(BaseModel):
    prefix: str = Field(default="", description="版本前缀，如 'v' 或 'release-'")
    major: int = Field(..., ge=0, description="主版本号，必须为非负整数")
    minor: int = Field(..., ge=0, description="次版本号，必须为非负整数")
    patch: int = Field(..., ge=0, description="修订号，必须为非负整数")

    def to_string(self) -> str:
        """Convert version object to string representation"""
        return f"{self.prefix}{self.major}.{self.minor}.{self.patch}"

    @classmethod
    def string_to_object(cls, version_str: str) -> Tuple[Optional['Version'], Optional[str]]:
        """
        Create Version object from version string

        Args:
            version_str: Version string, such as "v1.2.3" or "2.5.8"

        Returns:
            Tuple (Version object, error message)
            If successful, returns (Version, None)
            If failed, returns (None, error message)
        """
        # Use regular expression to match version string
        pattern = r'^([^\d]*)(\d+)\.(\d+)\.(\d+)$'
        match = re.match(pattern, version_str)

        if not match:
            return None, f"Invalid version string format: '{version_str}', expected format like 'v1.2.3'"

        # Extract matched groups
        prefix, major_str, minor_str, patch_str = match.groups()

        try:
            # Convert to integers
            major = int(major_str)
            minor = int(minor_str)
            patch = int(patch_str)
        except ValueError as e:
            return None, f"Version number contains invalid digits: '{version_str}', error: {e}"

        try:
            # Create and return Version object
            version = cls(prefix=prefix, major=major, minor=minor, patch=patch)
            return version, None
        except ValidationError as e:
            return None, f"Version data validation failed: {e}"


def is_incremental(latest: Version, current: Version) -> bool:
    if latest.major > current.major:
        return False
    elif latest.major < current.major:
        return True

    if latest.minor > current.minor:
        return False
    elif latest.minor < current.minor:
        return True

    return latest.patch < current.patch


def check_version(latest: str, current: str) -> tuple[bool, str | None]:
    latest_version, err = Version.string_to_object(latest)
    if err is not None:
        logger.error(f"Invalid latest version format: {latest}")
        return False, f"Latest version {latest} has invalid format: {err}"
    current_version, err = Version.string_to_object(current)
    if err is not None:
        logger.error(f"Invalid current version format: {current}")
        return False, f"Current version {current} has invalid format: {err}"

    if not is_incremental(latest_version, current_version):
        logger.error(f"Version not incremental: current {current_version} is not greater than latest {latest_version}")
        return False, f"Current release version {current} must be higher than existing latest version {latest}"

    return True, None


def convert_to_properties_format(input_list):
    """Convert parameter list to properties format"""

    properties = {}
    requires = []

    if not input_list:
        return {}

    try:
        for item in input_list:
            property_name = item.get('name')
            properties[property_name] = {
                'type': item.get('type'),
                'description': item.get('description'),
            }
            if item.get('required') is True:
                requires.append(property_name)
        return properties, requires
    except (KeyError, TypeError) as e:
        logger.error(f"[AGENT_CONVERT] failed to convert parameters to properties format - Error: {e}")
        raise ValueError(f"Failed to convert properties format: {e}") from e


def get_current_project_version() -> str:
    """Get current project version from pyproject.toml"""
    try:
        # Build path to pyproject.toml file
        current_file = os.path.abspath(__file__)
        # Navigate up the directory structure to find pyproject.toml
        # utils.py is in backend/openjiuwen_studio/core/manager/utils/
        # pyproject.toml is in backend/
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file)))))
        pyproject_path = os.path.join(backend_dir, "pyproject.toml")

        # Read and parse pyproject.toml
        with open(pyproject_path, "rb") as f:
            pyproject_data = tomllib.load(f)

        # Get version from project section
        version = pyproject_data.get("project", {}).get("version", "")
        return version
    except Exception as e:
        logger.warning(f"Failed to get current project version from pyproject.toml: {e}")
        return ""
