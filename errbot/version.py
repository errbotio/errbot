# Just the current version of Errbot.
# It is used for deployment on pypi AND for version checking at plugin load time.
from pkg_resources import get_distribution, DistributionNotFound
try:
    VERSION = get_distribution('errbot').version
except DistributionNotFound:
    # package is not installed
    VERSION = '9.9.9'
